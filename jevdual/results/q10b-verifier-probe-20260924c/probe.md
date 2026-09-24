# Q10b stage 1: verifier on oracle end states (dev, 5 calls per task)

| task | oracle | accept | verify | reject | complete (mean) | max unmet (mean) | window text |
|---|---|---|---|---|---|---|---|
| textedit-append-line | ok | 0 | 5 | 0 | 0.66 | 0.39 | 'draft.txt / First line. / Second line.' |
| textedit-read-word-after | ok | 0 | 5 | 0 | 0.61 | 0.15 | 'words.txt / brass lantern compass' |
