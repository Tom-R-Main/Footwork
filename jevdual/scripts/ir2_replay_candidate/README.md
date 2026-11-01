# IR2 Mac-hosted Linux fixture

The Mac runs the actual pinned Linux CUA source inside its existing arm64 Docker
Desktop VM. The test has no network, host display, user profile or production
CUA installation. The independent D-Bus target and test probe are the frozen
IR1 source in `../ir1_replay_audit/`. IR2 applies `candidate.patch` only to a
fresh extracted copy of the exact vendor archive.

Local cached image: `footwork-cua-ir2-offline-cache:20261101`, image ID
`sha256:f4b6128e6e031af4e1b13b5fc66c31573172a6fbbb1694b47eb1ac62a29eb264`.
It was made from stopped Footwork container `footwork-linux-native-20261030`
solely to reuse its arm64 Linux Cargo dependencies. Its Cargo.lock matches the
pin. This image is an execution input, not source authority.

Run `build_mac_linux.py` with `/repo` mounted read-only and the task-owned
`output/cua-ir2-mac-linux-20261101` directory mounted at `/work`. It extracts
the archive, checks hashes, applies the patch with zero fuzz, compiles the
complete Linux module plus the test-only IR1 child module, then links the probe.
Run `run_mac_linux.py` with the same mounts and
`jevdual/results/cua-ambiguous-write-ir2-20261101` mounted at `/results`.
Use `/workspace/footwork/bin/python` from the image for both scripts. Set
`IR2_FROZEN_COMMIT` to the exact Footwork commit holding this package.

Docker flags for both commands: `--rm --init --network none --cpus 2 --memory
3g --memory-swap 3g --pids-limit 256 --read-only --cap-drop ALL
--security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,size=512m`.
The run writes only inside `/work`, `/results` and its private `/tmp`. Execute
the build before the run. Never mount the host Docker socket, desktop sockets,
home directory or credentials into this container.

The 14 selected cases cover both actual helper boundaries and the public native
retained-reference setter, plus direct-timeout and deliberate-double-effect
controls. They do not execute the registered TypeTextTool/SetValueTool, a full
Footwork CLI, or the separate `run_steps` batch owner. Those remain separate
qualification boundaries.
