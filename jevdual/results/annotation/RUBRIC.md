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
