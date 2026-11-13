# The filmed click's invariant, cell by cell

Generated from `tests/test_filmed_click_invariant.py` on the pinned archive (`ff12d6a7ac5cc4056e6d7a3f689fbb89e9f7fbceb9ec750186155b609ef19817`). 2090 cells; in every one the receipt and events equal the oracle's, every event and the focus went to an element the stand-in page had under the pointer and inside the ref's node, and the unfilmed sequence sent what it sent before the step.

The two boundary tables below are the 665 cells in which the element a press focuses is the control itself. The third table is the other dimension: where that element is.

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

## A mousedown the page cancels (no focus)

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
| in the mousedown listener | stops | stops | stops | complete / complete, click on target | complete / complete, click on target | – / complete, click on target | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the pointerup listener | stops | stops | stops | complete / stops | complete / stops | – / stops | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the mouseup listener | stops | stops | stops | complete / stops | complete / stops | – / complete, click on target | stops (removed) | stops (hidden) | stops (hidden) | stops (hidden) |
| in the click listener | complete | complete | complete | complete | complete | – / complete | complete | complete | complete | complete |

## Where the focus goes

For an ordinary press, by where the nearest focusable element of the pressed one is. "same events" counts the cells whose events, the focus aside, are those of the cell with the control focusable: they differ only where the disturbance is made in the focus's own listener and no focus is given, so nothing is disturbed.

| nearest focusable element | cells | cells in which focus is given | focus given to | completed, saying `unfocused` | same events |
| --- | --- | --- | --- | --- | --- |
| the control (the ref's node) | 247 | 100 | target | 0 | 247 |
| the pressed element itself | 247 | 100 | icon, label, target | 0 | 247 |
| a container of the control | 247 | 0 | nothing | 67 | 229 |
| nowhere | 247 | 0 | nothing | 0 | 229 |

Without a point, in the cells with a container focusable, the same function focuses the container: 229 of 247 cells.

With a mousedown the page cancels, no focus is given in any cell, wherever the focusable element is: 0 of 912 cells give one, and 0 say unfocused.

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

A completed click that still has something to say:

| outcome | mark | the person is told | how |
| --- | --- | --- | --- |
| no focus given | focus_not_given | the press moved no focus | on the command's `filmed take:` line; not an error |
