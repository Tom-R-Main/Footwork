# Project workbench notes

Link an already reviewed desk note to one exact project and retain an inspectable JSON
and Markdown packet. The packet separates physical-source evidence from caller interpretation
and a proposed next check. It never runs that check or interprets note text as instructions.

This package reuses the desk inbox's saved-source verification and the public Footwork
`check-artifact` command. It opens no camera, calls no provider, creates no remote tasks,
and writes only its own private output. No native/browser session or Carry is fabricated.

## Inputs

Supply a bounded version-1 project catalog:

```json
{
  "version": 1,
  "projects": [
    {
      "namespace": "codex_app",
      "project_id": "abe2a667-dedc-4f3f-9863-62f3d80188bd",
      "label": "footwork",
      "root": "/Users/thomasmain/projects/footwork"
    }
  ]
}
```

The namespace and project ID must match exactly. Labels never select a project; duplicate
labels are allowed, duplicate namespaced identities are refused. The selected checkout must
be an existing canonical absolute directory. The catalog is caller-supplied metadata, not
authenticated identity from Codex. Only the selected entry is bound, so unrelated catalog
changes do not invalidate a packet.

Supply a caller-authored record, with all these fields:

```json
{
  "project": {
    "namespace": "codex_app",
    "project_id": "abe2a667-dedc-4f3f-9863-62f3d80188bd"
  },
  "kind": "experiment",
  "title": "Paper-note handoff",
  "question": "Does a fresh-process status check leave the saved packet unchanged?",
  "interpretation": "The reviewed paper note supplies a starting observation, rather than a completed test.",
  "proposed_next_check": "Record packet hashes, run status in a fresh process, then compare hashes again.",
  "expected_result": "Packet hashes remain unchanged; status retains its artifact checks; the proposed check remains not_run.",
  "references": []
}
```

Supported kinds are `observation`, `question`, `experiment`, `decision`, and `blocker`.
The title is one line, at most 160 characters; other text fields are nonempty and at most
4096 characters. Up to 32 code references use `{ "path": "repo/relative.py", "line": 12 }`.
They must exist inside the selected checkout, without symlinks or escapes, with a valid
positive line number. Secret patterns and dependency/build/data directories are refused.
Reference files are bounded to 1 MiB; metadata inputs to 128 KiB.

These strings remain caller assertions. Neither the catalog nor a record digest authenticates
who wrote them or establishes that the interpretation is correct.

## Link and review

Run from the repository root. Keep inputs private; the parent-owned `output/inputs/` directory
is one possible location. Obtain the exact record-file SHA256 with `shasum -a 256`, then:

```sh
python3 tools/workbench-notes/workbench.py link \
  --desk-run tools/desk-inbox-experiment/output/live-paper-v1 \
  --catalog tools/workbench-notes/output/inputs/catalog.json \
  --record-file tools/workbench-notes/output/inputs/footwork-record.json \
  --record-sha256 REPLACE_WITH_APPROVED_RECORD_DIGEST \
  --run-dir tools/workbench-notes/output/abe2a667-dedc-4f3f-9863-62f3d80188bd/first
```

The source must be a currently verified saved desk note. The tool binds its manifest and
note hashes, original frame provenance, explicit orientation and review kind. Native-camera
sources retain that label; synthetic fixtures remain synthetic. The original desk run and
source files remain untouched and must stay available for later checks.

`record.json` retains the reviewed note text, caller question/interpretation, proposed check,
acceptance criterion, checkout HEAD and optional reference hashes. Its check outcome is always
`not_run`. `record.md` presents the same evidence for review, with caller/source text HTML-escaped.
Open the Markdown file in an editor; the CLI prints paths and verification metadata without
the source note contents.

The tool records intent before create-only publication and calls the real Footwork CLI for
both outputs against digest-bound expected files. It retains `source-note.txt`, the original
caller metadata bytes, expected JSON/Markdown, and the checked published packet.

## Status and project listing

```sh
python3 tools/workbench-notes/workbench.py status \
  --run-dir tools/workbench-notes/output/abe2a667-dedc-4f3f-9863-62f3d80188bd/first

python3 tools/workbench-notes/workbench.py list \
  --project-namespace codex_app \
  --project-id abe2a667-dedc-4f3f-9863-62f3d80188bd \
  --output-root tools/workbench-notes/output/abe2a667-dedc-4f3f-9863-62f3d80188bd
```

Status rechecks retained source/caller bytes and both packets. It preserves historical recording
when present, while missing/tampered evidence makes current state `unknown` with empty claims.
The original caller input must remain available and retain its bound digest.

Repository HEAD/reference drift is reported separately as `unchanged`, `changed`, or
`unavailable`. A changed checkout does not alter the saved packet or erase valid byte checks.
It also does not make the proposed check run. Missing Git or reference context is explicitly
unavailable rather than fabricated.

Repeated `link` with identical binding reads the retained operation without rewriting files.
Changed project/source/metadata/digest conflicts. Interrupted or unknown publication never
replays, and a missing output is never recreated. There is no reset command.

Listing filters exact namespaced identity and returns title, kind, state, context summary and
run directory. It does not print note contents or caller paragraphs. It traverses only owned
private directories under this package's output, skips symlinks and reports exclusions/errors
as incomplete. Listing is capped at 1000 directories. Choose a project subtree to keep it narrow.

## Privacy, limits and verification

Run directories use 0700; created files use 0600. Notes, packet text, references, hashes and
receipts stay under ignored `output/`. One nonblocking process lock permits one owner per run.
The tool makes no writes to the selected checkout or catalog.

Exit code 0 means `recorded`, absent status, or a complete listing. Exit code 2 means refusal,
unknown evidence or incomplete listing. Read JSON state and context alongside the exit code.

Artifact equality establishes saved bytes matching the retained expected sources. It does not
establish OCR truth, interpretation accuracy, catalog authenticity, test completion, physical
causality, current code correctness, or power-loss recovery. This is a local record, with no
Codex sidebar task or project attachment created.

```sh
cd jevdual
uv run --no-sync pytest ../tools/workbench-notes/test_workbench.py -q
uv run --no-sync ruff check ../tools/workbench-notes
```

Tests use uniquely owned synthetic desk runs and temporary repositories, plus real public
Footwork byte checks. They never acquire a camera frame or execute proposed checks. A real
reviewed-note linkage and route profiling belong to separate preregistered runs.

Preregistration: `jevdual/docs/experiments/WB1-project-workbench.md`.
Notebook: `jevdual/docs/notebook/2026-10-10-project-workbench.md`.
