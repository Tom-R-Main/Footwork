# Q10b stage 1: verifier on oracle end states (dev, 5 calls per task)

| task | oracle | accept | verify | reject | complete (mean) | max unmet (mean) | window text |
|---|---|---|---|---|---|---|---|
| calc-multiply | ok | 5 | 0 | 0 | 0.97 | 0.05 | '12×11 / 132' |
| calc-subtract | ok | 5 | 0 | 0 | 0.97 | 0.05 | '250-75 / 175' |
| calc-percent | ok | 5 | 0 | 0 | 0.96 | 0.06 | '240×15% / 36' |
| calc-read-result | ok | 5 | 0 | 0 | 0.93 | 0.27 | '9×9 / 81' |
| textedit-type-sentence | ok | 5 | 0 | 0 | 0.96 | 0.08 | 'note.txt / The lantern arrived broken.' |
| textedit-append-line | ok | 0 | 5 | 0 | 0.82 | 0.37 | 'draft.txt / First line. / Second line.' |
| textedit-read-word-count | ok | 0 | 5 | 0 | 0.48 | 0.49 | 'words.txt / brass lantern compass' |
