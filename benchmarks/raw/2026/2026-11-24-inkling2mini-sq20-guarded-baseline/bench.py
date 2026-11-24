import os,sys,time,json,subprocess,signal,threading,urllib.request,hashlib,pathlib
D=pathlib.Path(sys.argv[1]); T='/opt/strata-0221/.local/share/strata/terminal/0.1.67'
P='/opt/strata-0221/.local/share/strata/Strata-data/packs/inkling-2-mini-sq-20/tokenizer'
C='/opt/strata-0221/.local/share/strata/install/strata-inkling-2-mini-sq-20.json'
base='http://127.0.0.1:18080'
gpu='00000000:81:00.0'
fields='temperature.gpu,temperature.memory,power.draw,memory.used,memory.free,utilization.gpu,clocks.current.graphics,clocks.current.memory,pcie.link.gen.gpucurrent,pcie.link.width.current,power.limit'
names=fields.split(',')
stop=threading.Event(); reason=[]; phase=['startup']; server=None; start=time.monotonic()
def get(path):
    with urllib.request.urlopen(base+path,timeout=3) as r:return json.load(r)
def sample():
    s=subprocess.check_output(['nvidia-smi','-i',gpu,'--query-gpu='+fields,'--format=csv,noheader,nounits'],text=True,timeout=2).strip().split(',')
    assert len(s)==len(names)
    d={}
    for k,v in zip(names,s):
        try:d[k]=float(v.strip())
        except ValueError:d[k]=None
    if d['temperature.gpu'] is None or d['power.limit']!=300:raise RuntimeError('invalid sensor or power limit')
    d.update(t=round(time.monotonic()-start,3),phase=phase[0])
    return d
def terminate():
    if server is not None:
        try:os.killpg(server.pid,signal.SIGTERM)
        except ProcessLookupError:return
        time.sleep(1)
        try:os.killpg(server.pid,signal.SIGKILL)
        except ProcessLookupError:pass
def monitor():
    with (D/'telemetry.jsonl').open('a',buffering=1) as f:
        while not stop.is_set():
            try:
                s=sample(); f.write(json.dumps(s)+'\n')
                if any(s[k] is not None and s[k]>=68 for k in ['temperature.gpu','temperature.memory']):raise RuntimeError('thermal guard >=68 C')
                if time.monotonic()-start>200:raise RuntimeError('overall time budget')
            except Exception as e:
                reason.append(str(e)); print('GUARD STOP',str(e),flush=True); terminate(); return
            stop.wait(.5)
def guard():
    if reason:raise RuntimeError(reason[0])
    if server.poll() is not None:raise RuntimeError('server exited')
def save(name,data):
    (D/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
try:
    try:get('/health')
    except Exception:pass
    else:raise RuntimeError('server already running')
    b=sample()
    if b['memory.used']>64 or b['temperature.gpu']>=60:raise RuntimeError('GPU not idle/cool')
    print('RUN_DIR',D,flush=True)
    save('initial-gpu.json',b)
    cmd=['/usr/sbin/runuser','-u','strata','--','env','HOME=/opt/strata-0221','PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',T+'/python/bin/python3.12',T+'/serve/server.py','--engine','strata','--config',C,'--host','127.0.0.1','--port','18080','--offline']
    save('launch.json',cmd)
    with (D/'server.log').open('w') as f:
        server=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    th=threading.Thread(target=monitor,daemon=True);th.start()
    for i in range(90):
        guard()
        try:
            h=get('/health')
            if h.get('loaded'):break
        except Exception:pass
        time.sleep(.5)
    else:raise RuntimeError('startup timeout')
    save('status.json',get('/v1/status'))
    print('MODEL_READY',round(time.monotonic()-start,3),flush=True)
    sys.path.insert(0,T+'/tools'); import strata_tokenizer as ST
    v=json.load(open(P+'/vocab.json')); tokens=[None]*len(v)
    for k,i in v.items():tokens[i]=k
    cfg=json.load(open(P+'/tokenizer.json'))
    tok=ST.Tokenizer(tokens,open(P+'/merges.txt',encoding='utf-8').read().splitlines(),json.load(open(P+'/token_type.json')),cfg['pre'],cfg.get('special_ids'))
    filler='The pressure sensor reports 42.7 bar and the controller records the value. '
    for target in (8192,32768,65536):
        guard(); phase[0]=str(target)
        prefix='CT128 baseline '+str(target)+' unique record. Control reference: ALPHA-7391.\n'
        suffix='\nQuestion: Return the control reference from the beginning of this record. Answer briefly.'
        ids=tok.encode(prefix+filler*(target//8+100))
        n=target-15-len(tok.encode(suffix))
        content=tok.decode(ids[:n])+suffix
        for _ in range(5):
            diff=target-15-len(tok.encode(content))
            if not diff:break
            n+=diff;content=tok.decode(ids[:n])+suffix
        payload={'model':'inkling-2-mini-sq-20','messages':[{'role':'user','content':content}],'max_tokens':256,'temperature':0,'reasoning_effort':'xhigh','stream':True,'stream_options':{'include_usage':True}}
        data=json.dumps(payload,ensure_ascii=False).encode()
        (D/(str(target)+'-request.json')).write_bytes(data)
        seen={r['id'] for r in get('/metrics')['requests']}
        req=urllib.request.Request(base+'/v1/chat/completions',data=data,headers={'Content-Type':'application/json'})
        t=time.monotonic(); first=None; visible=None; out=[]; usage=None; done=False
        with urllib.request.urlopen(req,timeout=120) as r:
            with (D/(str(target)+'-stream.jsonl')).open('w') as rawf:
                for raw in r:
                    guard()
                    ln=raw.decode().strip()
                    if not ln.startswith('data: '):continue
                    if ln=='data: [DONE]':done=True;break
                    obj=json.loads(ln[6:]); now=time.monotonic()-t
                    rawf.write(json.dumps({'elapsed_s':now,'event':obj},ensure_ascii=False)+'\n')
                    if first is None:first=now
                    if obj.get('usage'):usage=obj['usage']
                    for ch in obj.get('choices',[]):
                        txt=(ch.get('delta') or {}).get('content') or ''
                        if txt:
                            if visible is None and txt.strip():visible=now
                            out.append(txt)
        elapsed=time.monotonic()-t
        guard()
        m=get('/metrics'); records=[r for r in m['requests'] if r['id'] not in seen]
        if len(records)!=1:raise RuntimeError('ambiguous server metrics')
        r=records[0]
        samples=[json.loads(l) for l in (D/'telemetry.jsonl').read_text().splitlines() if l.strip()]
        samples=[x for x in samples if x['phase']==str(target)]
        def mx(k):return max((s[k] for s in samples if s[k] is not None),default=None)
        result={'target':target,'actual_user_tokens':len(tok.encode(content)),'request_sha256':hashlib.sha256(data).hexdigest(),'ttft_sse_event_s':first,'ttft_visible_s':visible,'client_elapsed_s':elapsed,'done':done,'usage':usage,'server':r,'gpu':{'samples':len(samples),'core_max_c':mx('temperature.gpu'),'memory_max_c':mx('temperature.memory'),'power_max_w':mx('power.draw'),'vram_max_mib':mx('memory.used'),'pcie_gen_max_observed':mx('pcie.link.gen.gpucurrent')},'answer':''.join(out),'reference_found':'ALPHA-7391' in ''.join(out),'guard_threshold_c':68}
        save(str(target)+'-result.json',result); print('RESULT',json.dumps(result,ensure_ascii=False),flush=True)
        phase[0]='cooldown'
        for i in range(30):
            guard()
            if sample()['temperature.gpu']<45:break
            time.sleep(.5)
except Exception as e:
    print('ERROR',repr(e),flush=True);save('failure.json',{'error':repr(e),'phase':phase[0],'guard':reason})
finally:
    stop.set();terminate()
    if 'th' in locals():th.join(timeout=3)
    print('END',str(D),'guard',reason,flush=True)
