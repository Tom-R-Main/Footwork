"""Owned native qualification; runtime site and output root are explicit arguments."""
import argparse,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--site',type=Path,required=True);ap.add_argument('--wrapper',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--interrupt',action='store_true');ap.add_argument('--loss',choices=['none','disconnect','truncated'],default='none');args=ap.parse_args()
sys.path.insert(0,str(args.site));ROOT=args.root.absolute();ROOT.mkdir();BASE=ROOT.parent;PY=Path('/Users/thomasmain/projects/footwork/jevdual/.venv/bin/python');FW=[str(PY),str(args.wrapper)];AUTH=ROOT/'authority.sqlite'
import json,subprocess,time,sqlite3,hashlib,os,signal,psutil
from jevdual import ax
from jevdual.app_oracles import create_fixture,check_finder,check_preview
from jevdual.app_qualification import HandoffRun,TicketStore,artifact_identity
from jevdual.session_operations import SessionOperations
from ApplicationServices import AXUIElementPerformAction
SUMMARY={'root':str(ROOT),'posture':'exclusive_desktop','loss':args.loss,'interrupt':args.interrupt,'events':[],'kills':[],'limits':['reserved desktop; no active-human coexistence claim']}
def save(): (ROOT/'summary.json').write_text(json.dumps(SUMMARY,indent=2))
def cli(label,words,session,check=True):
 r=subprocess.run(FW+words+['--session',str(ROOT/session)],capture_output=True,text=True,timeout=120);(ROOT/(label+'.txt')).write_text(r.stdout+r.stderr);event={'label':label,'words':words,'exit':r.returncode,'summary':[x for x in (r.stdout+r.stderr).splitlines() if 'driver says' in x or 'stopped:' in x]};SUMMARY['events'].append(event);save();print(json.dumps(event),flush=True)
 if check and r.returncode:raise RuntimeError(label+' CLI refused')
 return r
def state(session):return json.loads((ROOT/session/'session.json').read_text())
def rows():
 with SessionOperations(AUTH) as o:
  out=[o.receipt(x) for x in o.status()]
 (ROOT/'authority.json').write_text(json.dumps(out,indent=2));return out
def op(token):return next(x for x in rows() if x['client_token']==token)
def applied(token):
 x=op(token)
 if (x['state'],x['disposition'])!=('final','applied'):raise RuntimeError(token+' has unsettled custody: '+str(x['error']))
 return x['operation_id']
def start(app,name,title,extra=()):
 cli(name+'-start',['start','Owned full native qualification','--app',app,'--window',title,'--authority',str(AUTH),'--mode','exclusive_desktop',*extra],name)
def checkpoint(name):
 if not args.interrupt:return
 ready=ROOT/(name+'-ready.json');code='import sys,json,signal;from pathlib import Path;sys.path.insert(0,'+repr(str(args.site))+');from jevdual.app_qualification import HandoffRun;r=HandoffRun(Path('+repr(str(ROOT))+'),Path('+repr(str(AUTH))+'),"qualified-full-chain");\nwith r._owned() as (o,s):\n Path('+repr(str(ready))+').write_text(json.dumps({"completed":[r["stage"] for r in s["completed"]]}));signal.pause()'
 child=subprocess.Popen([str(PY),'-c',code],start_new_session=True)
 for _ in range(100):
  if ready.exists():break
  if child.poll() is not None:raise RuntimeError('checkpoint helper exited')
  time.sleep(.02)
 else:raise RuntimeError('checkpoint timeout')
 child.kill();child.wait(timeout=5);SUMMARY['kills'].append({'boundary':name,'returncode':child.returncode,'checkpoint':json.loads(ready.read_text())});save()
def close_document(name):
 st=state(name);w=ax.window_element(st['pid'],st['window_id']);button=ax._attr(w,'AXCloseButton');assert button is not None;err=AXUIElementPerformAction(button,'AXPress');time.sleep(.15)
 try:ax.window_element(st['pid'],st['window_id']);gone=False
 except ax.AXError:gone=True
 SUMMARY[name+'_closed']={'pid':st['pid'],'window_id':st['window_id'],'ack':err,'gone':gone};save()
 if not gone:raise RuntimeError('owned '+name+' window did not close')
manifest=create_fixture(ROOT/'fixture');asset=ROOT/'fixture/organized/renamed.png';handoff=HandoffRun(ROOT,AUTH,'qualified-full-chain');save()
subprocess.run(['open','-g','-a','Finder',str(ROOT/'fixture/inbox')],check=True)
subprocess.run(['open','-g','-a','Finder',str(ROOT/'fixture/organized')],check=True)
import asyncio
from cua_driver import CuaDriver,ListWindowsInput
from jevdual.finder_targets import bind as bind_file,resolve,resolve_marker
async def wait_finder_ready():
 driver=CuaDriver.create(embedded=True)
 try:
  binding=bind_file(manifest,'file:'+str(ROOT/'fixture/inbox/asset.png'))
  for _ in range(100):
   windows=await driver.list_windows(ListWindowsInput(pid=81134,on_screen_only=True));source_hits=[];dest_hits=[]
   for w in windows.windows:
    try:resolve(81134,w.window_id,binding,manifest);source_hits.append(w.window_id)
    except ax.AXError:pass
    try:resolve_marker(81134,w.window_id,manifest,str(ROOT/'fixture/organized'));dest_hits.append(w.window_id)
    except ax.AXError:pass
   if len(source_hits)==len(dest_hits)==1:return {'source':source_hits[0],'destination':dest_hits[0]}
   await asyncio.sleep(.1)
  raise RuntimeError('unique source and destination not ready')
 finally:await driver.shutdown()
SUMMARY['finder_readiness']=asyncio.run(wait_finder_ready());save()
start('Finder','finder','inbox',['--finder-manifest',str(ROOT/'fixture/fixture.json')]);handoff.begin('finder',session_id=state('finder')['session_id'])
cli('finder-wrong-directory',['do','move','file:'+str(ROOT/'fixture/decoy/asset.png'),str(ROOT/'fixture/organized'),'--no-judge','--token','wrong-directory'],'finder',False)
for token,words in [('rename',['type','file:'+str(ROOT/'fixture/inbox/asset.png'),'renamed.png']),('move',['move','file:'+str(ROOT/'fixture/inbox/renamed.png'),str(ROOT/'fixture/organized')])]:
 cli(token+'-grant',['grant',*words],'finder');cli(token,['do',*words,'--no-judge','--token',token],'finder');applied(token)
SUMMARY['finder_oracle']=check_finder(manifest,'organized/renamed.png').to_record();assert SUMMARY['finder_oracle']['ok'];handoff.complete('finder',[applied('rename'),applied('move')],lambda:check_finder(manifest,'organized/renamed.png'),asset)
cli('move-replay',['do','move','file:'+str(ROOT/'fixture/inbox/renamed.png'),str(ROOT/'fixture/organized'),'--no-judge','--token','move'],'finder');close_document('finder');checkpoint('finder-to-preview')
destination=state('finder')['finder_scope']['destination_window']
from jevdual.finder_targets import resolve_marker
assert resolve_marker(destination['pid'],destination['window_id'],manifest,str(ROOT/'fixture/organized'))==destination
w=ax.window_element(destination['pid'],destination['window_id']);button=ax._attr(w,'AXCloseButton');assert button is not None;SUMMARY['finder_destination_closed']={'window_id':destination['window_id'],'ack':AXUIElementPerformAction(button,'AXPress')};save()
preview_before_pids={p.pid for p in psutil.process_iter(['name']) if p.info['name']=='Preview'}
subprocess.run(['open','-g','-n','-a','Preview',str(asset),'--args','-ApplePersistenceIgnoreState','YES'],check=True)
for _ in range(100):
 preview_processes=[p for p in psutil.process_iter(['name','create_time']) if p.info['name']=='Preview' and p.pid not in preview_before_pids]
 if len(preview_processes)==1:break
 time.sleep(.1)
else:raise RuntimeError('unique new owned Preview process unavailable')
preview_process=preview_processes[0];preview_pid=preview_process.pid
(ROOT/'preview-owner.json').write_text(json.dumps({'pid':preview_pid,'start':preview_process.info['create_time'],'artifact':str(asset)},indent=2))
from ApplicationServices import AXUIElementCreateApplication
from jevdual.finder_targets import file_url_path
for _ in range(100):
 matches=[w for w in ax._attr(AXUIElementCreateApplication(preview_pid),'AXWindows') or [] if file_url_path(ax._attr(w,'AXDocument'))==str(asset)]
 if len(matches)==1:break
 time.sleep(.1)
else:raise RuntimeError('exact owned Preview document not ready')
time.sleep(.25)
start('Preview','preview','renamed.png',['--pid',str(preview_pid)]);assert ax.document_path(state('preview')['pid'],state('preview')['window_id'])==str(asset)
handoff=HandoffRun(ROOT,AUTH,'qualified-full-chain');handoff.begin('preview',session_id=state('preview')['session_id']);cli('preview-menu',['look','--menu-bar'],'preview');cli('rotate',['do','menu','Tools > Rotate Right','--no-judge','--token','rotate'],'preview');applied('rotate')
began=time.time();early=check_preview(manifest,str(asset));SUMMARY['preview_initial_pixels']=early.to_record()
for _ in range(1200):
 check=check_preview(manifest,str(asset))
 if check.ok:break
 time.sleep(.1)
else:raise RuntimeError('saved pixel oracle timed out')
SUMMARY['preview_wait_seconds']=time.time()-began;close_document('preview');check=check_preview(manifest,str(asset));SUMMARY['preview_oracle']=check.to_record();assert check.ok;handoff.complete('preview',[applied('rotate')],lambda:check_preview(manifest,str(asset)),asset);checkpoint('preview-to-chrome');save()
server_log=(ROOT/'server.txt').open('w');code='import sys,runpy;sys.path.insert(0,'+repr(str(args.site))+');runpy.run_module("jevdual.app_qualification",run_name="__main__")';server_args=[str(PY),'-u','-c',code,'--root',str(ROOT/'ticket-fixture')]
if args.loss!='none':server_args+=['--lose-reply-once','--reply-loss',args.loss]
server=subprocess.Popen(server_args,stdout=server_log,stderr=server_log,start_new_session=True)
for _ in range(100):
 try:server_info=json.loads((ROOT/'server.txt').read_text().splitlines()[0]);break
 except (ValueError,IndexError):time.sleep(.05)
else:raise RuntimeError('server startup failed')
profile='--user-data-dir='+str(ROOT/'chrome-profile');subprocess.run(['open','-g','-n','-a','/Applications/Google Chrome.app','--args',profile,'--force-renderer-accessibility','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-sync','--new-window',server_info['url']],check=True)
for _ in range(100):
 hits=[p for p in psutil.process_iter(['pid','cmdline','create_time']) if profile in (p.info['cmdline'] or [])]
 if len(hits)==1:break
 time.sleep(.05)
else:raise RuntimeError('owned Chrome PID unavailable')
chrome=hits[0];(ROOT/'owners.json').write_text(json.dumps({'server':server_info,'chrome_pid':chrome.pid,'chrome_start':chrome.info['create_time'],'profile':profile},indent=2));expected={'request_id':manifest['fixture_id'],'artifact':asset.name,'orientation':'clockwise90','digest':artifact_identity(ROOT,asset)['sha256']};SUMMARY['expected']=expected;(ROOT/'ticket-manifest.json').write_text(json.dumps({'database':server_info['database'],'url':server_info['url'],'expected':expected,'artifact':str(asset),'root':str(ROOT)},indent=2));time.sleep(.4)
async def wait_chrome_ready():
 driver=CuaDriver.create(embedded=True)
 try:
  for _ in range(100):
   windows=await driver.list_windows(ListWindowsInput(pid=chrome.pid,on_screen_only=True))
   hits=[w.window_id for w in windows.windows if w.title=='Footwork owned ticket fixture']
   if len(hits)==1:return hits[0]
   await asyncio.sleep(.1)
  raise RuntimeError('owned Chrome fixture not ready')
 finally:await driver.shutdown()
SUMMARY['chrome_readiness']=asyncio.run(wait_chrome_ready());save()
start('Google Chrome','chrome','Footwork owned ticket fixture',['--pid',str(chrome.pid),'--native-url',server_info['url'],'--native-title','Footwork owned ticket fixture','--ticket-manifest',str(ROOT/'ticket-manifest.json')]);handoff=HandoffRun(ROOT,AUTH,'qualified-full-chain');handoff.begin('chrome',session_id=state('chrome')['session_id'])
for key,value in expected.items():cli('type-'+key,['do','type','textbox:'+key,value,'--no-judge','--token','type-'+key],'chrome');applied('type-'+key)
words=['do','click','button:Register asset','--no-judge','--token','submit']
if args.interrupt:
 log=(ROOT/'submit.txt').open('w');child=subprocess.Popen(FW+words+['--session',str(ROOT/'chrome')],stdout=log,stderr=log,start_new_session=True);killed=False
 for _ in range(12000):
  connection=sqlite3.connect('file:'+server_info['database']+'?mode=ro',uri=True);count=connection.execute('SELECT count(*) FROM ingress').fetchone()[0];connection.close()
  if count and child.poll() is None:child.kill();killed=True;break
  if child.poll() is not None:break
  time.sleep(.005)
 child.wait(timeout=10);SUMMARY['kills'].append({'boundary':'submission-after-ingress-before-CLI-result','returncode':child.returncode,'injection_landed':killed});save()
 if not killed:raise RuntimeError('submission kill injection missed; no repeat permitted')
else:cli('submit',words,'chrome',False)
before=op('submit');SUMMARY['submission_before_reconcile']={k:v for k,v in before.items() if k!='projection'};cli('reconcile',['status','--reconcile'],'chrome');submit=op('submit');SUMMARY['submission_after_reconcile']={k:v for k,v in submit.items() if k!='projection'};applied('submit');SUMMARY['ticket_oracle']=TicketStore.readonly_check(Path(server_info['database']),expected);assert SUMMARY['ticket_oracle']['ok'];native=submit['projection'].get('execution_receipt');SUMMARY['native_submission_receipt_preserved']=native
snapshot=TicketStore.readonly_check(Path(server_info['database']),expected);cli('submit-replay',words,'chrome');cli('reconcile-repeat',['status','--reconcile'],'chrome');SUMMARY['replay_no_additional_ingress']=snapshot['ingress']==TicketStore.readonly_check(Path(server_info['database']),expected)['ingress'];assert SUMMARY['replay_no_additional_ingress'];handoff.complete('chrome',[submit['operation_id']],lambda:TicketStore.readonly_check(Path(server_info['database']),expected),asset);SUMMARY['completed_handoffs']=[x['stage'] for x in json.loads((ROOT/'handoff.json').read_text())['completed']];SUMMARY['status']='passed declared chain';save();rows();print(json.dumps({'status':SUMMARY['status'],'completed':SUMMARY['completed_handoffs'],'ingress':len(SUMMARY['ticket_oracle']['ingress'])}),flush=True)
