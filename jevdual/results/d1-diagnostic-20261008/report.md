# Explicit frozen-request diagnosis

On a8c5b94, one explicit request matching version 1's A12 hash returned HTTP 400 with
invalid_request_error, code array_below_min_length, param questions[2].choices. The sanitized
provider message establishes that at least two choice options are required; this request supplied
one. See result.json. This is a diagnosed request constraint, not an account-access failure.

Reported/retained upper across all earlier requests and this diagnostic is $0.141016194, including
both rejected requests' unknown-usage reservations. Actual billing for those rejections is unknown.
Redaction changed no files. No automatic retries or action dispatch occurred.
