#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1];inp=root/'docs/ceb/inputs';out=inp/'CEB-offline-inputs.zip'
files={f.relative_to(inp).as_posix():f.read_bytes() for f in (inp/'fixtures').rglob('*') if f.is_file()}
for n in ['context32-preview.txt','context128-preview.txt','context256-preview.txt','tool-service.py','catalog.json','delivery-contract.json','source-approval-template.json','runtime-template.json','output-contracts.json']:files[n]=(inp/n).read_bytes()
for n,p in {'tasks.json':'docs/ceb/tasks.json','START.txt':'docs/ceb/v2/offline-start.txt','README.md':'docs/ceb/inputs/PREPARE.md','ceb-prepare.py':'scripts/ceb-prepare.py','chat-template.json':'docs/ceb/v2/chat-template.json','submission-template.json':'docs/ceb/v2/submission-template.json'}.items():files[n]=(root/p).read_bytes()
inventory=[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(files.items())];files['portable-inventory.json']=(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n').encode()
with zipfile.ZipFile(out,'w') as z:
    for n,b in sorted(files.items()):
        info=zipfile.ZipInfo(n,(2026,11,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None and all(hashlib.sha256(z.read(x['path'])).hexdigest()==x['sha256'] for x in inventory)
    assert not any('reference' in n or 'answer' in n or 'validator' in n for n in z.namelist())
(inp/'portable-sha256.txt').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n')
print('OFFLINE PACK',len(files),'files',out.stat().st_size)
