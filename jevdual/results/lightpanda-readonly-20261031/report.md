# Read-only Lightpanda qualification

Runtime source: `2b5325edfbab95e095343d0c36ad5544db92d114`, based on merged PR18.
The source-matched pure-Python wheel has SHA256
`373a43fcccb905ae70fef7f63cb53a478ee40537134384fcc4d534787f43edbb`.

`footwork browser lightpanda read URL` now returns bounded DOM text from one fresh owned engine
and one authenticated private Unix connection. The route is explicit in tools, doctor, schema,
guide and artifact. It offers no input commands or action references. Typing stays disabled.

## Artifact and checks

The external engines are prebuilt artifacts, separate from the Footwork wheel. No engine source
build or model call was used. The rolling release tag is not a source revision.

| Host artifact | GitHub asset ID | SHA256 |
| --- | --- | --- |
| macOS arm64 | 694148451 | `273a4659510f8c48e6c5f26a2eee6aa20051632210cbf0f59975ac705056c44f` |
| Linux x86-64 | 694146173 | `19f3fee25fb14bb75a1e0c1e0f8ab9cce842950544e4a144fbad3884c94b98a3` |

The local binary reports `1.1.0-nightly.11423+56980afde`. The reference checkout is clean at
`49d717daba2c694ef1f02889ea49ca02fbb881a6`; the used handlers are unchanged from the binary's
reported source `56980afdec3ad177072e7a180cb05da838bc1744`.
[Grounding](grounding.json) records exact ranges and hashes, including the null `baseURL` writer
and the distinction between registered frames and DOM iframe elements. No upstream test suite
was run, and source inspection is separate from Footwork runtime qualification.

The final source suite passed **2,786 tests**, with 95 skipped and 66 browser/live checks deselected.
The exact installed wheel passed **308 checks** on macOS and in hosted Linux CI, without CUA or
browser-use. All 155 installed Python files matched source. The public command also read the
documented HTTPS example; its [receipt summary](https-macos.json) retains no page content.
The authorized VM chat also passed all 308 checks on the same wheel and completed one HTTPS read.
The parent compared all 15 copied test hashes with the candidate. The VM verified 211 installed
product files against the wheel. See the [verification ledger](verification.json) and
[origin manifest](vm/origin-manifest.json) for the compact receipt bundle and links to the full records.

The VM measured a 4-CPU quota and 16-GiB memory limit. Its clean repeat had no monitor gap, zero
extra cleanup signals and no final owned descendants. The outer test harness separately reaped
204 zombies. A prior attempt passed its 308 JUnit cases but lost monitor wait/cleanup custody after
ProcessLookupError; that failure remains [explicitly unresolved](vm/monitor-failure-assessment.json).
The diagnostic sampler changed for one preregistered fresh-consumer repeat; product code and all
15 tests remained unchanged. Neither the clean repeat nor test-only reaping establishes global
orphan absence. No 2-CPU/8-GB run occurred.

## What was challenged

| Requirement | Kind | Evidence and boundary |
| --- | --- | --- |
| One original child, one peer-checked connection and real target | Historical action | Launch/transport controls and installed real-engine fixtures; no STARTUP or second-browser probe |
| Useful JavaScript-populated page text | Answer | Literal fixture heading, link and script-populated text; DOM text makes no visibility claim |
| Field values and password-length variants withheld | Answer | Positive content controls, two different password lengths, equal projected content and absence of private markers |
| No input or later action authority | Historical observation | Public CLI/library refusals, empty actions, false mutation authority, typed method allowlist and zero fixture POSTs |
| Bounded timeout and interruption | Current state | Slow initial load, SIGTERM client and forced engine loss; cleanup reported separately, no reconnect |
| No guessed link base or child-frame content | Answer | Red/green base-href controls and real DOM omission; non-HTTP child metadata validation is modeled |
| Existing Chromium authority preserved | Historical action | Existing holder, guard, durable admission, replay and restart checks in the same installed gate |

Cleanup uses the original child handle and a bounded inventory. Forced engine loss reports
unverified cleanup. Test-only captured-process cleanup or orphan reaping is not product cleanup,
business completion or a claim that every descendant was inventoried.

## Failures retained and review disposition

The first source run used a relative `PYTHONPATH`; five subprocess tests changing directories lost
the package path. The [failed invocation](regression-relative-path-failure.txt) is retained. The
corrected absolute-path invocation passed without changing product code or assertions.

Automated review found two real projection gaps. A base-href page could receive an incorrect
frame-relative link destination, and an omitted `about:srcdoc` or `data:` child URL could block the
main-page read. [Three red controls](review-before.txt) reproduce both. The correction withholds
destinations when the effective base is unqualified and treats omitted child URLs as bounded,
unexported metadata. Main-page URL restrictions remain in force.

The first real iframe probe expected two registered child frames; the pinned engine reported zero.
That [failed expectation](review-first-runtime-failure.txt) is retained. The corrected real check
proves omission of iframe DOM content, while actual non-HTTP child metadata remains a modeled
protocol control. No child-frame count or wider iframe support is invented.

A separate context on the inherited model found no actionable defects at the initial source and
reran 119 focused checks. This is independent context, not model-family diversity. The later
automated findings, fixes and rechecks remain separate evidence; PR threads record their disposition.
The prediction-order warning was contradicted by Git: prediction commit `9baa7cb` precedes the
resolving implementation `d9ca03e`; review qualification was predicted in `9b800cb` before its tests.

## README and remaining work

The README revision used the user's explicitly selected local Colophon `paul-graham` profile.
Colophon exported private numeric guidance; this session wrote the candidate without another
writing-provider call. All 149 original protected technical spans, plus the two intended route
additions, passed the [151-span structural check](readme-structural.json). Commands, link targets,
numeric sequence and evidence tables were preserved. That check does not certify factuality or
literary quality. Private guidance, profile data and source passages are excluded.

This route does not claim rendered layout, visibility, atomic capture, task completion or mutable
Lightpanda compatibility. CSS-hidden DOM text can remain. Initial loading runs website code and can
have network effects. There is no mutation admission to bypass a guard.

Footwork still declares its full dependencies. The next install package must qualify binary-only
dependency closure and profile selection; the 2-CPU/8-GB comparative resource baseline remains open.
Existing Linux desktop reliability limits and the Chromium typing focus race remain separate work.
