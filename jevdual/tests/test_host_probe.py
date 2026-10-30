"""Presence-only diagnostics remain useful without promising runtime readiness."""

import json
import os
import subprocess
import sys
from pathlib import Path

from jevdual import host_probe


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_cgroup_v2_ancestor_limit_and_remaining_memory(tmp_path):
    proc, cgroup = tmp_path / "proc", tmp_path / "cgroup"
    put(proc, "self/cgroup", "0::/parent/child\n")
    put(cgroup, "memory.max", "max\n")
    put(cgroup, "parent/memory.max", "1024\n")
    put(cgroup, "parent/memory.current", "1000\n")
    put(cgroup, "parent/child/memory.max", "2048\n")
    put(cgroup, "parent/child/memory.current", "200\n")
    put(cgroup, "parent/cpu.max", "150000 100000\n")
    put(cgroup, "parent/child/cpu.max", "max 100000\n")
    result = host_probe._cgroups(proc, cgroup)
    assert result["versions"] == [2]
    assert result["memory_limit_bytes"] == 1024
    assert result["memory_remaining_bytes"] == 24
    assert result["cpu_quota_cores"] == 1.5


def test_cgroup_v1_limits_and_unlimited_sentinel(tmp_path):
    proc, cgroup = tmp_path / "proc", tmp_path / "cgroup"
    put(proc, "self/cgroup", "5:memory:/job\n4:cpu,cpuacct:/job\n")
    put(cgroup, "memory/memory.limit_in_bytes", "9223372036854771712\n")
    put(cgroup, "memory/job/memory.limit_in_bytes", "4096\n")
    put(cgroup, "memory/job/memory.usage_in_bytes", "5000\n")
    put(cgroup, "cpu,cpuacct/job/cpu.cfs_quota_us", "200000\n")
    put(cgroup, "cpu,cpuacct/job/cpu.cfs_period_us", "100000\n")
    result = host_probe._cgroups(proc, cgroup)
    assert result["versions"] == [1]
    assert result["memory_limit_bytes"] == 4096
    assert result["memory_remaining_bytes"] == 0
    assert result["cpu_quota_cores"] == 2


def test_missing_cgroups_do_not_assert_unlimited(tmp_path):
    result = host_probe._cgroups(tmp_path, tmp_path)
    assert result["membership_readable"] is False
    assert result["memory_limit_bytes"] is None
    assert result["cpu_quota_cores"] is None
    assert "not proof" in result["null_limit_meaning"]


def test_probe_presence_never_claims_ready_or_exposes_session_values(monkeypatch, tmp_path):
    monkeypatch.setattr(host_probe.sys, "platform", "linux")
    monkeypatch.setattr(host_probe.shutil, "which", lambda name: "/fake/bin/" + name)
    for name in host_probe._SESSION:
        monkeypatch.setenv(name, "sensitive-session-address")
    put(tmp_path, "meminfo", "MemTotal: 8192 kB\nMemAvailable: 4096 kB\n")
    put(tmp_path, "os-release", 'ID=ubuntu\nVERSION_ID="24.04"\nSECRET=do-not-return\n')
    result = host_probe.probe(proc=tmp_path, cgroup=tmp_path, os_release=tmp_path / "os-release")
    assert all(result["prerequisite_candidates"].values())
    assert result["runtime_qualification"] == "unverified"
    assert result["effect_verification"] == "not_asserted"
    assert result["resources"]["available_memory_upper_bound_bytes"] == 4096 * 1024
    assert result["distribution"] == {"ID": "ubuntu", "VERSION_ID": "24.04"}
    assert "sensitive-session-address" not in json.dumps(result)
    assert "do-not-return" not in json.dumps(result)


def test_missing_tools_and_resources_remain_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(host_probe.sys, "platform", "linux")
    monkeypatch.setattr(host_probe.shutil, "which", lambda name: None)
    for name in host_probe._SESSION:
        monkeypatch.delenv(name, raising=False)
    result = host_probe.probe(proc=tmp_path, cgroup=tmp_path, os_release=tmp_path / "absent")
    assert not any(result["prerequisite_candidates"].values())
    assert result["resources"]["available_memory_upper_bound_bytes"] is None
    assert result["runtime_qualification"] == "unverified"


def test_bounded_reads_and_membership_cannot_escape(tmp_path):
    put(tmp_path, "oversized", "x" * 65537)
    assert host_probe._read(tmp_path / "oversized") is None
    assert host_probe._hierarchy(tmp_path, "/../../private") == [tmp_path]


def test_standalone_without_site_packages_or_checkout(tmp_path):
    source = Path(host_probe.__file__)
    standalone = tmp_path / "probe.py"
    standalone.write_bytes(source.read_bytes())
    result = subprocess.run([sys.executable, "-I", "-S", str(standalone)], cwd=tmp_path,
                            capture_output=True, text=True, check=True,
                            env={**os.environ, "PATH": "", "DISPLAY": "secret-value"})
    report = json.loads(result.stdout)
    assert report["runtime_qualification"] == "unverified"
    assert not any(report["executables_present"].values())
    assert "secret-value" not in result.stdout
    assert len(result.stdout) < 10000


def test_task_swap_and_event_counters_include_ancestors_without_inventing_missing_limits(tmp_path):
    proc, cg = tmp_path / 'proc', tmp_path / 'cg'
    put(proc, 'self/cgroup', '0::/parent/child\n')
    put(cg, 'pids.max', 'max\n')
    put(cg, 'parent/pids.max', '512\n')
    put(cg, 'parent/pids.current', '510\n')
    put(cg, 'parent/pids.events', 'max 7\nunknown 100\n')
    put(cg, 'parent/memory.events', 'oom 0\noom_kill 0\nhigh 2\n')
    put(cg, 'parent/memory.swap.max', '0\n')
    put(cg, 'parent/child/pids.max', '1024\n')
    put(cg, 'parent/child/pids.current', '10\n')
    r = host_probe._cgroups(proc, cg)
    assert r['pids_limit'] == 512 and r['pids_remaining_upper_bound'] == 2
    assert r['swap_limit_bytes'] == 0
    parent = next(p for p in r['task_swap_event_snapshots'] if p['path'] == 'parent')
    assert parent['pids_events'] == {'max': 7} and parent['memory_events']['oom'] == 0
    assert parent['swap_current_bytes'] is None


def test_missing_pid_swap_and_supervision_facts_are_unknown(tmp_path):
    r = host_probe._cgroups(tmp_path, tmp_path)
    assert r['pids_limit'] is None and r['swap_limit_bytes'] is None
    assert r['task_swap_event_snapshots'] == []
    assert host_probe._supervision(tmp_path)['pid1_comm'] is None


def test_pid1_facts_do_not_read_process_arguments(tmp_path):
    put(tmp_path, '1/comm', 'tini\n')
    put(tmp_path, '1/cmdline', 'SECRET-SENTINEL')
    put(tmp_path, 'self/status', 'Name: python\nPPid:\t123\n')
    r = host_probe._supervision(tmp_path)
    assert r['pid1_comm'] == 'tini' and r['self_parent_pid'] == 123
    assert r['orphan_reaping'] == 'not_checked'
    assert 'SECRET' not in json.dumps(r)
