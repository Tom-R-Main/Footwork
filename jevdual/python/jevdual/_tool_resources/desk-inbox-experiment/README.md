# Paper note to a private desk inbox

Turn a saved camera frame into locally recognized text, review it against the paper,
then save one note whose bytes Footwork checks independently. The note is data: its
words never become commands, tasks, or agent instructions.

This isolated experiment uses installed Swift and Apple Vision for English OCR. It
needs no cloud model, microphone, browser automation, or new package installation.
The real Footwork `check-artifact` command verifies the file; no native/browser session
or carried value is fabricated.

## 1. Capture, then prepare

Run from the repository root. Acquire a deliberate frame using the existing camera tool,
or select an already acquired run and token. Use the exact eligible camera name:

```sh
python3 tools/camera-capture-experiment/capture.py capture \
  --run-dir tools/camera-capture-experiment/output/paper-001 \
  --camera 'MacBook Pro Camera' --token paper-001 \
  --allow-permission-prompt --timeout 60

python3 tools/desk-inbox-experiment/inbox.py prepare \
  --capture-run tools/camera-capture-experiment/output/paper-001 \
  --capture-token paper-001 \
  --run-dir tools/desk-inbox-experiment/output/paper-001
```

Preparation reads the original frame through the camera tool's private-directory,
lock, receipt and artifact checks. It does not acquire another frame. An unknown camera
operation cannot supply a note.

Vision uses accurate recognition, `en-US`, and disabled language correction. The result
retains each recognized line, confidence and normalized bounds. OCR remains fallible:
confidence does not establish correctness or authorize saving.

For a known horizontally mirrored frame, add `--mirror-input` to `prepare`. This chooses
Vision's `upMirrored` orientation and mirrors the review display. It retains the original
PNG and hash. The default explicitly uses `up`. Determine direction from readable calibration
text such as `LEFT 123 RIGHT`; the tool does not classify mirror state or choose a setting
from confidence. A different orientation is a different preparation request.

An explicit developer fixture route is available:

```sh
python3 tools/desk-inbox-experiment/inbox.py prepare \
  --fixture-image /absolute/path/to/printed-note.png \
  --run-dir tools/desk-inbox-experiment/output/fixture-001
```

That run is labeled `synthetic_fixture`, including when real Vision processes its image.
It supplies no native-camera acquisition evidence. Inputs must be saved PNGs at most 32 MiB.

## 2. Review the image and text

```sh
open tools/desk-inbox-experiment/output/paper-001/review.html
```

The local page shows the retained image, explicit orientation, original source path,
recognized text and candidate SHA256. All text and paths are HTML-escaped. It has no
scripts, upload route or automatic acceptance. Compare the text with the paper.

The original OCR stays in `ocr.json`; `candidate.txt` joins recognized nonblank lines with
LF and adds one final LF. No text means `needs_text`, with no candidate or inbox note.
Preparation repeats reuse the existing candidate. Changed source bytes or orientation
refuse reuse. An interrupted preparation stays unknown and does not rerun OCR.

If corrections are needed, write a separate reviewed UTF-8 file inside the private run,
then obtain its digest with `shasum -a 256`. Keep `candidate.txt` unchanged. Corrections retain
their exact bytes, including any CRLF or missing terminal newline, and are limited to 128 KiB.
Empty text and NUL bytes are refused. This experiment stores notes, rather than interpreting
their meaning or deciding what should be done.

## 3. Accept and verify

After review, use the exact digest shown for the candidate:

```sh
python3 tools/desk-inbox-experiment/inbox.py accept \
  --run-dir tools/desk-inbox-experiment/output/paper-001 \
  --approved-sha256 REPLACE_WITH_THE_REVIEWED_SHA256

python3 tools/desk-inbox-experiment/inbox.py status \
  --run-dir tools/desk-inbox-experiment/output/paper-001
```

For a corrected file, supply `--reviewed-file /absolute/path/to/reviewed.txt` and its
own approved SHA256. The manifest distinguishes corrected text from original OCR.
Digest approval is the caller's explicit review assertion; it does not authenticate a human
or prove that someone compared the paper.

Acceptance records intent before creating `approved.txt` and `inbox/note.txt`, both private
and create-only. It calls the installed public Footwork CLI:

```sh
jevdual/.venv/bin/footwork check-artifact DESTINATION \
  --expected-file REVIEWED_SOURCE --expected-sha256 APPROVED_DIGEST
```

The checker reads the source, validates its approved SHA256, compares the destination's
raw bytes and rechecks the source. It returns hashes, sizes and a verdict without note
contents. Its 1 MiB limit applies independently to both files; final file symlinks and
nonregular files are rejected. It does not authenticate ancestor directories or provenance.
The desk tool separately requires owned private run directories without symlinks.

Repeating acceptance reads the original operation. It never overwrites or recreates a
missing or altered note. A partial write, lost receipt, interrupted acceptance or failed
checker leaves the operation unknown and blocks replay. There is no reset command.

Status rechecks original/retained image hashes, candidate integrity, approved text and
the note. A later failure leaves the historical saved receipt intact while current state
is unknown with empty claims. Preserve source files and the original capture run so their
retained evidence remains checkable.

The result establishes current file equality to reviewed bytes. It does not establish OCR
accuracy, physical page identity, exposure freshness, native UI completion, exactly-once
camera effects, human-review authentication, or power-loss recovery.

## Files and checks

Each run lives under ignored `tools/desk-inbox-experiment/output/`. Images, OCR, candidate
and approved text, HTML review, Swift cache and diagnostics remain private. Run directories
use 0700; created files use 0600. JSON responses contain paths, hashes and operation state,
but no recognized text. One nonblocking process lock permits one owner per run.

`prepare`, `accept` and `status` return 0 for `needs_review`, `saved` or `absent`; other
states return 2. Footwork `check-artifact` returns 0 for equality and 6 for invalid/mismatched
evidence. Read JSON state as well as the exit code.

```sh
cd jevdual
uv run --no-sync pytest tests/test_artifacts.py tests/test_cli.py tests/test_carry.py \
  ../tools/desk-inbox-experiment/test_inbox.py -q
uv run --no-sync ruff check python/jevdual/artifacts.py python/jevdual/cli.py \
  tests/test_artifacts.py ../tools/desk-inbox-experiment
```

Conformance tests use OCR/process fixtures and the real Footwork file checker. Real Vision
against independently generated normal/mirrored/blank images, and a human's live paper note,
are separate preregistered validations. Neither fixture conformance nor printed-fixture OCR
establishes live handwriting usefulness.

Preregistration: `jevdual/docs/experiments/DI1-desk-paper-inbox.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-desk-paper-inbox.md`.
