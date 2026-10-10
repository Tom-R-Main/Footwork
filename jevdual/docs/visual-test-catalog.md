# Twenty visual task families

Proposed 2026-10-08. The initial authorized pilot is the six recommended families 1,8,11,13,18,20, registered in [D3](experiments/D3-visual-tasks.md). This catalog is a task inventory, not a claim that twenty runnable scenarios or independent real-app validation already exist. Use authored development fixtures separately from an independently collected adoption corpus.

| ID | Surface | Goal | Visual distinction | Independent outcome |
|---|---|---|---|---|
|1|Browser|Activate Crop among similar unlabeled toolbar glyphs|Icon semantics|Editor mode|
|2|Browser|Move an urgent Kanban card into Doing|Source/destination containment|Board data and preserved neighbors|
|3|Browser|Set a custom slider inside a safe band|Thumb versus interval|Actual value within fixed tolerance|
|4|Browser|Choose a date in a dual-month calendar|Repeated numerals/month/disabled state|ISO selected date|
|5|Browser|Match a reference palette color|Color similarity|Selected color tolerance|
|6|Browser|Paste a matrix into a scrolled canvas sheet|Frozen-header row/column alignment|Exact cell contents/neighbors|
|7|Browser|Pause just after a video gate closes|Temporal visual event|Paused annotated time window|
|8|Browser|Select the map pin inside a shaded zone|Spatial inclusion|Point-in-polygon and selected ID|
|9|Browser|Select a chart series using a point tooltip|Point/legend/tooltip association|Actual series/point IDs|
|10|Browser|Scroll an embedded list without moving outer page|Nested viewport boundaries|Inner/outer scroll readback|
|11|Desktop|Move the scanned PDF matching a preview reference|Document identity without filename hints|Correct source hash/destination|
|12|Desktop|Rotate a scan upright|Content orientation|Saved page rotation/content|
|13|Desktop|Crop while preserving the whole subject|Subject/crop boundaries|Saved rectangle and subject geometry|
|14|Desktop|Bold only one clause|Selection extent/typography|Exact saved formatting spans|
|15|Desktop|Align slide objects at bottom edge|Relative geometry|Saved coordinates within tolerance|
|16|Desktop|Connect specified diagram nodes|Connector topology|Saved edge endpoints|
|17|Desktop|Join timeline clips without gap/overlap|Temporal adjacency|Project start/end times|
|18|Desktop|Wait past100%until export finishes|Finalization versus completed effect|Readable completed artifact|
|19|Desktop|Edit correct same-title window|Surface identity/focus|Only intended document changes|
|20|Desktop|Refuse a moved target after capture|Observation freshness|No stale dispatch; fresh-bound action|

Every family needs supported, near-miss and ambiguous evidence, plus a text-rich accessible control. Keep actual DOM/AX/OCR text for every arm. For bounded Decisions questions, use predicates or supplied IDs; generated coordinates/arguments are outside that contract. Preserve native scores/refusals and code-held permission/freshness/target/effect authority.

Grounding sources inspected locally: CUA libs/cua-bench/datasets/cua-bench-basic/README.md and main.py evaluators; browser-use tests/ci/test_image_only_dom_representation.py, test_dom_paint_order_serialization.py, test_coordinate_clicking.py; arc-cua benchmarks/workflows.py and examples/finder_preview/README.md. Reference paths are under /Volumes/External SSD/referencerepos; source audit in [arc-cua reference](arc-cua-decisions-reference.md). These references supply recipes, not independent validation of our new cases.
