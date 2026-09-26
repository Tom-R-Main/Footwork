#!/bin/sh
# Package G pilot: one browser-to-TextEdit transfer with provenance and an exact saved-file oracle.
# Acts on this Mac's desktop: footwork's Chrome opens, TextEdit opens a scratch file, and Command-S
# takes the foreground only after 3 s without your input (foreground_permitted). Run it when the
# desktop may be used. Everything it writes is under ~/footwork-pilot and runs/g-*.
set -eu
cd "$(dirname "$0")/.."
DIR="$HOME/footwork-pilot"; FILE="$DIR/transfer.txt"
B=runs/g-browser; T=runs/g-textedit
mkdir -p "$DIR"; printf 'Price carried from the browser:\n' > "$FILE"
rm -rf "$B" "$T"
fw() { uv run footwork "$@"; }

fw start "Read the price of the first book" --browser --url https://books.toscrape.com/ --session "$B"
fw read --match '(£[0-9]+\.[0-9]{2})' --as price --session "$B"

open -a TextEdit "$FILE"; sleep 3
fw start "Append the carried price and save" --app TextEdit --window transfer.txt \
  --mode foreground_permitted --authorize Save --session "$T"
fw do append "text area" @price --from "$B" --session "$T"
fw do hotkey cmd s --no-judge --session "$T"
fw look --session "$T" --text 400
fw check-file "$FILE" @price --from "$B" --session "$T"
