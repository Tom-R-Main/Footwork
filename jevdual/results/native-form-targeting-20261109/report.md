# Native browser form targeting repair

Date: November 9, 2026 (America/Detroit).
Checked implementation: `1763f0926d3466d1cc2298c2b728dd5bf4316b56` on `codex/native-form-targeting`.
Prediction commit: `f720c51`; initial implementation: `ead1312`.

The Namecheap report's projection and audit failures are repaired in local Footwork source and
covered by simulated public CLI scenarios. This is not a live Chrome or DNS qualification.

## Behavior

| Report finding | Repair |
| --- | --- |
| Repeated row actions | Preserve explicit row ancestry; supplement collapsed web groups with bounded direct AX ancestor-name reads. Support `section:example.test::link:MANAGE`. Revalidate role, label, section and placeholder; retain refusal when peers cannot be qualified. |
| Dropdown option hidden by budget | Prioritize popup descendants and text fields before ordinary page controls. Preserve application menu-bar exclusion without discarding genuine popup menus. Add persistent `start --native-menu-cap 240` (default160, range1–1000). Missing selectors distinguish budget/driver incompleteness from absence. |
| Placeholder fields lose identity | Read actual values and placeholders separately before pruning. Qualify fallback names only when all members of their semantic peer group were read. Preserve empty values and stable placeholder labels after typing. |
| Early refusal history missing | Append redacted `attempted_action` records containing selector, reason, observation identities, coverage and ambiguity, with `dispatched=false`. Typed payloads and full page contents are omitted. |

Additional regression boundaries: independent domain-action ledger after reordering; added and
removed/renumbered nameserver fields; final revalidation after select-all; hidden duplicate peers;
long-label truncation; partial supplemental reads; and qualified identity in exact grants and field
receipts. Changes to the pre-pruning text-field roster invalidate pending placeholder selections and
their grants. A delivered select-all remains delivery evidence even when later typing is withheld.
An unqualified readback remains unverifiable, rather than claiming the field is empty.

## Validation

Final command from `jevdual/`:

```sh
.venv/bin/python -m pytest -q -m 'not browser and not live'
```

- [Final full offline suite](pytest-final.txt): **2925 passed,51 skipped,66 deselected,1 failed**.
  The sole failure is `test_cua_driver_version_is_pinned`: the existing environment has
  `0.38.0+footwork.d5373879`, while the repository requires `0.38.0+footwork.d5373879.cleanup2`.
  No dependency was installed or version assertion weakened. [Runtime identity](runtime.json).
- [Changed-file Ruff](ruff-changed.txt): passed. [Repository-wide Ruff](ruff.txt) reports nine
  pre-existing issues confined to unchanged `scripts/ir1_replay_audit/` files.
- [Notebook validation](notebook.txt) and [bundled resource check](resources.txt): passed.
- Independent scoped source review closed its identified findings after the follow-up repair.
  Worker red/green logs for audit, receipt and grant counterexamples remain in
  `output/native-form-targeting/`; initial native counterexample results were captured in tool output,
  not preserved as standalone raw artifacts. The [initial integrated suite](pytest-initial.txt)
  predates the follow-up repair.

## Limits and handoff

The supplemental AX reads are bounded to32 text-field attempts and32 repeated-control attempts
per snapshot. Unknown attributes, unresolved peers and incomplete driver observations cannot
establish universal uniqueness. Context comes from explicit AX names, never nearby page text.
Semantically identical replacements with an unchanged field roster are not distinguished by a
persistent native object ID. These limits remain explicit refusals or qualification gaps.

No live Namecheap form was edited, saved, reloaded or checked for DNS propagation. Server persistence
still requires an independently authorized save-and-reload check. No new driver was installed,
no hosted CI was run, and no push or merge is claimed. The existing project executable imports this
checkout's source; a separate deployed wheel has not been built or qualified.

Usage is documented in [the CLI guide](../../docs/unified-cli.md#native-form-targets).
