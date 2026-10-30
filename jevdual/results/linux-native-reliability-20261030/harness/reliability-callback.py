import subprocess,sys,json,os
from pathlib import Path
out=Path('/work');child=out/'callback.py'
child.write_text('''import asyncio,time,sys,json
import cua_driver as cd
from cua_driver import _native as n
if sys.argv[1]=='delay':
 @n._UNIFFI_RUST_FUTURE_CONTINUATION_CALLBACK
 def callback(handle,code):
  loop,future=n._UniffiContinuationHandleMap.remove(handle)
  loop.call_soon_threadsafe(n._uniffi_set_future_result,future,code)
  time.sleep(.1)
 n._uniffi_continuation_callback=callback
async def main():
 d=cd.CuaDriver.create(embedded=True)
 print('created',flush=True)
 await d.shutdown()
 print('shutdown_returned',flush=True)
asyncio.run(main());print('result_emitted',flush=True)
''')
rows=[]
for case in ['baseline','delay']:
 for i in range(3):
  command=['/workspace/.footwork-setup/sysroot/usr/bin/gdb','--return-child-result','-q','-batch','-ex','set pagination off','-ex','set debuginfod enabled off','-ex','run','-ex','thread apply all bt','--args',sys.executable,'-I',str(child),case]
  r=subprocess.run(command,capture_output=True,text=True,timeout=20)
  (out/f'{case}-{i}.gdb').write_text(r.stdout+r.stderr);rows.append({'case':case,'attempt':i,'returncode':r.returncode});(out/'attempts.json').write_text(json.dumps(rows,indent=2));print(rows[-1],flush=True)
