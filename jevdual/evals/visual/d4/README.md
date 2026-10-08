# D4 target grounding

`evals.d4_target_grounding` implements the committed D4 development repair study.
Twelve authored Chrome toolbar proposals span original, swapped, scaled and second
glyph-style layouts, with supported, near-miss and ambiguous meanings.

Layout0 reuses D3 HTML and question verbatim. Its near-miss original source PNG
was verified byte-identical to frozen D3 B02 during development. New observations
carry fresh timestamps, revisions and run-owned browser/process IDs.

The three arms retain identical observed DOM/AX text and question. Only the PNG
changes: original frame, DOM-rendered inspector outline labelled with offered
target ID, or direct CDP clip of the exact observed target bounds. No bitmap
editing or oracle text enters the provider input. Source-frame and transformed
image hashes, dimensions, scale, timestamps, target binding and phase timings are
retained. Independently captured clips may differ in a few antialiased pixels;
read-only pixel-difference receipts quantify that explicitly.

The default CLI validates committed-capture contracts offline. `--capture --out`
creates fresh evidence; `--run --cases --out --prior-cost` additionally requires
clean committed code/PNGs, existing credentials, and the cumulative $5 cap.
Calls use pooled HTTP, one predicate, 48k body bound, 64k-token reservation, no
retries. Errors, refusals and unknown usage remain receipts.

Repeat0 reconstructs a fresh safe toolbar, compares current content and bound
target, then executes only the native probability-derived acceptance band.
The expected label never blocks an accepted wrong icon. Crop/Rotate effects are
read back separately and wrong effects preserved. Private provider-backed
approval remains disabled; this is neither independent qualification nor a live
autonomous browser journey.
