# Discover an untitled native panel

Use `footwork apps` to find the intended process, then read only its on-screen windows:

```sh
footwork windows --pid 24992
footwork start 'Navigate own folder panel' --app 'Google Chrome' --pid 24992 --window-id 326559 --session runs/folder-panel
```

Use IDs from a fresh inventory; the example numbers are not current targets. The
inventory emits JSON with genuine SDK titles, retaining `null` or `""` for untitled
windows. It neither selects nor activates a window, captures its contents, changes
a session, nor establishes modal-parent/key-window association. `start` and later
actions retain their existing identity and policy checks.

The request is scoped to one explicit positive PID. Foreign or unreadable owner
IDs, duplicate/invalid window IDs, unreadable titles and over-bound inventories
return an error with no selectable rows. Listing is limited to 256 rows, 5 seconds
for the SDK read and 2 seconds for cleanup. No raw driver diagnostics or foreign
titles are printed. A failed or empty inventory does not fall back to another PID.
