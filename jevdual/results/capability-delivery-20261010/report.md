# Capability delivery preparation

Final source is frozen at `2ea6ff988ce3b7eb3bbf444fc4cee6633f74b690`, against main `8c9478f7afc05be9d00a6919388fb2a2cced33d4`. The final 75-member wheel has SHA256 `9bb0440d7bd981df7dc70bbd22f97861a7ed32a88bf6de7a18c2f46982fef3a7`. Initial delivery checks at `fc525da` used the prior U1-qualified artifact, SHA256 `54a4085c992f7066c105f1ce3772d310725b457858543766ea8958cb2e4a275a`; their receipts remain retained.

The new consumer check builds twice, verifies the artifact inventory/bytes/RECORD/license, creates a private fresh environment and installs only the local wheel offline. From a host directory containing shadow packages, isolated installed CLI calls prove installed module origins, missing-prerequisite strict refusal, and unavailable-journal refusal without creating a journal. The console entry point is also exercised. No native UI or input is used in this delivery package.

Local final artifact runs on Python 3.12.6 and 3.14.7 both pass, with receipts in `py312-final-artifact.json` and `py314-final-artifact.json`. All stage logs and environments remain under the corresponding `output/delivery-package-*` directories. V1/v2 smoke results remain retained; v2 added command recording before dispatch and partial logs on timeout. V3 was an exploratory check of the metadata change before its final source commit; v4 qualifies the committed final artifact.

Claude's final review approved `fc525da` with no blockers, then confirmed its two setup follow-ups closed at `2ea6ff9`: the strict doctor's `packaging` parser is declared directly, and the guide directs automation to generated isolated commands instead of the non-isolated console entry point. Two final empty-cache/private-state dependency installs each resolve 115 binary packages, with every selected version matching U1, including packaging26.3. Both final installed strict doctors exit0 with a compatible parser. Only wheel METADATA and RECORD bytes changed; all product runtime modules and other resources match U1 exactly. `runtime-byte-comparison.json` and the final dependency/doctor receipts record this distinction. No native input was repeated for the metadata-only follow-up.

Offline full lock regeneration initially failed because the default cache lacked resolution metadata for the broad Python split. The final lock update adds only the two direct dependency metadata entries using the existing resolution; `uv lock --check --offline` passes. The earlier attempt and exploratory v3 remain recorded in `retained-attempts.json`.

Checks against initial delivery source `fc525da`; the 58 affected tests, Ruff and lock check were repeated after the four-file metadata/documentation follow-up:

| Check | Observed result |
| --- | --- |
| Python, `pytest -q -m 'not browser'` | 1473 passed, 27 skipped, 12 deselected |
| Focused completion/setup/installation/notebook tests | 58 passed |
| Browser inspection/experiment/transport Node tests | 97 passed |
| Rust workspace tests, locked and offline | 19 passed |
| Rust formatting and Clippy with warnings denied | Pass |
| Ruff and notebook validation | Pass |
| Workflow YAML structure and embedded shell syntax | Pass |
| Final lock freshness check, offline | Pass |

The separate `capability-package` workflow defines Linux3.12 and macOS-arm64 3.12/3.14 artifact profiles. Both macOS profiles also use the U1 binary-only fresh dependency installer. Existing development CI remains in place. CI candidate artifacts and receipts are retained; no registry publication is configured. Hosted execution is not yet established by these local checks.

The delivery audit also found that the notebook reader parses only the first resolution in combined fields. Individual appended updates close the four already-measured A2/U1 predictions without changing their results or regrading retained failures.

Independent Claude review is approved, bound to `2ea6ff9` by mailbox1791670452579982000 and follow-up1791670667746229000. Hosted CI has not run at this recording boundary; the PR's checks are the authority for its later hosted status. Native qualification is reused from [U1](../clean-installation-20261010/report.md) for byte-identical runtime modules and identical selected dependency versions; the final artifact's installation is checked separately. Existing macOS permissions, one loopback browser fixture and one identified TextEdit document remain its limits. Fresh-OS permission onboarding, direct worker `__main__` diagnostic origin, arbitrary apps and saved-file or whole-goal certification remain unqualified. Major-tag action pins and running the packaging matrix on every PR remain explicit nonblocking CI hygiene/cost choices consistent with existing CI.

## Hosted delivery update

[Draft PR2](https://github.com/Tom-R-Main/Footwork/pull/2) head `75994a7fa423d53428448f50755c1e0544296523` was tested as merge candidate `e30e761a25c1ceb6f7bb036d4bb0c369dc4a8847` against the recorded base. The [packaging run](https://github.com/Tom-R-Main/Footwork/actions/runs/38091091640) passed all three profiles. Downloaded wheels independently verify against the source inventory; all three SHA256 values match the final local artifact. Hosted macOS arm64/Python3.12.10 and3.14.7 binary installs each resolve115packages, with fresh-site origins and the declared26.3 parser. Their permission status is already granted, so this supplies no permission-prompt evidence. `hosted-artifacts.json` preserves the profile results and source identities.

The [main CI run](https://github.com/Tom-R-Main/Footwork/actions/runs/38091091582) also passed:1472 non-browser Python tests,28 skipped,12 deselected;97 Node tests;19 Rust tests; lint, formatting and Clippy. The local macOS count remains1473/27/12; the hosted Linux count is reported separately. No review threads were present in the complete current page. Final evidence-only commits do not change the reviewed runtime or wheel; the PR's current checks remain authoritative for the latest head. No registry publication or merge occurred.
