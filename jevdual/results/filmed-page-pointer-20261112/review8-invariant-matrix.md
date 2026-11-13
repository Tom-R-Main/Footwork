# The filmed click's invariant, cell by cell

Generated from `tests/test_filmed_click_invariant.py` on the pinned archive (`9f7a7a8e2cc5a7de6c370dffbd7497221ab40a522962599aaa7efb1d2044f698`). 437 cells; in every one the receipt and events equal the oracle's, every event and the focus went to an element the stand-in page had under the pointer, and the unfilmed sequence sent what it sent before the step.

Each cell: what a page listener does (column) at one boundary (row), and what the filmed click then does. "stops" means it returns `left_pointer` having sent exactly the events up to that boundary and nothing after; where the pointer starts on the control itself and on a child of it differ, both are given (control / child).

## An ordinary press

| the page changes | moved | covered | nothing there | sibling | onto control | child removed | removed | cursor none | cursor image | pointer lock |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before the first event | nothing sent | nothing sent | nothing sent | complete, click on label | complete / complete, click on target | – / complete, click on label | nothing sent (removed) | nothing sent (hidden) | nothing sent (hidden) | nothing sent (hidden) |
| in the pointerover listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerenter listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mouseover listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mouseenter listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointermove listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mousemove listener | stops | stops | stops | complete, click on label | complete / complete, click on target | – / complete, click on label | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerdown listener | stops | stops | stops | complete / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mousedown listener | stops | stops | stops | complete / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the focus | stops | stops | stops | complete / complete, click on target | complete / complete, click on target | – / complete, click on target | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerup listener | stops | stops | stops | complete / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mouseup listener | stops | stops | stops | complete / stops | complete / stops | – / complete, click on target | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the click listener | complete | complete | complete | complete | complete | – / complete | complete | complete | complete | complete |

## A pointerdown the page cancels (no mouse events)

| the page changes | moved | covered | nothing there | sibling | onto control | child removed | removed | cursor none | cursor image | pointer lock |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before the first event | nothing sent | nothing sent | nothing sent | complete, click on label | complete / complete, click on target | – / complete, click on label | nothing sent (removed) | nothing sent (hidden) | nothing sent (hidden) | nothing sent (hidden) |
| in the pointerover listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerenter listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mouseover listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mouseenter listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointermove listener | stops | stops | stops | complete, click on label / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mousemove listener | stops | stops | stops | complete, click on label | complete / complete, click on target | – / complete, click on label | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerdown listener | stops | stops | stops | complete / complete, click on target | complete / complete, click on target | – / complete, click on target | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerup listener | stops | stops | stops | complete / stops | complete / stops | – / complete, click on target | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the click listener | complete | complete | complete | complete | complete | – / complete | complete | complete | complete | complete |

## What the command says of each outcome

From `tests/test_filmed_outcome_reporting.py`: every row's text is in the pinned driver's source, the rows cover every variant of the driver's click outcome and every reason its insert function returns, and each is checked at the bridge and through the `do` command.

| outcome | action | the driver's outcome | refusal code | mark | the person is told |
| --- | --- | --- | --- | --- | --- |
| off the point | click | Misplaced | browser_action_unavailable |  | no event was sent |
| pointer hidden | click | Misplaced | browser_action_unavailable |  | no event was sent |
| child frame | click | before | browser_action_unavailable |  | no event was sent |
| no isolated world | click | before | browser_action_unavailable |  | no event was sent |
| gone before the first event | click | Refuse | browser_ref_stale |  | no event was sent |
| left on hover | click | Left | browser_action_unavailable |  | no press or click was sent |
| hidden on hover | click | Left | browser_action_unavailable |  | no press or click was sent |
| left once pressed | click | Left |  | click_stopped_after_press | the click stopped after mousedown and no click event was sent |
| left once released | click | Left |  | click_stopped_after_press | the click stopped after mouseup and no click event was sent |
| hidden once pressed | click | Left |  | click_stopped_after_press | the click stopped after pointerdown and no click event was sent |
| removed once pressed | click | Partial |  | click_stopped_after_press | the click stopped after mousedown and no click event was sent |
| removed once released | click | Partial |  | click_stopped_after_press | the click stopped after pointerup and no click event was sent |
| removed on hover | click | Partial |  | click_stopped_before_press | no press or click was sent |
| threw | click | Interrupted |  | click_interrupted | the click did not report completing (the sequence threw) |
| no receipt | click | Interrupted |  | click_interrupted | the click did not report completing (no completion receipt) |
| malformed receipt | click | Interrupted |  | click_interrupted | the click did not report completing (a malformed receipt) |
| dialog | click | Dialog |  | click_interrupted | a alert dialog opened during the click |
| call failed | click | Failed | error |  | DOM click failed |
| field removed | type | detached | browser_ref_stale |  | nothing was inserted |
| field not focused | type | not_focused | browser_input_trust_unavailable |  | nothing was inserted |
| field not editable | type | not_editable | browser_input_trust_unavailable |  | nothing was inserted |
| field off the point | type | not_under_pointer | browser_action_unavailable |  | nothing was inserted |
| pointer hidden over the field | type | pointer_hidden | browser_action_unavailable |  | nothing was inserted |
| field in a child frame | type | before | browser_action_unavailable |  | nothing was inserted |
| no isolated world for the insert | type | before | browser_action_unavailable |  | nothing was inserted |
| document refused the insertion | type | command_refused | browser_input_incomplete |  | what reached the page is unknown |
| insert threw | type | unknown | browser_input_incomplete |  | what reached the page is unknown |
