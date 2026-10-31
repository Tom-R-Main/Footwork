# Lightpanda VM evidence ledger

Final source **2b5325edfbab95e095343d0c36ad5544db92d114**, wheel SHA256 **373a43fcccb905ae70fef7f63cb53a478ee40537134384fcc4d534787f43edbb**: **308/308 passed**, no skips; pytest/wrapper exits 0. One installed HTTPS read succeeded. [Final report and limits](2b5325e-monitored/report.md).

| Retained lane | Outcome |
| --- | --- |
| [Pinned engine preparation](preparation/report.md) | Exact asset verified; guessed --version failed 1, documented version succeeded 0 |
| [Prior d9ca03e artifact](d9ca03e/report.md) | 303/303 passed, one HTTPS read succeeded; prior source/wheel only |
| [First 2b5325e monitor failure](2b5325e-monitor-failure/failure-assessment.json) | JUnit 308 passed, outer monitor exited 1; final wait/cleanup custody unavailable |
| [Single fresh 2b5325e repeat](2b5325e-monitored/report.md) | 308/308 passed, full scoped receipts; one HTTPS read succeeded |

The current VM has a 4-CPU quota and 16-GiB memory cap, not a 2CPU/8GB profile. Real srcdoc/data DOM omission passed, while opaque child metadata is modeled only: the pinned engine reported zero real child frames. Forced engine loss retains cleanup uncertainty. Test-only subreaping and the first monitor's lost custody remain separate from product cleanup claims. Prior PR18 evidence is unchanged. This branch contains notebook/results only; parent owns implementation and PR19 merge.
