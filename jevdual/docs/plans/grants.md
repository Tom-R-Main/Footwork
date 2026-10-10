# Grants bound to a resource and an effect (package H, design)

Status: first version built with this document. Source: the secondary audit's second round
(`results/status-audit-20260927/`): "exact action labels alone still permit reuse across different
resources".

## The problem

A grant today is a label (`--authorize "Delete"`, since package B an exact label, not a substring). It
clears that label on any page, any document, any element that carries it, with any arguments, any
number of times. A person who allowed "Delete" on one draft has allowed it on every draft the session
reaches afterwards; a person who allowed appending one value has allowed appending another.

## A grant

> This operation, on this resource, with these arguments, under this precondition, usable this many
> times.

| part | what it binds | taken from |
|---|---|---|
| operation | the route: click, type, append, enter, key, hotkey, menu | the command |
| resource | where: the browser URL or the native window's document path (its AXDocument; the window title when it names no file), and the element: role and label | the observation the grant is issued on |
| arguments | the text typed or appended, the keys, the menu path, as a SHA-256 | the command |
| precondition | the element's current value (SHA-256) when it has one | the observation |
| uses | how many dispatches it clears (default 1) | the command |

The grant is issued against the current observation with the same words as `do`:

    footwork grant append "text area" @price --uses 1
    footwork grant click "Move to Trash"

and `do` consumes it only when every part matches the observation and command at dispatch. A pause
that no grant clears prints which part of each open grant did not match.

## What it must refuse (the tests)

- a different document or page: same label, other location;
- a different selected item: same location, other element;
- a changed argument: another text or another key;
- a changed precondition: the field's value changed since the grant;
- an unexpected retry: a second dispatch on a one-use grant.

Browser tab identity is not enough (the tab can navigate): the URL is part of the resource.

## What it does not change

The label grants (`--authorize`) stay, because the experiments froze them (the task files' authorized
actions); in the operator session they remain available but are the broad form. The gate's keyword
rules, the Jev judgment and the posture run as before: a grant clears the gate's pause for one exact
effect, it does not skip the posture or the live identity check.

## Next

Bounded System 1 execution (package I) uses the same record: System 1 may finish only an action a grant
(or the task's authorized scope) fixes completely.
