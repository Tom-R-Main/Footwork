#!/bin/bash
# Package H live pilot: one grant clears exactly one effect on one resource, on a real Finder window.
# A scratch folder with a.txt and b.txt; the grant is issued for File > Move to Trash with a.txt
# selected; the pilot then checks it does not clear the same menu item with b.txt selected, clears it
# once with a.txt selected, and does not clear a retry. Evidence under results/grants-pilot-<time>/.
set -u -o pipefail
cd "$(dirname "$0")/.."
STAMP="$(date +%Y%m%d-%H%M%S)"; OUT="results/grants-pilot-$STAMP"; S="$OUT/session"
NAME="grants-$STAMP"; DIR="$HOME/footwork-pilot/$NAME"
mkdir -p "$OUT" "$DIR"; echo a > "$DIR/a.txt"; echo b > "$DIR/b.txt"
LOG="$OUT/pilot.log"
fw() { echo "\$ footwork $*" >> "$LOG"; uv run footwork "$@" --session "$S" 2>&1 | tee -a "$LOG"; }
step() { echo "== $*" | tee -a "$LOG"; }
open "$DIR"; sleep 3
step "bind the Finder window"; fw start "Move a.txt to the Trash, nothing else" --app Finder --window "$NAME" --mode foreground_permitted > /dev/null
step "select a.txt, ask to trash: expect a pause"; fw do click a.txt --no-judge | grep -E "^receipt|dispatched"; fw do menu "File > Move to Trash" --no-judge | grep -E "paused|grant"
step "grant exactly that"; fw grant menu "File > Move to Trash"
step "select b.txt, ask to trash: expect the grant not to apply"; fw do click b.txt --no-judge | grep -E "^receipt"; fw do menu "File > Move to Trash" --no-judge | grep -E "paused|not cleared|cleared by"
step "select a.txt again, ask to trash: expect the grant to clear it once"; fw do click a.txt --no-judge | grep -E "^receipt"; fw do menu "File > Move to Trash" --no-judge | grep -E "cleared by|^receipt|paused|not sent"
step "retry: expect no uses left"; fw do click b.txt --no-judge | grep -E "^receipt"; fw do menu "File > Move to Trash" --no-judge | grep -E "paused|not cleared|cleared by"
step "oracle: the folder on disk"; ls "$DIR" | tee "$OUT/folder-after.txt"
if [ ! -e "$DIR/a.txt" ] && [ -e "$DIR/b.txt" ]; then echo "oracle confirmed: a.txt gone, b.txt kept" | tee -a "$LOG"; C=0; else echo "oracle failed" | tee -a "$LOG"; C=6; fi
osascript -e "tell application \"Finder\" to close (every window whose name is \"$NAME\")" >/dev/null 2>&1
rm -rf "$S/screenshots"; exit $C
