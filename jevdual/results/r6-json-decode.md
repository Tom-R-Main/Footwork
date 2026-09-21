# R6: CDP message decode, stdlib json vs orjson

Median of 15 runs, release orjson wheel, Python 3.12.6.

| fixture | payload MB | json.loads ms (min..max) | orjson.loads ms (min..max) | speedup |
|---|---|---|---|---|
| wikipedia-python | 3.74 | 23.6 (21.6..35.0) | 12.5 (11.5..16.2) | 1.9x |
| amazon-usb-c-hub | 1.85 | 10.9 (10.7..17.1) | 5.6 (5.2..6.6) | 1.9x |
| github-browser-use | 0.75 | 4.5 (4.3..7.4) | 2.5 (2.1..5.9) | 1.8x |

Payload is the DOMSnapshot.captureSnapshot result wrapped as a CDP response, the largest message cdp-use decodes per step.
