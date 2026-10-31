from pathlib import Path
import tarfile,io,gzip,hashlib,difflib,json
vendor=Path('/workspace/Footwork/jevdual/vendor/cua-driver');archive=vendor/'native-source.tar.gz';before=archive.read_bytes()
Path('/workspace/scratch/cua-upstream-native-source.tar.gz').write_bytes(before)
root=Path('/workspace/scratch/cua-reliability-source');names=['libs/cua-driver/rust/crates/'+n for n in ['cua-driver-core/src/consent.rs','cua-driver-core/src/browser/engine.rs','cua-driver-core/src/tool.rs','cua-driver-sdk/src/runtime.rs']]
buffer=io.BytesIO();patch=[];manifest={}
with tarfile.open(fileobj=io.BytesIO(before),mode='r:gz') as source,tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as dest:
 for member in source:
  original=source.extractfile(member).read() if member.isfile() else None
  content=(root/member.name).read_bytes() if member.name in names else original
  if member.name in names:
   patch.extend(difflib.unified_diff(original.decode().splitlines(True),content.decode().splitlines(True),fromfile='a/'+member.name,tofile='b/'+member.name))
   manifest[member.name]={'before':hashlib.sha256(original).hexdigest(),'after':hashlib.sha256(content).hexdigest()}
   member.size=len(content)
  dest.addfile(member,io.BytesIO(content) if content is not None else None)
result=io.BytesIO()
with gzip.GzipFile(fileobj=result,filename='',mode='wb',mtime=0,compresslevel=9) as f:f.write(buffer.getvalue())
archive.write_bytes(result.getvalue());digest=hashlib.sha256(result.getvalue()).hexdigest()
(vendor/'patches').mkdir(exist_ok=True)
(vendor/'patches/session-cleanup-join.patch').write_text(''.join(patch))
(vendor/'patches/session-cleanup-join.json').write_text(json.dumps({'upstream_commit':'d5373879e9e0baf5a63999ac4d26902340c0ce20','upstream_archive_sha256':hashlib.sha256(before).hexdigest(),'patched_archive_sha256':digest,'patch_sha256':hashlib.sha256(''.join(patch).encode()).hexdigest(),'files':manifest},indent=2)+'\n')
base=Path('/workspace/Footwork/jevdual')
for name in ['pyproject.toml','uv.lock','vendor/cua-driver/pyproject.toml','vendor/cua-driver/build_support.py','tests/contract/test_cua_driver_seams.py','docs/upstream/cua-driver-build.md']:
 p=base/name;s=p.read_text().replace('0.38.0+footwork.d5373879','0.38.0+footwork.d5373879.cleanup1')
 if name.endswith('build_support.py'):s=s.replace(hashlib.sha256(before).hexdigest(),digest)
 p.write_text(s)
p=vendor/'pyproject.toml';p.write_text(p.read_text().replace('include = ["src",','include = ["patches", "src",'))
p=base/'scripts/build_onboarding_packet.py';p.write_text(p.read_text().replace('    "PROVENANCE.md",','    "PROVENANCE.md",\n    "patches/session-cleanup-join.patch",\n    "patches/session-cleanup-join.json",'))
p=vendor/'PROVENANCE.md';s=p.read_text().replace('0.38.0+footwork.d5373879','0.38.0+footwork.d5373879.cleanup1')
s=s.replace('`native-source.tar.gz` SHA256: `606d8c8696aa54afcff32f285f8f6730a8eef1b6c2b4730372f5ce2b0fe426b1` (5,887,584 bytes).',f'`native-source.tar.gz` SHA256: `{digest}` ({archive.stat().st_size:,} bytes).\n\nThe upstream archive before the local patch has SHA256 `606d8c8696aa54afcff32f285f8f6730a8eef1b6c2b4730372f5ce2b0fe426b1`. The reviewed local diff and per-file before/after hashes are in `patches/session-cleanup-join.patch` and `patches/session-cleanup-join.json`. Only four Rust source files differ; no Cargo dependency, generated Python binding, authorization predicate or other upstream resource changed.')
s=s.replace('These are unmodified upstream source files, including', 'Apart from that explicit Footwork cleanup patch, these are upstream source files, including')
s+='''
## Footwork cleanup1

The SDK closed operation admission and revoked sessions, but browser and protected-grant end hooks spawned untracked asynchronous cleanup. A Debian x86-64 public browser recovery reproduced SIGABRT after shutdown returned; the native stack identified the BrowserEngine session-end task on async-compat/to during Python finalization. The patch owns both hook tasks through the runtime-owned ApprovalBroker and joins them after revocation before shutdown returns. Cancelled drains retain pending joins; task panics prevent successful completion. It changes no consent or input scope. The distribution suffix identifies this local native change; embedded CUA_DRIVER_GIT_SHA still identifies the upstream base, so use it together with the distribution version and archive/wheel hashes. See results/linux-native-reliability-20261030 in the project for retained failure and qualification evidence.
'''
p.write_text(s)
print(digest)
