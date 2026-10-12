# SIM11: Mid-job process restart and browser recovery

Hypothesis: the retained queue, exact command journal and historical body receipts preserve a camera-guided job across process restarts, including after a dispatch reply is lost, without replaying actions.

Predictions if true: restarting the workbench while planning cancels its owned model process and leaves the retained job paused. A visible body outage during planning pauses and cancels the host; reboot preserves body identity and motion state while revoking old leases. Restarting either process with an uncertain dispatch preserves the exact pending command, body and application identities and client send count. Receipt recovery reads the original result, requires explicit Resume and obtains a fresh TCP image before the next decision.

Predictions if false: a restart silently resumes planning, repeats an uncertain command, resets the body or loses its identity, releases an unknown outcome without proof, leaves an orphan model process or completes a job without measurement and reset evidence.

Design: preserve the current paused completed product. Add a separate owned restart harness and independent scorer around the unchanged TCP body, link and browser workbench. Use two new actual Codex jobs in a fresh trial root. On job one, stop/restart the workbench during model planning and later while a dispatch is uncertain. On job two, stop the body during model planning long enough to observe an outage, restart it, and later stop/restart it while a different dispatch is uncertain. All product recovery actions use the real browser. Harness process controls use exact owned PIDs, retained roots and ports, checked public-state predicates and independent journal snapshots. Graceful process termination is the tested interruption; process kill during native file persistence is outside this trial.

Primary metric: all four interruptions recover visibly without another send of the interrupted command, followed by two independently verified continuous native placement/measurement/contact-reset cycles on one body.

Secondary checks: stopped workbench model processes are reaped; body epochs advance and stale leases cannot dispatch; restart is paused or blocked until explicit recovery; retained camera frames cannot grant new authority; a fresh observation precedes the next decision. Reload retains final results. Existing restart conformance and affected guards remain passing.

Guardrails: commit predictions before tests, freeze all measured source before model calls, preserve failing attempts, keep original body/core/client guard source unchanged unless a demonstrated defect requires a separately preregistered repair, use bounded owned process controls, never initialize a retained body again, never replay an uncertain request, no private pose in model inputs and no hidden automatic Resume. Independent native scoring runs only after all trial processes stop. No new remote access or hardware actuation.

Decision rule: report restart recovery verified only if all four product interruptions and the independent scorer pass. If any boundary fails, retain its evidence and report the exact mismatch without promoting unaffected checks to a full pass. Hand off a paused connected product only after successful scoring; otherwise return to the preserved product.

Scope: two actual-model jobs, graceful owned process restarts, same-Mac loopback simulation. Abrupt power loss and torn native writes remain untested.
