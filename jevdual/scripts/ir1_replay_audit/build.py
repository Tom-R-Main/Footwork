"""Offline compile using exact Cargo-fingerprint-selected existing artifacts.

No Cargo.lock/manifest/production function is edited. Only an audit cfg module
is appended in a task-owned copy. Full pinned Linux source is compiled, not a
copied mutation function/model. Original dependency features are preserved.
"""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

PIN='5588fa808559de5982f9195c1031696f51a67b057164fd42b60485ac6c30b401'


def main():
    package=Path(__file__).resolve().parent
    repo=package.parents[1]
    task=Path(sys.argv[1]);task.mkdir(mode=0o700)
    archive=repo/'vendor/cua-driver/native-source.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==PIN
    source=task/'source';source.mkdir()
    with tarfile.open(archive) as tf:
        for m in tf.getmembers():
            assert not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
        tf.extractall(source,filter='data')
    workspace=source/'libs/cua-driver/rust'
    native=workspace/'crates/platform-linux/src/atspi/native.rs'
    original=native.read_bytes()
    suffix=f'\n#[cfg(ir1_audit)]\n#[path = {json.dumps(str(package/"native_probe.rs"))}]\npub mod ir1_audit;\n'
    native.write_bytes(original+suffix.encode())
    cache=Path('/workspace/Footwork/jevdual/vendor/cua-driver/.native-cache/target/debug')
    fingerprint=next((cache/'.fingerprint').glob('platform-linux-*/lib-platform_linux.json'))
    fp=json.loads(fingerprint.read_text());deps=[];extern=[]
    for _,name,_,wanted in fp['deps']:
        matches=[]
        for f in (cache/'.fingerprint').glob('*/lib-'+name):
            if int.from_bytes(bytes.fromhex(f.read_text().strip()),'little')==wanted:
                suffix=f.parent.name.rsplit('-',1)[1]
                matches += [p for p in [cache/'deps'/f'lib{name}-{suffix}.rlib',cache/'deps'/f'lib{name}-{suffix}.so'] if p.is_file()]
        assert len(matches)==1,(name,matches)
        path=matches[0];extern+=['--extern',f'{name}={path}'];deps.append({'name':name,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    rustc=Path('/workspace/.footwork-setup/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/bin/rustc')
    out=task/'bin';out.mkdir()
    env=dict(os.environ,CARGO_MANIFEST_DIR=str(workspace/'crates/platform-linux'),CARGO_PKG_VERSION='0.38.0',CARGO_PKG_NAME='platform-linux',CUA_DRIVER_GIT_SHA='d5373879e9e0baf5a63999ac4d26902340c0ce20')
    libs=['-L',f'dependency={cache/"deps"}']
    for p in sorted((cache/'build').glob('*/out')):libs+=['-L',f'native={p}']
    libs+=['-L','native=/workspace/.footwork-setup/sysroot/usr/lib/x86_64-linux-gnu']
    command=[str(rustc),'--edition=2021','--crate-name','platform_linux','--crate-type','rlib',str(workspace/'crates/platform-linux/src/lib.rs'),'--cfg','ir1_audit','--cfg','feature="default"','-C','debuginfo=0','-o',str(out/'libplatform_linux.rlib'),*libs,*extern]
    manifest={'archive_sha256':PIN,'production_native_sha256':hashlib.sha256(original).hexdigest(),'test_augmented_native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'production_prefix_byte_identical':native.read_bytes()[:len(original)]==original,'cargo_lock_sha256':hashlib.sha256((workspace/'Cargo.lock').read_bytes()).hexdigest(),'original_feature_fingerprint':fp,'dependency_artifacts':deps,'commands':[command]}
    (task/'build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    p=subprocess.run(command,cwd=workspace,env=env,stdout=(task/'compile.stdout.txt').open('w'),stderr=(task/'compile.stderr.txt').open('w'));manifest['compile_exit']=p.returncode
    (task/'build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if p.returncode:raise SystemExit(p.returncode)
    entry=task/'main.rs';entry.write_text('fn main(){platform_linux::atspi::native::ir1_audit::run();}\n')
    command=[str(rustc),'--edition=2021',str(entry),'--extern',f'platform_linux={out/"libplatform_linux.rlib"}',*libs,'-C','debuginfo=0','-o',str(out/'ir1-probe')]
    manifest['commands'].append(command)
    p=subprocess.run(command,cwd=workspace,env=env,stdout=(task/'link.stdout.txt').open('w'),stderr=(task/'link.stderr.txt').open('w'));manifest['link_exit']=p.returncode
    if p.returncode==0:manifest['probe_sha256']=hashlib.sha256((out/'ir1-probe').read_bytes()).hexdigest()
    (task/'build.json').write_text(json.dumps(manifest,indent=2)+'\n');raise SystemExit(p.returncode)


if __name__=='__main__':main()
