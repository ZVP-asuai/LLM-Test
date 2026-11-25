#!/usr/bin/env python3
"""Owner-only: obtain known original documents, run preflight, make a private chat attachment.
Never publishes documents or answers. Requires PyMuPDF; does not run any LLM."""
import argparse, hashlib, json, pathlib, subprocess, sys, urllib.request, zipfile
from pathlib import Path
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--approved',type=Path);p.add_argument('--runtime',type=Path);p.add_argument('--offline',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('output must be new')
    a.output.mkdir(parents=True);a.sources.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.pack) as z:
        lock=json.loads(z.read('source-acquisition-lock.json'));c=json.loads(z.read('delivery-contract.json'))
        script=a.output/'ceb-prepare.py';script.write_bytes(z.read('ceb-prepare.py'))
        if lock['revision']!=c['revision']:raise ValueError('mixed delivery revisions')
    acquisitions={}
    for name,ref in lock['files'].items():
        dest=a.sources/name
        try:
            if not dest.exists() and not a.offline:
                req=urllib.request.Request(ref['url'],headers={'User-Agent':'Mozilla/5.0'})
                with urllib.request.urlopen(req,timeout=45) as r:b=r.read(80*1024*1024+1)
                if len(b)>80*1024*1024 or not b.startswith(b'%PDF-') or hashlib.sha256(b).hexdigest()!=ref['sha256']:raise ValueError('wrong bytes or revision')
                dest.write_bytes(b)
            if not dest.exists():raise FileNotFoundError(name)
            if digest(dest)!=ref['sha256']:raise ValueError('existing PDF differs from acquisition lock')
            acquisitions[name]={'ok':True,'sha256':ref['sha256']}
        except Exception as e:acquisitions[name]={'ok':False,'error':str(e)}
    (a.output/'acquisition.json').write_text(json.dumps(acquisitions,indent=2),encoding='utf-8')
    cmd=[sys.executable,str(script),'--pack',str(a.pack),'--sources',str(a.sources),'--output',str(a.output/'prepared')]
    if a.approved:cmd+=['--approved',str(a.approved)]
    if a.runtime:cmd+=['--runtime',str(a.runtime)]
    subprocess.run(cmd,check=True)
    prepared=a.output/'prepared';pre=read(prepared/'preflight.json')
    # Only task inputs and non-secret contracts. No owner scripts, original full standards, grading or credentials.
    paths=set()
    for t in pre['tasks']:paths.update(t['inputs'])
    for n in ['tasks.json','delivery-contract.json','output-contracts.json','catalog.json','chat-template.json','START.txt']:paths.add('bundle/'+n)
    paths.update('tasks/'+t['id']+'.json' for t in pre['tasks'])
    paths.add('preflight.json')
    out=a.output/'CEB-chat-inputs-private.zip'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(paths):
            f=prepared/name
            if f.is_file():z.write(f,name)
        # Same START at archive root so any chat can locate it; manifest and contracts retained under bundle/.
        z.writestr('START.txt',(prepared/'bundle'/'START.txt').read_bytes())
    with zipfile.ZipFile(out) as z:assert z.testzip() is None
    print('CHAT ATTACHMENT:',out,'bytes',out.stat().st_size)
    print('Standard readiness:',pre['ready_standard'],'/44; documents unapproved/missing remain explicitly listed.')
    print('This is an exploratory attachment, not proof of full readiness. Keep private.')
if __name__=='__main__':main()
