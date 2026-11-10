"""A loopback page for the live CLI drag check (notebook PD2), and the server that records what it saw.

    python scripts/drag_page.py --out DIR [--port 0]

Prints the URL once listening. The page has a card dragged with pointer events onto a drop zone, and a
range input with a mark under its 75% point. On every pointerup it shows a status line and POSTs its
own event summary to /log, which the server appends to DIR/page-log.jsonl. Those records come from the
page's event handlers, independent of the poster.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TITLE = "footwork drag fixture"
PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>%s</title>
<link rel="icon" href="data:,">
<style>
 body{font:16px -apple-system,sans-serif;margin:24px;user-select:none}
 #board{position:relative;width:760px;height:260px;border:1px solid #bbb}
 #card{position:absolute;left:30px;top:100px;width:120px;height:60px;background:#2b6cb0;color:#fff;
       display:flex;align-items:center;justify-content:center;border-radius:6px;touch-action:none;cursor:grab}
 #zone{position:absolute;left:520px;top:60px;width:200px;height:140px;border:2px dashed #888;
       display:flex;align-items:center;justify-content:center}
 #range{width:400px;margin-top:40px}
 #mark{position:relative;left:%dpx;top:20px;width:40px;height:30px}
</style></head><body>
<div id="board">
 <div id="card" role="button" aria-label="Card A">Card A</div>
 <div id="zone" role="button" aria-label="Done column">Done column</div>
</div>
<input id="range" type="range" min="0" max="100" value="50" aria-label="Volume">
<div><button id="mark" aria-label="Mark 75">75</button></div>
<p id="status" role="status">ready</p>
<script>
const card=document.getElementById('card'), zone=document.getElementById('zone'), range=document.getElementById('range');
let moves=0, grab=null, run={kind:null,moves:0,points:[]};
function begin(kind,e){run={kind,moves:0,points:[[e.screenX,e.screenY,performance.now()]],start:[e.screenX,e.screenY]};}
card.addEventListener('pointerdown',e=>{card.setPointerCapture(e.pointerId);grab={dx:e.offsetX,dy:e.offsetY};begin('card',e);});
card.addEventListener('pointermove',e=>{if(!grab)return;run.moves++;run.points.push([e.screenX,e.screenY,performance.now()]);
  const b=document.getElementById('board').getBoundingClientRect();
  card.style.left=(e.clientX-b.left-grab.dx)+'px';card.style.top=(e.clientY-b.top-grab.dy)+'px';});
card.addEventListener('pointerup',e=>{grab=null;const c=card.getBoundingClientRect(),z=zone.getBoundingClientRect();
  const cx=c.left+c.width/2,cy=c.top+c.height/2;const inside=cx>z.left&&cx<z.right&&cy>z.top&&cy<z.bottom;
  finish(e,{dropped_in_zone:inside});});
range.addEventListener('pointerdown',e=>begin('range',e));
range.addEventListener('pointermove',e=>{if(run.kind!=='range'||!(e.buttons&1))return;run.moves++;run.points.push([e.screenX,e.screenY,performance.now()]);});
range.addEventListener('pointerup',e=>finish(e,{value:+range.value}));
range.addEventListener('lostpointercapture',e=>{if(run.kind==='range'&&!run.done)finish(e,{value:+range.value});});
function finish(e,extra){if(run.done)return;run.done=true;
  const gaps=run.points.slice(1).map((p,i)=>p[2]-run.points[i][2]);
  const rec=Object.assign({kind:run.kind,moves:run.moves,end:[e.screenX,e.screenY],start:run.start,
    max_gap_ms:gaps.length?Math.max(...gaps):null,dpr:devicePixelRatio,points:run.points},extra);
  document.getElementById('status').textContent=run.kind+' moves '+run.moves+' '+JSON.stringify(extra);
  fetch('/log',{method:'POST',body:JSON.stringify(rec)});}
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # the range is 400 px wide; the mark sits under its 75% point (thumb travel is roughly the track)
    page = (PAGE % (TITLE, 400 * 0.75 - 20)).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            with (out / "page-log.jsonl").open("a") as f:
                f.write(body.decode() + "\n")
            self.send_response(204)
            self.end_headers()

        def log_message(self, *a: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{server.server_address[1]}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
