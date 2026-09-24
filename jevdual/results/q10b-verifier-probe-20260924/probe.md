# Q10b stage 1: verifier on oracle end states (dev, 5 calls per task)

| task | oracle | accept | verify | reject | complete (mean) | max unmet (mean) | window text |
|---|---|---|---|---|---|---|---|
| calc-multiply | ok | 4 | 1 | 0 | 0.82 | 0.11 | '12×11 / 132' |
| calc-subtract | ok | 5 | 0 | 0 | 0.89 | 0.09 | '250-75 / 175' |
| calc-percent | ok | 2 | 3 | 0 | 0.78 | 0.10 | '240×15% / 36' |
| calc-read-result | ok | 0 | 5 | 0 | 0.57 | 0.19 | '9×9 / 81' |
| textedit-type-sentence | ok | 5 | 0 | 0 | 0.96 | 0.05 | 'note.txt / The lantern arrived broken.' |
| textedit-append-line | ok | 1 | 4 | 0 | 0.87 | 0.35 | 'draft.txt / First line. / Second line.' |
| textedit-read-word-count | ok | 0 | 5 | 0 | 0.48 | 0.46 | 'words.txt / brass lantern compass' |
