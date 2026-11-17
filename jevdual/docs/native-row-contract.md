# SDK-owned row recipient contract (design boundary)

Authority: Monitor explicitly reopened the closed f65368d feasibility tranche for a bounded change to the pinned CUA fork and minimal Footwork plumbing. The independently reviewed infobar repair is landed and delivered as fdbf48f; this row branch includes that base without widening its authority. Scroll and live input remain excluded.

## Source and ownership

Base Footwork52da, row feasibility f65368d. The owning fork is the vendored source distribution, not a new upstream branch: CUA release5486b6246e4c807c0d793216e52df283671d9362 with cleanup2.focus1.helptag1.connected4.locate10. Base native-source.tar.gz SHA2565cf6ce6a66b06783d8798a3c90e9a82728266326c80b6beab9ff3efe0080ade9. Extracted source and all build outputs stay under the separate SSD row evidence directory; final review uses an inspectable patch, manifest and deterministic archive in this row branch. No upstream publication.

## Implemented contract pending independent review

The existing snapshot seam may publish a versioned expected-row predicate only for a token whose actual retained AX recipient is qualified by the SDK. Footwork does not associate an independent AX object with a token. A row-qualified token is marked as requiring the predicate in SDK-owned snapshot metadata: removing the predicate must not downgrade it to ordinary click.

The typed predicate binds exact PID/window/document URL, one table identified by a complete unambiguous column-header signature, a unique-column locator and its readable value, the complete selected row header-to-cell content tuple, and one descendant role/name/AXPress action. ExpectedRow version2 requires row_values; version1 is refused. A locator is display text, not sufficient recipient identity: Status or a row number can be unique today without identifying the same task tomorrow. All recorded row values must agree between look and do. This prevents locator reassignment only when other recorded content distinguishes the tasks; it is not proof that a mutable locator is a stable application ID. Each cell is mapped by explicit column membership, never its positional index; cells must be distinct, cover every selected-row child, and remain held inside dispatch. The header-to-cell relationship must be explicit in AX; no positional row number, screen geometry or invented label is authority. The full relevant document/table census preserves errors and distinguishes unsupported/absent attributes from failed reads; hidden peers are counted for uniqueness. Aliased references are compared by object equality and cannot inflate or erase conflicting ancestry. Every non-column child edge must match AXParent reciprocally; column-to-cell aliases retain their explicit table relationship. Every AXColumn must be a declared column of an owning AXTable, and each such table is validated before the reciprocity exemption is accepted; orphan or nested columns cannot hide conflicting edges. The unique document must be above the table, which must be above the row and recipient. Missing/duplicate/unreadable identity, nested tables, unsupported column mapping and tokenless controls refuse.

Inside the click adapter, retain the existing focus/window checks. Immediately before a single fixed AXPress, re-read this predicate from the actual held token recipient and the complete relevant census, compare against the admitted predicate and held snapshot references, then mark dispatch. No pixel/key/ordinary SDK fallback. Schema, typed adapter and this production validator must also run in offline fixture tests; a mock must implement AX reads/presses, not return validation success.

Footwork persists the predicate and operation intent through look/do and ordinary/durable records. All selector spellings are resolved against prior intent before refreshing. Missing proof, stale selectors, contradictory no-send/acknowledgement, or basis downgrade refuses or stays unverified; generic page change never confirms a task-specific result. An acknowledged AXPress proves delivery only. The initial effect remains unverified unless a separately specified exact recipient-bound effect is observed; no menu-open or task mutation is inferred.

## Bounded cell representation

Header and locator cells still require one nonempty, unambiguous text value. The non-key cells admit only AXStaticText, AXGroup, AXButton, AXPopUpButton, AXCheckBox, AXImage and AXLink descendants, bounded to 64 objects and 2048 encoded bytes per cell. This expands observation, not the permitted action: only the separately qualified popup/button recipient can receive AXPress. Unsupported roles, failed reads and conflicting ancestry still refuse.

Simple single-text cells retain their existing string representation. Multiple text values, or checkbox/image/link descendants, use a U+001E tag followed by canonical JSON of ordered `(depth, role, name, value)` tuples; object IDs are excluded. A plain value starting with the tag is encoded as a tagged JSON string, which cannot equal the tagged array representation. Duplicate object aliases count once, in first-observed order. The chosen locator remains its literal text value and is independently bound by key_column/key_value. Content/order changes conservatively refuse.

The native collector reads AXValue only for AXCell and AXStaticText. This representation therefore does **not** claim checkbox checked-state, link destination, image pixels, or complete application-state identity. The retained NS-1001 descendant roles are tested with synthetic favorable columns/headers and text; retained observations do not prove that Chrome supplies those relationships. No live attempt is justified solely by that fixture.

## Race and scope limits

AX has no atomic application-side compare-and-press. Holding/checking actual references inside dispatch narrows the race but cannot remove changes after the last read. Across commands, fresh semantic requalification is not object continuity. Same-full-row-value replacement between commands is not universally distinguishable. In particular, tables containing only Status/Actions, #/Actions or #/Status/Actions can redirect when all recorded values are reassigned to another logical task. No content fingerprint can distinguish those cases without an additional stable semantic identifier. They remain explicit unsupported semantic guarantees; a future operator-named identity-column contract is separate work. A peer change can also change the first qualifying locator column and conservatively refuse an unchanged row. Whole-window reciprocal ancestry checks can refuse on an unrelated inconsistent browser-chrome edge; no exception for that topology is added here. Content changes conservatively refuse even if the application considers it the same logical row. Within a token's lifetime, replaced row/key/document/recipient references and identity drift refuse. No automatic retry after possible dispatch.

Footwork offers only click for this row route and refuses other operations. The SDK predicate gate is implemented in click; other raw SDK token-consuming tools do not enforce the row binding. They are not reachable through this Footwork row route and are not qualified by this package. This is an explicit standalone-SDK limitation, not permission for alternate input. An unqualified control sharing role and label with a qualified row control retains ambiguity, even when its sibling gains a section identity.

## Decisive tests and stop rule

Record red public-CLI cases for complete/flattened SDK rows; tokenless stays refused. Exercise actual Rust schema/validation/dispatch adapter through a fixture AX provider and assert ordinary/durable evidence. Include wrong PID/window/document/table/key/recipient, duplicate and unreadable/hidden peers, reorder without identity drift, replacement/key-control swaps, stale selector variants, metadata loss, contradictory dispatch and acknowledgement-only outcomes. Preserve existing named-section/DOM-ID controls and unchanged unrelated routes.

This is built and checked offline, not a delivered or live-qualified capability. If AX cannot expose an explicit column/key relationship or the SDK seam cannot retain required binding with bounded work, stop and report the precise unsupported contract. Do not infer a broader primitive or live discovery authority.

## Recipient-description consumer agreement

`target_label` must be present and equal to the admitted identity label and expected-row name. `native_row.admission` checks the sibling label; `projection_effect` checks the independent admitted predicate and recursively checks any attached execution projection. Both projections explicitly agree on the label. Missing, null, wrongly typed or different labels are evidence errors, even when the effect was already unverifiable.

| Boundary | Shared check | Label regression |
| --- | --- | --- |
| Prepared admission | `native_row.admission` | valid controls and damaged admission copies |
| Producer result to durable retention | `record_execution` → `validate_execution` → `projection_effect` | producer injection before record construction; no corrupt capsule retained |
| Retained historical read | `_retained_execution` / `qualified_receipt` → `validate_execution` | corrupt stored body with matching digest refuses |
| Settlement / reconciliation | `finish_from_execution` / `_reconcile_execution` → retained validation | corrupt no-send cannot release unknown custody |
| Ordinary presentation | `_outside_receipt` → `projection_effect` | direct validator rejection plus unverified ordinary output |
| Attached execution presentation | recursive `projection_effect` | inner and outer corruption independently reject |
| Same-token replay | existing operation projection and ordinary consumer; no new dispatch | producer/retained faults stay unknown, presentation faults stay unverified, no second press |

These cases run across acknowledged delivery, SDK refusal, pre-input error and lost RPC reply using the production Rust row adapter with simulated AX/input. They do not claim application-effect confirmation or authenticate arbitrary external files. Replay does not independently authenticate every historical file: retained reads use the durable validator, while ordinary replay checks the projected copies. No SDK/AX dispatch code changes are needed for this agreement check.

## AXWindow NoValue membership

The held census accepts only AXWindow kAXErrorNoValue (-25212) as a reason to prove membership through AXParent. Each complete held-reference parent chain must remain in the same PID, have reciprocal parent/child membership, and end at the exact window whose native ID was checked. Any explicit non-root AXWindow must equal that window. Unsupported/timeout/other read errors, invalid types, missing parents, cycles, inconsistent aliases and exhausted bounds refuse. The full census still validates every edge/column alias before discovery. Additional chain work is charged to the existing two-second/500000-work budget; the existing 32-parent, 2048-node and 4096-held-reference limits are unchanged.

This is an observation membership proof, not an optional-attribute shortcut. The actual click recipient still requires its explicit AXWindow, and dispatch repeats the census against held token objects before the existing foreground check and press. No across-command object continuity or atomic app-side final-read/press is promised. The motivating retained trace proves only NoValue on a local AXGroup; parent-chain positives are synthetic until a separately authorized live observation establishes actual topology.
