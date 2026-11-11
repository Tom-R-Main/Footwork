# Unnamed native web controls

On macOS, an unnamed AXButton or AXPopUpButton may appear with its exact literal
AXDOMIdentifier as the label and `opaque identifier; accessible name empty` provenance.
This identifier does not establish purpose. Use a fresh `look`, then
`inspect-target <numeric-id> --postcondition '<intended visible effect>'` to inspect
its screenshot and bounds before choosing an action. Existing authorization and
foreground-delivery rules still apply.

Qualification reads the actual empty native title and description, exact bound
role/frame/process/window and closest direct WebArea HTTP(S) URL. A bounded census
of all observed web buttons (including named and disabled peers) detects duplicate
identifiers. Readable empty IDs remain omitted; unreadable peers, over-bound
censuses and identity/name/scope drift remove opaque qualification. Only supported
enabled controls with AXPress are exposed. Named-control peer checks are unchanged.
This covers the observed accessibility projection, not undisclosed controls or
canvas gestures; it never supplies a semantic name for an unknown control.

A named SDK peer lacking a frame may supply census evidence through a complete
bounded native subtree lookup for its exact role and readable native name. The
lookup requires one unique AX object, normal same-process/window/document proof,
and a final unchanged exact name. Known unsupported/no-value attributes are
explicit negative evidence; failed reads remain unknown. Such an unframed peer
is omitted from action candidates. Missing/ambiguous/unreadable/bound-exceeded
lookup, conflicting IDs or document scope still blocks opaque qualification.
