# Model-driven completion: evidence for the requested effect, and bounded recovery

Package set by the 2026-09-29 review of Q19 (measurement consistency, effect-specific completion evidence,
bounded cross-loop recovery). Q19 is closed; its failure classes become development cases with different
resources and content, and the next adoption decision uses fresh independently authored tasks.
Measurement consistency landed first (bc49e13: adjudication apart from raw records, checked start states).

## M1 · prediction · 2026-09-29 10:40
Question: why were three correct model effects not accepted, and can evidence for the requested effect close the gap without accepting wrong ones?
Hypothesis: two of the three are the done decision's evidence model, not the verifier's judgment. H10's done ("QUIET-83 27") was refused by the claim check because the confirmation page lacks the values, though the session's own submit receipt shows them in the submitted URL; the operator's H02 dones were refused because any done text forces `answer_expected`, so a no-fact explanation on a task that asks no answer must carry a page fact. H06 (complete p 0.69 to 0.71, every requirement met) is overall-judgment uncertainty, and the verifier never sees the save readback as evidence, only as a memory line.
Alternatives: Jev distrusts short answers whatever the evidence; or the refusals are right because a generic confirmation page proves nothing about which request was made.
Test: build per-session effect evidence from receipts (save readback naming the file and its equality with the window; a submission whose result URL carries the submitted fields; field holds; carried reads with sources), each tagged current state, event or answer, with its step and limits. Pass it to the verifier as its own section; let claim atoms matching an evidence value count as supported; stop forcing `answer_expected` from done text. Replay the verifier offline on the stored Q19 sessions (development use of a closed evaluation's records, not a rescore) and on negatives built from them: wrong resource (the readback names the neighbour), a duplicated submission, stale evidence (an edit after the save), a generic success page with no submission evidence, a claimed value no evidence holds.
Predicts: operator H02 and model H10 dones accepted; every negative refused; model H06 moves to accept in at least 2 of 3 replays (weakest part).
Against: any negative accepted; H10 still refused with the fields in evidence; H06 unmoved would leave judgment uncertainty for a separate change, not refute the rest.
