# SIM3: Repeatable visual work orders

Both the deterministic RGB controller and a fresh image-capable host completed all three
ordinary work orders. Both left the three challenged jobs unresolved. This supports
adopting the bounded episode interface and keeping a conventional controller for movement;
the experiment found no AI advantage in movement completion.

Protocol/case freeze: `5128f37`. Runtime and cold-host documentation freeze: `b9941ef`.
The six parent-selected cases were excluded from implementation development and run once
per participant. No case, runtime or detector settings changed during qualification.

| Observed metric | Deterministic RGB | Fresh host |
|---|---:|---:|
| Attempted cases | 6/6 | 6/6 |
| Completed ordinary jobs | 3/3 | 3/3 |
| Completed across all cases | 3/6 | 3/6 |
| Unresolved challenged jobs | 3 | 3 |
| Case initialization / driver failures | 0 / 0 | 0 / 0 |
| Incorrect completion claims | 0 | 0 |
| Visual false positives observed | 0 | 0 |
| Declared external interventions | 0 | 0 |
| Executed movements | 11 | 13 |
| First-use setup issues | 0 | 1 |

## What changed

Valid rendered images persist before recognition. Packets distinguish acquired images
from recognized, ambiguous or unavailable perception. Case digests bind initial scene,
requested zone, calibration and an eight-action maximum, including completion. Initialization
sets a case's starting position once; motion continues through native MuJoCo contact.

`episode_runner.py` adds doctor, initialization, deterministic baseline, participant finish
and parent-only evaluation commands. Finish records a declaration without scoring it.
Evaluation checks retained historical evidence, current native state and exact saved
software bytes. A satisfied scene alone cannot manufacture motion or software receipts.
Every completion attempt records its visual verdict before the native truth gate, so an
oracle refusal cannot erase an unsupported visual success.

The comparator plans from current RGB-derived boxes and calibration, rather than native
poses or a recorded sequence. Both planners use the same observations, bounds and admitted
effects. The fresh host selected its own targets after inspecting actual images.

## Case outcomes

| Case | Deterministic result / elapsed | Fresh-host result / elapsed |
|---|---|---|
| ordinary-a | completed / 1.14 s | completed / 66.89 s |
| ordinary-b | completed / 1.35 s | completed / 49.85 s |
| ordinary-c | completed / 1.32 s | completed / 55.46 s |
| low-light | unresolved / 0.11 s | unresolved / 11.96 s |
| occlusion | unresolved / 0.11 s | unresolved / 12.45 s |
| camera-shift | unresolved / 0.11 s | unresolved / 10.83 s |

Elapsed time runs from initialization to declared finish. The baseline used one process;
the host incurred model and fresh CLI round trips. These are descriptive observations,
not a controlled performance benchmark or hardware timing measurement.

Ordinary jobs varied starting position and requested zone. Each completed through contact,
a fresh positive visual verdict, qualifying native state and a staged local JSON order
whose saved bytes Footwork checked. Independent scoring found no evidence errors.

Low illumination yielded unavailable recognition. A static render-only occluder yielded
ambiguous block evidence. Camera displacement retained recognized pixel boxes but invalidated
world calibration. All three images remained inspectable; both participants attempted no
motion or computer effect and explained the unresolved jobs. None counts as completion.

## Fresh-host use and retained failures

One fresh Codex context handled all six cases, with within-set learning permitted. It
received public documentation, opaque case paths/digests and owned output paths, without
previous trajectories or baseline results. It inspected 19 images, made 13 movements and
staged three orders. Helpers serialized explicit decisions and parsed public packets;
they did not select targets. Separation relied on instructions on a shared filesystem.
The post-trial self-audit reported no reads of raw cases, native state, implementation,
evaluator or baseline data; this is not adversarial isolation.

Its initial doctor-output redirection failed before doctor executed because the parent
output directory did not exist. First-case initialization created the directory; the host
then ran doctor successfully before viewing or acting, without a parent hint or episode
rerun. This is one retained first-use issue, separate from zero case initialization failures.
Strict doctor-before-init and installation on a clean machine were not demonstrated.

Pre-freeze development found a frame-packet variable NameError. The corrected conformance
suite and retained failure summary are referenced in the notebook. Qualification cases were
not used to repair it. Existing unknown-outcome behavior still blocks replay; this package
does not add recovery for a disconnected or independently running controller.

## Evidence and limits

- [Comparison totals](comparison.json), [deterministic episodes](baseline-v1.json) and
  [fresh-host scores, declarations and audit](fresh-host-v1.json) retain every attempted case.
- [Checks](checks.json) retain 50 passing native-engine/renderer tests, Ruff output and
  frozen runtime/documentation hashes. [Case freeze](case-freeze.json) records input digests.
- Private native state, images, proposals and receipts remain under
  `tools/physical-workcell/output/sim3-qualification-v1/` in the repository. The read-only
  host scoring pass hashed all run files before and after and found no changes.

Six cases and one host context cannot establish comparative reliability. No observed visual
false positive across these cases is not an accuracy estimate; separate conformance tests
exercise oracle-hidden false positives and incorrect declarations. The setup still uses
known colors, a fixed geometry, bounded forward pushes and the known block-center predicate.
It does not establish whole-part containment, inspection quality or learned recognition.

This remains Python in Footwork's experiment area, backed by MuJoCo's native engine.
It uses the public Footwork artifact checker for a local JSON result. Physical operations
are not yet governed through Footwork's production capability service. Real camera control,
robot hardware and an application workflow are unqualified by SIM3.

## Decision

Keep the deterministic RGB controller for this bounded movement task. AI work-order
interpretation, exception handling and software coordination remain hypotheses, not measured
advantages here. Next, test an independently running controller with status and cancellation,
lost replies and changed controller incarnation. Then bind fulfillment to a versioned local
application order and verify its saved state. Promote an adapter into Footwork core only when
those lifecycle semantics have an actual capability-service caller.
