# Native browser infobar dismissal

The explicit operator `look`/`do click` route may offer **Dismiss browser infobar**
(reserved observation ID `-3`, section `Native browser`). It is offered only after
an independent, complete bounded native AX census establishes one Infobar
Container, one Infobar alert, one enabled Close offering AXPress, and a unique
native tab group in the exact bound PID/window. Web subtrees cannot qualify it.
An unreadable peer or ambiguous ancestry withholds it. Other Close/menu candidates
retain their existing ambiguity rules. This is not a generic AX or SDK-token API.

Select its exact observed label or ID through ordinary `do click`. It requires
foreground posture, explicit operator intent, and preparation outside filmed takes.
The existing foreground gate still applies. The bridge requalifies before fronting
and immediately before one fixed AXPress, holding actual references within the
operation. No coordinates, cached SDK Close token, fallback or automatic retry is
used. A stale label cannot fall through to an ordinary same-label SDK candidate.

Persistence carries semantic proof and CFHash discriminators; it does not claim
object continuity across commands. AX offers no atomic app-side conditional press.
After dispatch, unreadable/replaced window or tab state stays unverified. The
`ax_infobar_disappearance_readback` basis records an acknowledged press with
readback evidence. Only `effect=confirmed` asserts observed infobar absence with
the same window and tabs retained, plus exactly one acknowledged press.
Acknowledgement without that readback is unverified; prepress refusal records zero
AX attempts even if an observation changed. Ordinary and durable receipts preserve
this boundary; a durable token replay does not press again.

Offline fixtures do not establish live accessibility exposure or timing. Live
qualification requires reviewed installed bytes, fresh exact target and custody.
Page scrolling and row-menu identity are separate, unimplemented scopes here.

The census reads at most 2,048 native nodes, excluding web subtrees. CFHash buckets
only accelerate actual object-equality checks; collisions do not prove identity.
Excessive collision work refuses. Full census AX reads still cost linear work on
operator observations; this has not been measured as live end-to-end latency.

Receipt consumers compare all retained dispatch, count and basis facts, including
the execution projection, before reporting an effect or no attempt. Contradictory
durable capsules are rejected before retention and settlement; the attempt stays
unknown with no automatic retry. A bridge exception explicitly marked before
dispatch writes zero-send facts at the producer. Empty or missing facts alone do
not establish no-send. Older optional projection metadata may be absent; any
retained delivery object must contain the complete, agreeing delivery facts.

The retained delivery object is closed to its six declared fields. Optional
posture/route fields must describe this foreground AX action when present;
attached execution identity and proof copies compare with JSON types preserved.
The session also checks the fixed action's dispatch counter before accepting an
exception's default no-send flag. A marker already observed remains an attempted,
unverified action even if the reply is lost.

Every present binding copy is validated, including boot and process incarnation,
and agrees across the outer projection, attached envelope and inner projection.
Present attempt, observation, session and error copies are typed and agree too.
Historical omissions remain optional; a lone retained value does not authenticate
history that no other copy records. Contradictory attachments can only downgrade
the ordinary receipt; they do not alter the original durable capsule.

Durable validation applies the same provenance agreement before retention, for
sent, no-send and unknown outcomes. Record construction and retention call
`validate_execution`; retained reads call it again; settlement and reconciliation
read through that validator. Ordinary attached presentation checks separately.
The consumer matrix in `tests/test_native_infobar_boundaries.py` injects the same
faults at each boundary, including a matched-digest storage fault and a negative
control that omits only the durable shared check.

Known historical compatibility limit (preexisting): when a successful returned
projection omits its optional `error`, the admission placeholder can reappear in
ordinary presentation. Durable settlement stays correct; ordinary presentation
conservatively says unverifiable. This projection-merge behavior is deferred,
not silently described as preserving the ordinary success classification.
