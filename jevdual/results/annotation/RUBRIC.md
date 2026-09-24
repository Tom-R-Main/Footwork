# Labelling rubric: was System 1's choice the right next action?

One row is one step. System 1 (the fast model) saw a task, the page it was on, and a menu of the
controls on that page. It chose an operation and a target. The label answers one question:

**Given the task and what the menu shows, was `s1_operation` on `s1_target` the right next action?**

Labels: `right`, `wrong`, `unclear`. A one-line `reason` for every row.

- `right`: a careful person doing this task on this page would do that action next, or an equally
  good one; the target is the control that advances the task. Typing into the field the task names,
  clicking the link or button the task is about, submitting a form the task asked to submit, opening
  the result the task asked for. "Right" includes any of several equally reasonable next actions.
- `wrong`: the action does not advance the task, or a better next action was plainly on the menu.
  Typing into the wrong field; clicking a decoy (a nav link, an ad, a similar-looking item); typing when
  the field is already filled and the next action is to submit; clicking a control the task said not
  to use; choosing a search box when the target link is already on the page; an operation that does
  not fit the target (type into a button).
- `unclear`: the right action is not decidable from the menu (the control the task needs is not
  listed; the page is not the one the task expects and the menu does not show how to get there; two
  targets are indistinguishable by label). Say which in the reason.

Rules:

1. Judge the decision, not the run. You do not know what happened next; do not guess it.
2. The menu is what System 1 could choose from. A right target missing from the menu makes the row
   `unclear`, not `wrong`.
3. `alternatives` lists the next-best targets with System 1's probabilities. They are context, not
   the answer: a `right` choice can have a close alternative, and a `wrong` one can have none.
4. Operations: `click` opens or activates; `type` enters `value` into the target (the value shown is
   what System 1 meant to type, or `<needs value>` if it had none); `select` picks an option;
   `scroll` moves the page; `done` claims the task is finished on this page. `done` is `right` only if
   the menu and task make it plausible the task is complete on this page.
5. A sign-in step with the credentials the task names is `right` on a sign-in page. A step that types
   a literal from the task into a field that clearly is not for it (a password into a search box) is
   `wrong`.
6. When the task is a chain ("open X, then find Y"), judge against where the chain stands on this
   page: a step that opens X from the start page is `right` even though Y is the goal.
7. Do not open any other file. The packet is all the evidence there is.


## Split labels (protocol 2, from the native set onward)

One row still is one decision, but the answer has three parts, so a right target with a wrong value
or an unsupported completion stops being one blurred `wrong`:

- `target`: was `s1_operation` on `s1_target` the right next action? (`right` / `wrong` / `unclear`,
  the rules above.)
- `argument`: for `type`, `append` and `select`, is `value` the right thing to enter? (`right` /
  `wrong` / `unclear` / `n/a` when the value is `<needs value>` or the operation takes none.) A
  `type` that would overwrite a document to add a line is `wrong` here even when the target is right.
- `completion`: for `done` rows, do `prior_actions` and `window_text` show the task's requirements
  satisfied? (`supported` / `unsupported` / `insufficient` when the packet lacks the evidence, for
  example a Calculator run without its display.) A `done` can be the right stopping point
  (`target` right) while its `completion` is `insufficient`; do not turn missing evidence into
  `wrong`.

Packets under this protocol carry `window_text` (what the model saw before acting) and
`prior_actions` with their effects, and carry no confidence scores, probabilities or routing reasons:
you judge the decision, not the model's opinion of it. Write `{"key", "target", "argument",
"completion", "reason"}` per row. Calculator: an operand order that reaches the result through the
percent key is right whichever operand comes first; a digit that no valid sequence from the keys
already pressed can use is wrong; when the display is missing and the order matters, `unclear`.
