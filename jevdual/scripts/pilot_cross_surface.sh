#!/bin/sh
# Package G pilot: one browser-to-TextEdit transfer as an integration test, evidence kept per run.
#
#   scripts/pilot_cross_surface.sh [clean|duplicate]
#
# clean      read a price, append it once, save, and check with the workflow oracle
# duplicate  the same, but append the value twice: the oracle must fail with "inserted 2 times"
#
# Acts on this Mac's desktop: footwork's Chrome opens, TextEdit opens a fresh scratch file, and Command-S
# takes the foreground only after 3 s without your input (foreground_permitted). A save whose receipt is
# not confirmed is retried once through File > Save, and the retry is recorded. Everything is kept under
# results/g-pilot-<time>-<variant>/ (sessions, receipts, the file before and after, the oracle's verdict).
set -u
cd "$(dirname "$0")/.."
VARIANT="${1:-clean}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/g-pilot-$STAMP-$VARIANT"; B="$OUT/browser"; T="$OUT/textedit"
DIR="$HOME/footwork-pilot"; NAME="transfer-$STAMP.txt"; FILE="$DIR/$NAME"
mkdir -p "$OUT" "$DIR"; printf 'Price carried from the browser:\n' > "$FILE"
LOG="$OUT/pilot.log"
fw() { echo "\$ footwork $*" >> "$LOG"; uv run footwork "$@" 2>&1 | tee -a "$LOG"; }
step() { echo "== $*" | tee -a "$LOG"; }

step "source: read the first book's price"
fw start "Read the price of the first book" --browser --url https://books.toscrape.com/ --session "$B" > "$OUT/source-observation.txt"
fw read --match '(£[0-9]+\.[0-9]{2})' --as price --session "$B"

step "destination: open a fresh document and snapshot it"
open -a TextEdit "$FILE"; sleep 3
fw start "Append the carried price and save" --app TextEdit --window "$NAME" \
  --mode foreground_permitted --authorize Save --session "$T" > /dev/null
fw snapshot-file "$FILE" --session "$T"
cp "$FILE" "$OUT/file-before.txt"

step "append"
fw do append "text area" @price --from "$B" --session "$T" | grep -E "^(carrying|dispatched|receipt)"
if [ "$VARIANT" = duplicate ]; then
  step "append again (the duplicate case)"
  fw do append "text area" @price --from "$B" --session "$T" | grep -E "^(carrying|dispatched|receipt)"
fi

step "save"
SAVE="$(fw do hotkey cmd s --no-judge --session "$T" | grep -E "^receipt")"; echo "$SAVE"
case "$SAVE" in
  *confirmed*) echo "save: confirmed on the first Command-S" >> "$OUT/recovery.txt" ;;
  *) step "save not confirmed: recovering through File > Save"
     echo "save: first Command-S not confirmed; File > Save used: $SAVE" >> "$OUT/recovery.txt"
     fw do menu "File > Save" --no-judge --session "$T" | grep -E "^receipt" ;;
esac
fw look --session "$T" --text 400 | grep -E "^receipt" || true

step "independent check: the workflow oracle"
fw check-file "$FILE" @price --from "$B" --session "$T" --appended; CODE=$?
cp "$FILE" "$OUT/file-after.txt"
echo "oracle exit $CODE" | tee -a "$LOG"
osascript -e "tell application \"TextEdit\" to close (every document whose name is \"$NAME\") saving no" >/dev/null 2>&1
rm -rf "$B/screenshots" "$T/screenshots"
exit $CODE
