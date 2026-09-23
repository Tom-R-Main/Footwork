Paired on 54 tasks: A = guarded (q9b-coherent-20260922-050153), B = guarded (q8-q9e-live-dev-20260922-162350)

only in A: ['li-login-[REDACTED:secret_4]']
only in B: ['lh-form-submit-unauthorized', 'lh-form-submit-unauthorized-2', 'li-login-wrong-password', 'ls-order-backpack-unauthorized', 'ls-order-jacket-unauthorized']

| field | A total | B total | mean B−A per task | 95% CI | tasks B better | tasks A better |
|---|---|---|---|---|---|---|
| passed | 51.000 | 48.000 | -0.056 | [-0.130, +0.000] | 0 | 3 |
| steps | 226.000 | 246.000 | +0.370 | [-0.481, +1.111] | 14 | 17 |
| llm_calls | 223.000 | 243.000 | +0.370 | [-0.481, +1.111] | 14 | 17 |
| jev_calls | 82.000 | 78.000 | -0.074 | [-0.333, +0.167] | 9 | 7 |
| cost | 0.380 | 0.373 | -0.000 | [-0.001, +0.001] | 26 | 28 |
| wall_s | 4714.545 | 5858.761 | +21.189 | [-6.895, +56.212] | 33 | 21 |
| unverified | 8.000 | 9.000 | +0.019 | [-0.056, +0.093] | 2 | 3 |

