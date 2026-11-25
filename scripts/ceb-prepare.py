#!/usr/bin/env python3
"""Owner-side preflight and task packet builder. No model execution or grading keys."""
import argparse, hashlib, json, re, shutil, sys, urllib.request, zipfile
from pathlib import Path, PurePosixPath
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def safe_extract(z,d):
    total=0;seen=set()
    for n in z.infolist():
        q=PurePosixPath(n.filename); total+=n.file_size
        if q.is_absolute() or '..' in q.parts or '\\' in n.filename or n.filename in seen or ((n.external_attr>>16)&0o170000)==0o120000 or total>200*1024*1024:raise ValueError('unsafe ZIP: '+n.filename)
        seen.add(n.filename)
    z.extractall(d)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack',type=Path,required=True);p.add_argument('--sources',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--approved',type=Path);p.add_argument('--runtime',type=Path)
    p.add_argument('--fetch',action='store_true');p.add_argument('--strict',action='store_true');a=p.parse_args()
    if a.output.exists():p.error('output must be a new directory')
    a.output.mkdir(parents=True);root=a.output/'bundle'
    if a.pack.is_dir():shutil.copytree(a.pack,root)
    else:
        root.mkdir()
        with zipfile.ZipFile(a.pack) as z:safe_extract(z,root)
    c=read(root/'delivery-contract.json');m=read(root/'tasks.json');cat=read(root/'catalog.json')
    if blob(root/'tasks.json')!=c['manifest_blob_sha']:raise ValueError('manifest hash mismatch')
    for x in read(root/'portable-inventory.json'):
        f=root/x['path']
        if not f.is_file() or f.is_symlink() or sha(f)!=x['sha256']:raise ValueError('checksum mismatch: '+x['path'])
    approved=read(a.approved) if a.approved else {};rt=read(a.runtime) if a.runtime else {}
    a.sources.mkdir(parents=True,exist_ok=True);records={};paths={}
    for name,spec in {**c['source_documents'],**c['private_documents']}.items():
        src=a.sources/name;errs=[];rec={'file':name,'edition':spec['edition'],'present':False,'approved':False,'errors':errs,'pages':[]};records[name]=rec
        if not src.is_file() and a.fetch and name in c['source_documents']:
            for url in [cat['files'][name]['url']]+cat['files'][name].get('mirrors',[]):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40) as r:b=r.read(80*1024*1024+1)
                    if len(b)>80*1024*1024 or not b.startswith(b'%PDF-'):raise ValueError('not a PDF or too large')
                    src.write_bytes(b);break
                except Exception as e:errs.append(str(e))
        rec['present']=src.is_file()
        if not rec['present']:continue
        try:
            import fitz
            with fitz.open(src) as doc:
                if doc.is_encrypted or not len(doc):raise ValueError('encrypted/empty PDF')
                rec['original_sha256']=sha(src);rec['original_page_count']=len(doc)
                lock=approved.get(name,{})
                rec['approved']=lock.get('sha256')==rec['original_sha256'] and lock.get('edition')==spec['edition'] and lock.get('reviewed') is True
                selected=spec.get('pages',list(range(1,len(doc)+1)))
                if any(not 1<=i<=len(doc) for i in selected):raise ValueError('requested page outside PDF')
                out=a.output/'documents'/name.removesuffix('.pdf');out.mkdir(parents=True)
                with fitz.open() as dst:
                    for j,i in enumerate(selected,1):
                        dst.insert_pdf(doc,from_page=i-1,to_page=i-1);page=doc[i-1];im=out/f'original-page-{i}.png'
                        if 'pages' in spec:page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False).save(im)
                        rec['pages'].append({'slice_page':j,'original_pdf_page':i,'printed_label':page.get_label() or None,'image':str(im.relative_to(a.output)) if im.exists() else None})
                    subset=out/'selected.pdf';dst.save(subset,garbage=4,deflate=True)
                rec['slice_sha256']=sha(subset);paths[name]=[str(subset.relative_to(a.output))]+[v['image'] for v in rec['pages'] if v['image']]
                if not rec['approved']:errs.append('owner must verify exact edition and approve original SHA-256')
        except Exception as e:errs.append(str(e))
    readiness=[]
    for t in m['tasks']:
        q=c['tasks'][t['id']];issues=[];inputs=[];maps={}
        for n in q['files']:
            names=['tool-service.py','fixtures/tool-catalog.json'] if n=='tool service' else [cat['files'][n]['path']]
            for name in names:
                if not (root/name).is_file():issues.append('missing input: '+name)
                else:inputs.append('bundle/'+name)
            if n in ['spread.pdf','eplan.pdf','pid.pdf']:inputs+=['bundle/'+str(im.relative_to(root)) for im in sorted((root/'fixtures').glob(n[:-4]+'-page-*.png'))]
        for n in q['documents']+q['private_documents']:
            r=records[n]
            if n not in paths:issues.append('missing/unreadable document: '+n)
            else:
                inputs+=paths[n];maps[n]={k:r[k] for k in ['original_sha256','edition','pages','slice_sha256']}
                if not r['approved']:issues.append('unapproved source: '+n)
        for cap in q['runtime']:
            v=rt.get(cap,{})
            if not(isinstance(v,dict) and v.get('verified') is True and v.get('evidence')):issues.append('runtime not verified: '+cap)
        if t['id'] in c['context_policy']:
            v=rt.get('native_'+t['id'],{});target=c['context_policy'][t['id']];n=v.get('input_tokens');r=v.get('reserve_tokens');w=v.get('configured_context')
            if not(isinstance(n,int) and isinstance(r,int) and isinstance(w,int) and target*.9<=n<target and r>0 and n+r<=target<=w and v.get('tokenizer_id') and v.get('direct_injection') is True and v.get('truncation') is False and re.fullmatch('[0-9a-f]{64}',str(v.get('input_sha256')))):issues.append('native context evidence missing')
        readiness.append({'id':t['id'],'profile':t['profile'],'ready':not issues,'issues':issues,'inputs':inputs,'depends_on':q['depends_on']})
        write(a.output/'tasks'/(t['id']+'.json'),{'id':t['id'],'number':t['number'],'prompt':t['prompt'],'clarification':cat.get('clarifications',{}).get(t['id']),'inputs':inputs,'source_maps':maps,'artifacts':q['artifacts'],'runtime':q['runtime'],'depends_on':q['depends_on'],'delivery_revision':c['revision']})
    inv=[{'path':x.relative_to(a.output).as_posix(),'sha256':sha(x)} for x in sorted([*(a.output/'bundle').rglob('*'),*(a.output/'documents').rglob('*'),*(a.output/'tasks').glob('*.json')]) if x.is_file()]
    write(a.output/'prepared-inventory.json',inv)
    report={'delivery_revision':c['revision'],'manifest_blob_sha':c['manifest_blob_sha'],'ready_standard':sum(x['ready'] and x['profile']=='standard' for x in readiness),'ready_all':sum(x['ready'] for x in readiness),'standard_total':44,'total':50,'sources':records,'tasks':readiness,'prepared_sha256':hashlib.sha256(json.dumps(inv,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'scope':'Input/runtime readiness only, not model evaluation or proof of isolation'}
    write(a.output/'preflight.json',report)
    print(f"READY Standard {report['ready_standard']}/44; all {report['ready_all']}/50")
    for x in readiness:
        if not x['ready']:print(x['id']+': '+'; '.join(x['issues']))
    return 2 if a.strict and report['ready_standard']!=44 else 0
if __name__=='__main__':sys.exit(main())
