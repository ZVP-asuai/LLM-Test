#!/usr/bin/env python3
"""Owner-side sequential CEB runner. A trusted, separately sandboxed adapter handles actual LLM calls.
No adapter, model credentials or actual sandbox are supplied by this script.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, signal, shutil, subprocess, sys, time, uuid
from pathlib import Path
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def safe(root,n):
    if not isinstance(n,str):raise ValueError('path must be a string')
    p=root/n
    if not isinstance(n,str) or Path(n).is_absolute() or '..' in Path(n).parts or '\\' in n or not p.resolve().is_relative_to(root.resolve()) or p.is_symlink():raise ValueError('unsafe path '+str(n))
    return p
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--select',nargs='+');p.add_argument('--qualification',action='store_true');p.add_argument('--strict',action='store_true');p.add_argument('--standard-limit',type=float,default=7200);p.add_argument('--qualification-limit',type=float,default=3600);p.add_argument('--worker',nargs=argparse.REMAINDER,required=True);a=p.parse_args()
    if not a.worker or a.output.exists():p.error('trusted worker required; output must be a new directory')
    if not 0<a.standard_limit<=7200 or not 0<a.qualification_limit<=7200:p.error('invalid time limit')
    root=a.prepared.resolve();pre=read(root/'preflight.json');bundle=root/'bundle';manifest=read(bundle/'tasks.json');c=read(bundle/'delivery-contract.json');fmt=read(bundle/'output-contracts.json');run=read(bundle/'submission-template.json')
    inv=read(root/'prepared-inventory.json')
    if hashlib.sha256(json.dumps(inv,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=pre['prepared_sha256']:raise ValueError('prepared inventory mismatch')
    for i in inv:
        f=safe(root,i['path'])
        if not f.is_file() or sha(f)!=i['sha256']:raise ValueError('prepared input changed: '+i['path'])
    if pre['manifest_blob_sha']!=run['manifest_blob_sha'] or pre['delivery_revision']!=c['revision']:raise ValueError('preflight version mismatch')
    rows={x['id']:x for x in pre['tasks']}
    if len(rows)!=50 or set(rows)!={t['id'] for t in manifest['tasks']}:raise ValueError('preflight coverage mismatch')
    if a.strict and (pre['ready_standard']!=44 or any(not rows[t['id']]['ready'] for t in manifest['tasks'] if t['profile']=='standard')):raise SystemExit('Infrastructure not ready: inspect preflight.json before starting.')
    if a.select and not set(a.select)<=set(rows):p.error('unknown selection')
    cfg=read(a.model)
    for k in run['model']:
        if k in cfg:run['model'][k]=cfg[k]
    if not run['model']['name']:p.error('actual model name required')
    # This runner cannot prove sandbox isolation. Never emit submitted or validated.
    run.update(run_id='ceb-'+uuid.uuid4().hex,variant_id='ceb-2.0-'+c['revision'],fixture_sha256=pre['prepared_sha256'],status='incomplete',execution_mode='orchestrated',telemetry_source='external_orchestrator',context_isolated=False,network_isolated=False)
    out=a.output.resolve();out.mkdir();(out/'private').mkdir();answers=[];completed_outputs={};summary={r['id']:r for r in run['tasks']}
    for profile,limit in [('standard',a.standard_limit),('qualification',a.qualification_limit)]:
        start=time.monotonic();stamp=now()
        if profile=='standard':run['started_at']=stamp
        if profile=='qualification' and not a.qualification:continue
        for t in manifest['tasks']:
            id=t['id'];r=summary[id];q=rows[id]
            if t['profile']!=profile:continue
            if a.select and id not in a.select:r['reason_code']='not_selected';continue
            if not q['ready']:r.update(status='blocked',reason_code='missing_input' if any('document' in x or 'input' in x or 'source' in x for x in q['issues']) else 'missing_tool');continue
            if q.get('model_unsupported'):r.update(status='unsupported',reason_code='unsupported_context');continue
            remaining=limit-(time.monotonic()-start)
            if remaining<=0:r['reason_code']='time_limit';continue
            packet=read(root/'tasks'/(id+'.json'))
            deps=packet.get('depends_on',[])
            if any(x not in completed_outputs for x in deps):r.update(status='blocked',reason_code='dependency_failed');continue
            work=out/'private'/id;work.mkdir();(work/'inputs').mkdir();(work/'artifacts').mkdir()
            files=[]
            for n in packet['inputs']:
                src=safe(root,n);dst=safe(work/'inputs',n);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);dst.chmod(0o444);files.append(str(dst.relative_to(work)))
            for dep in deps:
                # Explicit CAD dependency; never pass previous answers or other outputs.
                src=completed_outputs[dep]/'LC1D09B7.step'
                if not src.is_file():break
                dst=work/'inputs'/'LC1D09B7.step';shutil.copyfile(src,dst);dst.chmod(0o444);files.append('inputs/LC1D09B7.step')
            else:
                source_maps=packet['source_maps']
                for name,s in source_maps.items():
                    s['slice_path']='inputs/documents/'+name.removesuffix('.pdf')+'/selected.pdf'
                    for page in s['pages']:
                        if page.get('image'):page['image']='inputs/'+page['image']
                request={'id':id,'prompt':packet['prompt'],'clarification':packet['clarification'],'inputs':files,'source_maps':source_maps,'output_contract':{'common':fmt['common'],'task':fmt['tasks'].get(id,{})},'artifact_requirements':packet['artifacts'],'allowed_tools':t['tool_allowlist'],'search_policy':t['search_policy'],'output_directory':'artifacts','time_budget_seconds':remaining}
                write(work/'request.json',request);r['started_at']=now();tick=time.monotonic()
                response=None;reason='runtime_error';status='failed';proc=None
                try:
                    with (work/'request.json').open('rb') as inp,(work/'worker.stdout.json').open('wb') as stdout,(work/'worker.stderr.log').open('wb') as stderr:
                        proc=subprocess.Popen(a.worker,cwd=work,stdin=inp,stdout=stdout,stderr=stderr,start_new_session=(os.name=='posix'))
                        try:code=proc.wait(timeout=max(0.001,limit-(time.monotonic()-start)))
                        except subprocess.TimeoutExpired:
                            if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
                            else:proc.kill()
                            proc.wait();raise
                    if code!=0:raise RuntimeError('worker exit '+str(code))
                    if (work/'worker.stdout.json').stat().st_size>20*1024*1024:raise ValueError('response too large')
                    response=read(work/'worker.stdout.json')
                    if not isinstance(response,dict):raise ValueError('response not object')
                    status=response.get('status');reason=response.get('reason_code')
                    if status not in ['completed','partial','failed','unsupported','blocked','timeout']:raise ValueError('bad status')
                    if status in ['completed','partial'] and response.get('answer') in (None,{},[],''):raise ValueError('empty answer')
                    arts=response.get('artifacts',[])
                    if not isinstance(arts,list) or len(set(arts))!=len(arts):raise ValueError('invalid artifact names')
                    actual=[]
                    for n in arts:
                        f=safe(work/'artifacts',n)
                        if not f.is_file() or not f.stat().st_size:raise ValueError('missing artifact '+n)
                        actual.append({'name':n,'sha256':sha(f),'bytes':f.stat().st_size})
                    import fnmatch
                    if status=='completed' and any(not any(fnmatch.fnmatch(x['name'],pat) for x in actual) for pat in packet['artifacts']):status='partial';reason='missing_artifact'
                    if status=='completed':reason=None
                    elif reason not in ['missing_input','missing_tool','unsupported_context','dependency_failed','time_limit','runtime_error','invalid_output','policy_block','measurement_unavailable','not_selected','other','missing_artifact','context_unverified','source_unverified','output_limit','missing_sdk','missing_normative']:reason='other'
                    payload={'id':id,'status':status,'reason_code':reason,'answer':response.get('answer'),'evidence':response.get('evidence',[]),'notes':response.get('notes'),'artifacts':actual}
                    write(work/'answer.json',payload);answers.append(payload);r['answer_sha256']=sha(work/'answer.json');r['artifact_count']=len(actual)
                    if status=='completed':completed_outputs[id]=work/'artifacts'
                except subprocess.TimeoutExpired:status='timeout';reason='time_limit'
                except Exception as e:status='failed';reason='invalid_output' if response is not None else 'runtime_error';write(work/'worker-error.json',{'error':str(e)})
                r['ended_at']=now();r['wall_seconds']=round(time.monotonic()-tick,6);r['status']=status;r['reason_code']=reason
                # Do not derive token counts or tool telemetry from model-authored output.
                write(out/'ceb-run.json',run)
                continue
            r.update(status='blocked',reason_code='dependency_failed')
        elapsed=round(time.monotonic()-start,6)
        if profile=='standard':run['ended_at']=now();run['total_wall_seconds']=elapsed
        else:run['qualification_wall_seconds']=elapsed
    write(out/'private'/'ceb-answers.json',{'run_id':run['run_id'],'suite_version':run['suite_version'],'tasks':answers});run['answers_sha256']=sha(out/'private'/'ceb-answers.json')
    write(out/'ceb-run.json',run)
    print('Recorded',len(answers),'answers,',sum(x['status']=='completed' for x in run['tasks']),'completed; not validated. See',out/'ceb-run.json')
if __name__=='__main__':main()
