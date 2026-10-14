Read-only static review by Claude Opus 5.5 of target57ed816 againstbase268f0fc. No tools or historical evidence reads; one paid invocation, no follow-up paid review. The review preceded completion of current CI and is preserved as given.

# Review of Footwork consolidation 57ed816 against base 268f0fc

**Verdict:** I found no code-level blocker in the shipped product path or in the two repairs you asked me to inspect. The merge still depends on three things the diff can't settle:

1. The full physical rerun of 314 tests has not finished. The original failures were environmental, so the repaired suite should pass, including on Linux CI, before you merge.
2. Commits 445a348 and d931559 must stay reachable after the merge (finding 1).
3. Before publishing the prerelease, scan the exact ZIP 8dc81c… for personal data (finding 5). This gates publication, not the merge.

I had no tools, so everything below is static reading of the diff you pasted.

## The two repairs you asked about

**Controller socket (`tools/physical-workcell/controller.py`, `socket_path`).** The repair is sound:
- **Path length:** the worst case is about `/private/tmp/fw-c-4294967295/<64 hex>.sock`, roughly 99 bytes, under the 104-byte limit.
- **Ancestor checks:** every ancestor must be owned by root or the user, and any group/world-writable one must be sticky. Ancestors are checked with `lstat`, so symlinked parents are refused.
- **Private directory:** it is created with mode 0700, never chmod'ed or repaired, and a symlink race is refused.
- **Uniqueness:** the full SHA-256 of the control path is the socket name, so different checkouts get different sockets.
- **Stale sockets:** cleanup happens only after a refused probe, and only while the control lock is held.
- **Client side:** the client re-checks the socket's owner and mode.
- **Tests:** the 10 new `SocketPathTests` account for 304 → 314 tests.

**Frozen wheel verification (`build_onboarding_packet.verify_committed_wheel`, shared by `build_release_candidate`).** Rebuilding the source tree from commit blobs and reusing the existing `verify_wheel` is the right design. The test shows a later runtime change no longer moves the check. Hardening points are in findings 6–8.

## Findings

### 1. Medium–High (integration): qualification commits may become unreachable after merge
- **Where:** `build_release_candidate.py` (`QUALIFIED_PRODUCT_COMMIT`, `committed_bytes`) and `build_onboarding_packet.verify_committed_wheel`.
- **Trigger:**
  - Both verifiers run `git ls-tree` and `git show` against 445a348 and d931559.
  - If the PR is squash- or rebase-merged and the branch deleted, any commit that exists only on this branch becomes unreachable.
  - Fresh clones won't fetch it, and local `gc` can eventually delete it.
  - From then on, `--verify --source-commit d931559` fails everywhere, and the approved ZIP can no longer be re-verified from the repo.
- **Fix:**
  - Use a true merge commit, or
  - Push annotated tags (for example `qualified-product/445a348` and `release-candidate/d931559`) before deleting the branch.
  - Either way, add a one-line check after merge: `git merge-base --is-ancestor <sha> origin/main` (or confirm the tag resolves).

### 2. Medium (qualification claims): installs from the release bundle record the docs commit as `source_commit`
- **Where:** `capability_clean_install.source_commit`, also used by `capability_installed_trial` and `capability_installed_agent_trial`.
- **Trigger:**
  - Inside the release bundle, `footwork/MANIFEST.json` has `source_commit` set to the release commit (d931559).
  - The product commit (445a348) appears only in `qualification.json`.
  - So any receipt produced from the bundle, including the pending README-only Codex adoption, records d931559 as its provenance.
  - That clashes with `approved_summary`/inventory, which require the agent and guest summaries to carry 445a348.
  - Comparing the adoption receipt with the existing evidence will either fail or need hand-waving.
- **Fix:** the ZIP is frozen, so don't change the helper. Score adoption evidence by the release ZIP's SHA-256 plus `wheel_sha256`, and treat the receipt's `source_commit` as "bundle manifest commit". State this in the adoption scoring plan before collecting evidence. For future bundles, add a `product_source_commit` field.

### 3. Medium (incorrect evidence): the order-handoff qualifier checks the old socket path and doesn't enforce a frozen source
- **Where:** `tools/physical-workcell/qualify_order_handoff.py`.
- **Trigger 1:** `Fixture.cleanup` reports `socket_exists` against `BASE/'output/.s'/<sha[:20]>.sock`. After the repair that path never exists, so the field is always `False` and proves nothing.
- **Fix 1:** use `json.load(control/"controller-binding.json")["socket_path"]`, or `controller.socket_path(control)`.
- **Trigger 2:** `main()` compares only the `HEAD` string and hashes the files. Unlike `qualify_bench`, `qualify_network_body` and the others, it never checks `git show <commit>:<file> == current bytes`. A dirty worktree can therefore be qualified under a clean commit ID.
- **Fix 2:** reuse the freeze pattern from `qualify_network_body.freeze` over `SOURCE_FILES`.

### 4. Medium (claim accuracy): earlier controller and order-handoff results no longer describe current source
- **Trigger:**
  - `controller.py` changed in this PR.
  - `app_handoff.fingerprints`, `order_app.SOURCES`, `qualify_order_handoff.SOURCE_FILES` and the controller binding (`controller_sha256`, `socket_path`) all include it.
  - Historical run directories will refuse to load, and any doc saying the controller/handoff simulation "qualified" now refers to pre-repair bytes.
- **Fix:** in the docs, label those results "qualified at <old commit>; post-repair: conformance tests only (28 controller + 15 agent targeted)". Don't present them as qualifying the head commit.

### 5. Medium (privacy; gates the outward publish): sanitization leaves some identity data in place
- **Where:** `build_release_candidate.sanitized_legacy_json` and the `REPORTS`/`EVIDENCE` copies.
- **Trigger:**
  - The URL branch keeps `file:///Users/<name>/...` unchanged. TextEdit `AXDocument` values are file URLs, so these can appear in evidence.
  - `report.md` files and the two `*-summary.json` files are copied into the public ZIP without any sanitization.
- **Fix, without changing bytes:** before publishing, list and grep the exact ZIP 8dc81c… for `/Users/`, `/home/`, `file://`, `@`, `.local` and the account name.
- **If anything matches:** the bytes can't change without requalification, so treat it as a publication decision.
- **For future builds:** exempt only `http`/`https` URLs, sanitize the path part of `file:` URLs, and sanitize reports and summaries the same way.

### 6. Low: verified bytes and packaged bytes come from separate reads
- **Where:**
  - `build_onboarding_packet.inventory` reads the wheel three times: once for verification, once for the member data, once for `wheel_sha256`.
  - `build_release_candidate.qualification_packet` runs `read_archive(path)` and then `sha(path.read_bytes())` separately.
- **Trigger:** a concurrent writer changes the file between reads, so different bytes are verified than are packaged.
- **Fix:** read once into memory, then hash, verify and parse that buffer (`zipfile.ZipFile(io.BytesIO(data))`).

### 7. Low: the onboarding packet verifier is weaker than the release verifier
- **Where:** `build_onboarding_packet.verify`.
- **Trigger:** member mode bits (a symlink `external_attr`), directory entries and uncompressed size are not checked. A repacked packet with identical member bytes but symlink modes passes this verifier. The guest-side extracted check and the release `read_archive` both catch it.
- **Fix:** reuse `build_release_candidate.read_archive`, or move it into a shared module.

### 8. Low: wheel source reconstruction uses porcelain `git show` and never checks the object type
- **Where:** `verify_committed_wheel` and `committed_bytes`.
- **Fix:**
  - Run `git rev-parse --verify <sha>^{commit}` first, so a tree SHA can't be presented as a "commit".
  - Read blobs with `git cat-file blob <blob-sha-from-ls-tree>` so output is never affected by `show` behaviour or configuration.
  - Pass `-c core.quotePath=off` or keep `-z` everywhere; the docs/helpers `ls-tree` call is not `-z`.

### 9. Low: the measurement database can end up permanently unreadable
- **Where:** `measurement.run`.
- **Trigger:** `sqlite3.connect` creates the file with umask permissions, and `chmod 0600` runs only after the insert. A crash in between leaves a 0644 database, which `read_result` rejects forever, so the bench stays unknown.
- **Fix:** before connecting, pre-create the file with `os.open(path, O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW, 0o600)` if it is absent.

### 10. Low: planner cleanup has two edge cases
- **Where:** `planner_guard.supervise` and `codex_policy.terminate`.
- **Trigger 1:** a descendant that escapes the planner's process group (via `setsid`) is observed but never signalled. Closure proof is then withheld, and every later restart refuses.
  - **Fix 1:** send SIGKILL to observed processes whose identity (pid, uid, start time) still matches, then re-check.
- **Trigger 2:** `terminate()` sends SIGKILL to the guardian after 10 s. The guardian's own worst-case cleanup is about 3 + 3 + 3 s, so it can be killed before writing its closure record. That fails closed, but loses the call.
  - **Fix 2:** raise the host's escalation timeout to about 15 s.

### 11. Low: a non-object proposal crashes `app_handoff submit` with a traceback
- **Where:** `app_handoff.submit`.
- **Trigger:** if the JSON proposal is not an object, `proposal.get` raises `AttributeError`, which the CLI's `main()` doesn't catch.
- **Fix:** call `protocol.fields`, or add an `isinstance(proposal, dict)` check right after decoding.

### 12. Low (documentation friction for the README-only run)
- **Where:** `installed-agent-host.md` step 1.
- **Trigger:** `capability_clean_install` refuses any run directory outside `<extracted footwork>/output`. The doc only says "a new output directory".
- **Fix:** for future docs, state the location explicitly. For the pending adoption run, expect this friction and record it rather than coaching around it.

### 13. Informational (fail-closed by design)
- **`capability_*` `source_commit`:** with Git, it records `HEAD` without checking whether the tree is dirty. The wheel SHA-256 remains the binding product identity.
- **`body_network`:** an accepted non-dispatch command with no result (for example `observe`/`start_job` interrupted by a crash) blocks the body permanently, because there is no read-only recovery path. Document this as an operator-reset scenario.
- **`/tmp/fw-c-<uid>`:** another local user can pre-create it and cause a refusal (denial of service only).
- **`inbox.source_request`:** it reads the capture after releasing the camera lock and doesn't compare against the receipt's SHA-256. A later `status` catches any mismatch.

## Not checked (outside this diff, or needs execution)
- **CI:** whether the job's runner matrix includes macOS, where `sudo apt-get` would fail. Whether Linux procps accepts `ps -axo …,lstart=`, which `planner_guard` uses. The Linux EGL rendering path.
- **Release ZIP contents:**
  - Whether the bundled 445a348 `capability_fixture.py` writes the `cleanup.json` that the release docs tell users to inspect.
  - What the bundled helpers' `source_commit()` actually does (finding 2 assumes it matches this branch).
- **`test_order_app` `retain`:** whether it is exclusive-create. `qualify_order_handoff` rewrites `qualification.json` once per case.
- **`build_capability_wheel.verify`:** its inventory rules (all `.py` files plus `arbiter.toml`) and how they relate to `artifacts.py`/`cli.py` at 445a348 versus the PR head.
- **Agent trial isolation:** whether the trial host (cwd inside the repo, `--setting-sources ""`) loaded the repo's `CLAUDE.md`. Check the init event in the transcript before calling that run independent.
- **Historical evidence:** none of the historical evidence files' contents.
