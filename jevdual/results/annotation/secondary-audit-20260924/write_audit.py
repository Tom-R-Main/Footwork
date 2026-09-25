"""Materialize the reviewer's packet-based judgments, without reading prior model labels."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
WEB = [
('wrong','Product name is bound to Username instead of standard_user.'),
('wrong','Product name is bound to Username instead of standard_user.'),
('unclear','Input contains A, but the resulting message and proposed answer are absent; completion is not established.'),
('wrong','The supplied username tomsmith is being typed into Password.'),
('unclear','Password is the appropriate field, but <needs value> does not establish a correct executable input.'),
('wrong','Repeats the product name already incorrectly present in Username.'),
('right','Password entry follows the specified locked_out_user username; the value is an opaque named password reference.'),
('right','All three requested fields have the requested values; stopping respects the no-submit constraint.'),
('right','Menu shows Nobel Prize in Physics and First award 1901; stopping to answer is plausible. URL conflicts with menu; navigation history is unavailable.'),
('unclear','Username is correct but password occupancy is suppressed; cannot establish that Login is ready.'),
('right','Menu explicitly identifies Capital Canberra; done is plausible under the rubric, without certifying the unseen answer.'),
('wrong','No Delete element remains; this does not show the required two additions followed by one deletion.'),
('right','The requested Python search is already in the search box; Enter submits it.'),
('wrong','Types the username into Password; the task asks for the supplied password.'),
('unclear','Price (low to high) is a role-none label, apparently the current sort label; packet lacks its actionable semantics and product prices.'),
('unclear','KeyError occurs in an exception-context menu, but the defining text and proposed answer are absent.'),
('unclear','KeyError occurs in an exception-context menu, but the defining text and proposed answer are absent.'),
('wrong','Menu contains the requested jacket and cart controls; Back abandons the available forward path.'),
('right','Menu explicitly says Designed by Guido van Rossum; done is plausible, although the URL is stale and the answer is not shown.'),
('unclear','Password is an appropriate next field but its proposed value is unavailable.'),
('wrong','Product name is bound to Username instead of standard_user.'),
('unclear','Password is an appropriate next field but its proposed value is unavailable.'),
('unclear','Cart has one item, but the packet loses the Remove-to-product association and image click semantics; cannot establish whether opening this product is redundant.'),
('wrong','Chooses a role-none aggregate of sort labels while the explicit Sort products combobox is available.'),
('right','Types the specified standard_user into the empty Username field.'),
('wrong','Two Delete controls already exist; another Add Element exceeds the requested two additions.'),
('unclear','Six indistinguishable Add to cart labels lack product sections; ordinal adjacency suggests Backpack but does not establish binding.'),
('wrong','Search the site and CSS navigation are available; scrolling this search/footer menu does not address the requested lookup.'),
('wrong','Two Delete controls already exist; another Add Element exceeds the requested two additions.'),
('unclear','Username is the correct field but <needs value> leaves the executable value unknown.'),
('right','The requested locked-out error is explicitly visible in the menu; done is plausible for reporting it.'),
('wrong','Cart is explicitly empty; adding the requested Onesie should precede checkout.'),
('wrong','Product name is bound to Username instead of standard_user.'),
('right','Enter submits the already-filled exact article search; matching suggestions do not invalidate this equivalent route.'),
('wrong','Product name is bound to Username instead of standard_user.'),
('unclear','Only one Delete remains; without earlier actions cannot tell whether the required deletion already happened.'),
('right','Types the requested Grace Hopper into Customer name; filling does not itself submit.'),
('unclear','Password is the correct next field but no executable value is provided.'),
('right','Enter submits the requested query already present in DuckDuckGo search.'),
('unclear','Delivery instructions is the correct field but the missing proposed value prevents full input validation.'),
]
NATIVE = [
('right','Starting with 15 is a valid arithmetic route to 15 percent of 240; the task does not require entering 240 first.'),
('right','Starting with 15 is a valid arithmetic route; do not label against one oracle sequence only.'),
('right','A second 1 completes the second operand 11 after 12 times 1.'),
('unclear','Percent after 15 may begin 0.15 times 240, but the packet omits display state and percent-key semantics; it is not intrinsically wrong.'),
('right','2 starts the requested first operand 250 after clearing.'),
('right','The requested complete sentence is visible in the text area.'),
('right','5 completes 15 after 1; starting from the percentage is permissible.'),
('unclear','Prior keys form 250 minus 75, but the display and action-effect confirmations are absent from the packet.'),
('unclear','Only Second line. is visible; prior document contents and successful persistence are absent, so append-and-save is not established.'),
('wrong','After the latest All Clear and 2, 0 builds 20 instead of 240; 4 is the direct next key.'),
('wrong','Clears a valid leading 2 after a restart; no observed error supports discarding that operand.'),
('unclear','4 can continue 240 after entry-clear and 2, but retained operator/percentage state is absent.'),
('right','9 starts the requested multiplication after clearing.'),
('wrong','After 15 then Percent, entering 2 omits the multiplication operator required for the intended product.'),
('right','The previous 23 is not an intended operand; Clear is a reasonable recovery.'),
('right','Equals evaluates the complete 9 times 9 expression recorded in prior actions.'),
('right','All Clear is a reasonable recovery after a disrupted sequence of entry-clears.'),
('right','The document exposes brass lantern compass; stopping to report lantern is plausible. This does not certify an unseen answer.'),
('right','All Clear directly follows the task instruction to clear first.'),
('right','All Clear resets a disrupted calculation; no correct result is established.'),
('unclear','The intended subtraction keys were issued, but no resulting display is available to validate done.'),
('unclear','Repeated save attempts are not evidence of persistence or preservation of the original line.'),
('unclear','The packet shows the intended keys but neither the resulting display nor a reported answer.'),
('right','1 starts the first operand 12 after clearing.'),
('unclear','The packet shows the intended keys but neither the resulting display nor a reported answer.'),
('right','The second word is visible in the text area; done is plausible under the rubric, without validating answer delivery.'),
('right','5 completes the initial 15; that arithmetic route is not inherently wrong.'),
('wrong','Clears a valid leading 2 in the second operand with no evidence of an input error.'),
('unclear','The keys form 12 times 11, but the packet omits the display and effect confirmations.'),
('right','After clearing the previous entry, 2 can start the valid operand 240.'),
('right','All Clear is a reasonable reset after an incomplete/misordered expression.'),
('unclear','Text presence and repeated save attempts do not establish a correct append or successful persistence.'),
('right','All Clear satisfies the explicit first instruction.'),
('right','No controls are offered; blocked appropriately hands off an unexecutable state, without claiming a permanent impossibility.'),
('unclear','Three controls are identically labelled button; the packet cannot identify which is a save or window control.'),
('unclear','Three controls are identically labelled button; the packet cannot identify the chosen control function.'),
('right','2 begins 250 after clearing.'),
('right','After clearing the entry, 2 can begin the valid operand 240.'),
('unclear','Intended multiplication keys are present but the result display is absent.'),
('unclear','The packet does not establish retained original content or successful saving.'),
]
manifest={'reviewer':'Codex AI','human_review':False,'fully_blinded':False,'protocol':'Packet-only first pass; prior handoff and aggregate claims already seen; individual model label files not opened before freezing these labels. Missing evidence is unclear. Done means plausible stopping under supplied rubric, not certified answer delivery.','sources':{}}
for tag,base,judgments in [('web',ROOT,WEB),('native',ROOT/'q10',NATIVE)]:
 source=base/'audit-sheet.csv'; rows=list(csv.DictReader(source.open())); assert len(rows)==len(judgments)==40
 manifest['sources'][str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
 fields=list(rows[0])+['audit_reviewer','audit_evidence_scope']
 for row,(label,note) in zip(rows,judgments,strict=True):
  row.update(audit_label=label,audit_note=note,audit_reviewer='Codex AI (not human)',audit_evidence_scope='original blinded packet; no future outcomes')
 with (OUT/f'{tag}-audit.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 manifest[tag+'_audit_sha256']=hashlib.sha256((OUT/f'{tag}-audit.csv').read_bytes()).hexdigest()
(OUT/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
