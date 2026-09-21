# B1 spike findings: DualProcessAgent on browser-use 0.13.10

Run: `uv run python scripts/spike_b1.py` (headless Chrome, local page, no model calls).
Four probes: click then done; type, Enter, done; click, scroll, scroll, done; escalate.

## What worked unchanged

- Overriding only `Agent._get_next_action` is sufficient. Setting `state.last_model_output`
  to an `AgentOutput` built from `agent.ActionModel` / `agent.AgentOutput` flows through
  `multi_act`, the tools registry, watchdogs and `_finalize` with no other change.
- History: every S1 step produced an `AgentHistory` item. `interacted_element` resolved for
  index-bearing actions (click, input) and was `None` for scroll/send_keys/done, which matches
  upstream S2 behavior.
- GIF generation and `save_conversation_path` worked for S1 steps once the override calls
  `_handle_post_llm_processing(state, message_manager.get_messages())`, mirroring upstream.
- S2 context sees S1 steps: the `memory` line we put on each S1 `AgentOutput` appeared in
  `message_manager.get_messages()` at the next step, because the message manager renders
  prior steps from history. This is the mechanism that keeps S2's memory from going stale;
  the synthesized line's content is the design surface (C3 bridge).
- Escalation is reachable and contained: returning `None` from the policy ran the stock
  `_get_next_action`; the refusing LLM raised, `_handle_step_error` recorded it as a step
  error, and `run()` ended cleanly at `max_steps` without an exception escaping.
- `history.is_done()` is true after an S1 `done` action.

## What needed a workaround

- `_get_next_action`'s tail (pause/stop checks, callbacks, conversation save) is not factored
  out upstream, so the override duplicates four lines. Candidate for the upstream hook PR (R7).
- The LLM double must expose `provider`, `model`, `name`, `model_name` and
  `_verified_api_keys = True`; `Agent.__init__` logs `llm.provider` and `llm.model` at start.

## Contract findings that change downstream tasks (from A4)

- Tab switching is the `switch` action with `tab_id`; there is no `switch_tab`. `close` also
  takes `tab_id`. C3 bridge must use these names.
- `go_back` takes a free-text `description` only. `input` has `clear`; `done` has
  `files_to_display`; `scroll` takes `(down, pages, index)`.
- Actions flagged `terminates_sequence`: go_back, switch, evaluate, navigate, search. Only one
  action per S1 step is planned, so this does not bite, but D6's micro-loop must not batch them.
- `EnhancedSnapshotNode` has no `is_visible`. Its ten fields are is_clickable, cursor_style,
  bounds, clientRects, scrollRects, computed_styles, paint_order, stacking_contexts,
  input_value, input_checked. R2 must reproduce exactly these; visibility is computed later
  in `DomService`.
- `sensitive_data` is already domain-scoped at dispatch via
  `Registry._replace_sensitive_data(params, sensitive_data, current_url)` using
  `match_url_with_domain_pattern`. D5 builds on this rather than re-implementing it.

## Environment note

Renaming the workspace directory broke the venv's console-script shebangs; `uv sync` did not
repair them. Delete `.venv` and re-run `uv sync` after moving the repo.
