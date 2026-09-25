"""Fake-bridge boundary probes. No desktop actions or model requests."""
import asyncio,json
from types import SimpleNamespace
from pathlib import Path
from jevdual.desktop_s2 import NativeS2,ChatReply
from jevdual.desktop import StepOutcome
from jevdual.native import menu_from_snapshot
from jevdual.menu import Candidate

OUT=Path(__file__).resolve().parent
class Bridge:
 def __init__(self): self.calls=[]
 async def key(self,nm,key,mods):
  self.calls.append(('key',key,mods));return SimpleNamespace(effect='confirmed',route='fake')
 async def hotkey(self,nm,keys):
  self.calls.append(('hotkey',keys));return SimpleNamespace(effect='confirmed',route='fake')
class Verifier:
 async def judge_destructive(self,*args,**kwargs):raise RuntimeError('simulated unavailable classifier')
async def main():
 nm=menu_from_snapshot(json.loads(Path('tests/fixtures/native/calculator.json').read_text()))
 results={}
 for name,action in [('key',{'name':'key','key':'Delete','modifiers':['cmd']}),('hotkey',{'name':'hotkey','keys':['cmd','delete']})]:
  async def chat(messages):return ChatReply(json.dumps({'note':'probe','action':action}))
  s=NativeS2(chat);b=Bridge();agent=SimpleNamespace(task='Read only',requirements=(),memory=[],secrets=None,bridge=b,steps=[],jev_calls=0)
  gate_calls=[]
  async def deny(*args):gate_calls.append(1);return 'denied'
  s.gate=deny
  o=StepOutcome(1,'s2',nm)
  await s.step(agent,nm,'probe',o)
  results[name]={'fake_dispatch':b.calls,'gate_calls':len(gate_calls),'verdict':o.verdict.kind}
 async def chat(messages):raise AssertionError('not called')
 s=NativeS2(chat,verifier=Verifier());agent=SimpleNamespace(task='Read only',jev_calls=0,steps=[])
 results['classifier_exception_returns']=await s.gate(agent,nm,Candidate(1,'Proceed','button',('click',)))
 (OUT/'probes.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
asyncio.run(main())
