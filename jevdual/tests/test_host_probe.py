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


def test_controller_observations_keep_ancestor_events_separate(tmp_path):
    proc, cgroup = tmp_path / "proc", tmp_path / "cgroup"
    put(proc, "self/cgroup", "0::/parent/child\n")
    put(cgroup, "pids.max", "max\n")
    put(cgroup, "memory.swap.max", "max\n")
    put(cgroup, "parent/pids.max", "512\n")
    put(cgroup, "parent/pids.current", "500\n")
    put(cgroup, "parent/pids.events", "max 423\nunknown_secret 123\n")
    put(cgroup, "parent/memory.events", "oom 0\noom_kill 0\nmax 0\n")
    put(cgroup, "parent/memory.swap.max", "0\n")
    put(cgroup, "parent/memory.swap.current", "0\n")
    put(cgroup, "parent/child/pids.max", "1024\n")
    put(cgroup, "parent/child/pids.current", "10\n")
    put(cgroup, "parent/child/pids.events", "max 400\n")
    result = host_probe._cgroups(proc, cgroup)
    rows = result["controller_observations"]
    assert result["pids_limit"] == 512 and result["pids_remaining"] == 12
    assert [(r["level"], r["scope"]) for r in rows] == [(0, "root"), (1, "ancestor"), (2, "member")]
    assert rows[0]["pids_max"] == rows[0]["swap_max_bytes"] == "max"
    assert rows[1]["pids_events"] == {"max": 423}
    assert rows[2]["pids_events"] == {"max": 400}
    assert rows[1]["memory_events"] == {"oom": 0, "oom_kill": 0, "max": 0}
    assert rows[1]["swap_max_bytes"] == rows[1]["swap_current_bytes"] == 0
    assert rows[2]["swap_max_bytes"] is None
    assert "unknown_secret" not in json.dumps(result)
    assert not result["observations_truncated"]


def test_pids_v1_zero_and_missing_are_distinct(tmp_path):
    proc, cgroup = tmp_path / "proc", tmp_path / "cgroup"
    put(proc, "self/cgroup", "7:pids:/job\n")
    put(cgroup, "pids/pids.max", "max\n")
    put(cgroup, "pids/job/pids.max", "0\n")
    put(cgroup, "pids/job/pids.current", "1\n")
    result = host_probe._cgroups(proc, cgroup)
    assert result["versions"] == [1]
    assert result["pids_limit"] == result["pids_remaining"] == 0
    assert result["controller_observations"][1]["memory_events"] is None
    assert result["controller_observations"][1]["pids_events"] is None


def test_controller_reads_are_bounded_and_unreadable_stays_unknown(tmp_path, monkeypatch):
    proc, cgroup = tmp_path / "proc", tmp_path / "cgroup"
    put(proc, "self/cgroup", "0::/\n")
    put(cgroup, "pids.events", "x" * 4097)
    put(cgroup, "memory.events", "oom 3\n")
    put(cgroup, "memory.swap.max", "7\n")
    real_open = Path.open

    def selected_unreadable(path, *args, **kwargs):
        if path.name == "memory.swap.max":
            raise PermissionError("not delegated")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", selected_unreadable)
    result = host_probe._cgroups(proc, cgroup)
    row = result["controller_observations"][0]
    assert row["pids_events"] is None and row["swap_max_bytes"] is None
    assert row["memory_events"] == {"oom": 3}
    assert result["pids_limit"] is None


def test_deep_membership_is_bounded_and_marked_partial(tmp_path):
    proc, cgroup = tmp_path / "proc", tmp_path / "cgroup"
    member = "/" + "/".join(["deep"] * 80)
    put(proc, "self/cgroup", f"0::{member}\n")
    result = host_probe._cgroups(proc, cgroup)
    assert len(result["controller_observations"]) == host_probe._MAX_LEVELS
    assert result["observations_truncated"] is True
    assert len(json.dumps(result)) < 15000


def test_too_many_membership_records_are_bounded(tmp_path):
    put(tmp_path, "self/cgroup", "0::/\n" * 60)
    result = host_probe._cgroups(tmp_path, tmp_path)
    assert len(result["controller_observations"]) == host_probe._MAX_RECORDS
    assert result["observations_truncated"] is True


def test_pid1_reports_selected_namespace_facts_without_reaping_claim(tmp_path):
    put(tmp_path, "1/comm", "docker-init\n")
    put(tmp_path, "1/status", "State:\tS (sleeping)\nPPid:\t0\nThreads:\t1\nSecret:\topaque\n")
    put(tmp_path, "1/cmdline", "do-not-read-arguments")
    put(tmp_path, "1/environ", "do-not-read-environment")
    result = host_probe._pid1(tmp_path)
    assert result["comm"] == "docker-init" and result["state"] == "S"
    assert result["parent_pid"] == 0 and result["threads"] == 1
    assert result["reaping"] == "not_checked"
    assert "opaque" not in json.dumps(result) and "do-not-read" not in json.dumps(result)


def test_pid1_missing_and_oversized_are_unknown(tmp_path):
    result = host_probe._pid1(tmp_path)
    assert result["comm"] is result["state"] is result["threads"] is None
    put(tmp_path, "1/comm", "x" * 257)
    put(tmp_path, "1/status", "x" * 8193)
    assert host_probe._pid1(tmp_path) == result


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
