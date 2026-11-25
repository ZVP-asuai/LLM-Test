#!/usr/bin/env python3
"""CEB run ledger: standard Python, no network, no scoring. Run in a private workspace."""
import argparse, hashlib, json, math, os, time, zipfile
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

PROTOCOL = "ceb-execution-1"
STATUSES = {"completed","partial","failed","blocked","timeout","not_run"}
CATEGORIES = {"model_error","environment","missing_input","ambiguous_task","timeout","not_run","unknown"}
SHA = "d7e1172e8f0893d8f9896d48f8501b4d38d8adf0422d6b9df5dde60828540eca"
DATASET = "ceb-100-portable-20261125-r2"
def now(): return datetime.now(timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def put(p, obj):
    p=Path(p); tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8"); os.replace(tmp,p)
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def safe(s):
    return isinstance(s,str) and bool(s) and "\\" not in s and ":" not in s and all(x not in ("",".","..") for x in s.split("/"))
def artifact(root,s):
    require(safe(s),"Invalid artifact path: "+str(s))
    p=(root/s).resolve()
    require(p.is_relative_to(root.resolve()) and p.is_file(),"Missing output artifact: "+s)
    return p
def check_catalog(c):
    require(c["dataset_id"]==DATASET,"Wrong dataset")
    require([x["number"] for x in c["tasks"]]==list(range(1,101)),"Expected 100 ordered tasks")
    require(len({x["id"] for x in c["tasks"]})==100,"Duplicate IDs")
def empty_task(t):
    return {"number":t["number"],"id":t["id"],"status":"not_run","answer":None,"calculation_steps":[],"sources":[],"assumptions":[],"checks":[],"artifacts":[],"wall_seconds":None,"issue":{"category":"not_run","code":"not_started","description":"Not started","attempts":[]}}
def nonempty(x): return x is not None and x!="" and x!=[] and x!={}
def duration(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>0
def check_task(t,c,root):
    require(t.get("number")==c["number"] and t.get("id")==c["id"],"Task ID/number mismatch")
    require(t.get("status") in STATUSES,"Invalid status")
    require("score" not in t and "points" not in t,"No self scoring")
    for k in ["calculation_steps","sources","assumptions","checks","artifacts"]:
        require(isinstance(t.get(k),list),"Missing list "+k)
    for x in t["calculation_steps"]:
        require(isinstance(x,dict) and set(("description","inputs","formula_or_method","substitution","result","unit"))<=x.keys(),"Incomplete calculation")
    for x in t["sources"]:
        require(isinstance(x,dict) and all(isinstance(x.get(k),str) and x[k].strip() for k in ("file","locator","fact")),"Incomplete source")
    for x in t["checks"]:
        require(isinstance(x,dict) and isinstance(x.get("name"),str) and {"expected","observed","evidence"}<=x.keys() and x.get("status") in ("pass","fail","not_run"),"Invalid check")
        if x["status"]=="not_run": require(x["observed"] is None,"Unrun check has observed value")
        else: require(x["observed"] is not None and isinstance(x["evidence"],str) and x["evidence"].strip(),"Missing actual evidence")
    require(len(set(t["artifacts"]))==len(t["artifacts"]),"Duplicate artifact")
    for x in t["artifacts"]: artifact(root,x)
    if t["status"]=="completed":
        require(nonempty(t.get("answer")) and t.get("issue") is None and t["calculation_steps"] and t["sources"] and t["checks"],"Missing answer/method/source/checks")
        require(set(c.get("artifacts",[]))<=set(t["artifacts"]),"Required output missing")
        require(any(x["status"] in ("pass","fail") for x in t["checks"]),"No performed checks")
        require(not any(x["status"]=="fail" for x in t["checks"]),"Failed check unresolved: use partial/failed")
        if c.get("artifacts"): require(not any(x["status"]=="not_run" for x in t["checks"]),"Required artifact checks not performed: use partial")
    else:
        q=t.get("issue")
        require(isinstance(q,dict) and q.get("category") in CATEGORIES and all(isinstance(q.get(k),str) and q[k].strip() for k in ("code","description")) and isinstance(q.get("attempts"),list),"Missing concrete issue")
    if t["status"] in ("blocked","timeout"): require(bool(t["issue"]["attempts"]),"No documented attempt")
def summarize(r):
    counts={s:sum(t["status"]==s for t in r["tasks"]) for s in sorted(STATUSES)}
    measured=[t["wall_seconds"] for t in r["tasks"] if duration(t["wall_seconds"])]
    attempted=100-counts["not_run"]
    r["execution"]["counts"]=counts
    r["execution"]["measured_tasks"]=len(measured)
    r["execution"]["attempted_tasks"]=attempted
    r["execution"]["next_task"]=next((t["number"] for t in r["tasks"] if t["status"]=="not_run"),None)
    r["timing"]["solve_seconds"]=round(sum(measured),6) if measured else None
    r["execution"]["task_time_coverage"]=round(len(measured)/attempted,6) if attempted else None
    r["execution"]["complete_submission"]=counts["completed"]==100
    r["execution"]["updated_at"]=now()
    return r
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--workspace",default="ceb-run")
    sub=a.add_subparsers(dest="cmd",required=True)
    i=sub.add_parser("init");i.add_argument("--catalog",required=True);i.add_argument("--model",required=True);i.add_argument("--run-id",required=True);i.add_argument("--archive");i.add_argument("--platform",default=None);i.add_argument("--effort",default=None)
    b=sub.add_parser("begin");b.add_argument("number",type=int)
    e=sub.add_parser("end");e.add_argument("number",type=int);e.add_argument("record")
    sub.add_parser("checkpoint")
    z=sub.add_parser("finalize");z.add_argument("--delivery-log")
    args=a.parse_args(); w=Path(args.workspace).resolve(); w.mkdir(parents=True,exist_ok=True)
    rp=w/"engineering-report.json"; cp=w/"catalog.json"; st=w/"clock.json"; root=w/"outputs"; root.mkdir(exist_ok=True)
    if args.cmd=="init":
        require(not rp.exists(),"Existing run; resume rather than overwrite")
        c=read(args.catalog);check_catalog(c)
        verified=None
        if args.archive:
            require(sha(args.archive)==SHA,"Archive SHA mismatch")
            with zipfile.ZipFile(args.archive) as z:
                require(z.testzip() is None,"Corrupt ZIP")
                require(json.loads(z.read("engineering.json"))==c,"Catalog differs from verified ZIP")
            verified=SHA
        r={"format":"ceb-engineering-report-1","dataset_id":DATASET,"run_id":args.run_id,"model":{"name":args.model,"reasoning_effort":args.effort,"platform":args.platform},"input_sha256":verified,"timing":{"source":"agent_monotonic","delivery_seconds":None,"setup_seconds":None,"solve_seconds":None,"verification_seconds":None,"total_seconds":None},"tasks":[empty_task(t) for t in c["tasks"]],"delivery_attempts":[],"execution":{"protocol":PROTOCOL,"started_at":now(),"timing_scope":"sequential task start through persisted result; excludes delivery, pauses and final packaging; self-instrumented, not external","clock_events":[],"artifact_manifest":[]}}
        put(cp,c);put(st,{"active":None});put(rp,summarize(r)); print(rp);return
    c=read(cp);r=read(rp);clock=read(st);check_catalog(c)
    if args.cmd=="begin":
        n=args.number;require(1<=n<=100,"Task outside range")
        require(clock["active"] is None,"Previous task active; end it first")
        require(r["tasks"][n-1]["status"]=="not_run","Already recorded; preserve first result")
        clock["active"]={"number":n,"start_ns":time.monotonic_ns(),"start_utc":now()};put(st,clock)
        print("BEGIN",n,clock["active"]["start_utc"]);return
    if args.cmd=="end":
        n=args.number;active=clock["active"];require(active and active["number"]==n,"No matching begin")
        t=read(args.record);require(t.get("status")!="not_run","Use an actual terminal task status")
        check_task(t,c["tasks"][n-1],root)
        end_ns=time.monotonic_ns();delta=(end_ns-active["start_ns"])/1e9
        # UTC cross-check detects most clock/environment restarts; never invent a duration.
        utc=now();utc_delta=(datetime.fromisoformat(utc)-datetime.fromisoformat(active["start_utc"])).total_seconds()
        valid=delta>0 and utc_delta>=0 and abs(delta-utc_delta)<5
        t["wall_seconds"]=round(delta,6) if valid and round(delta,6)>0 else None
        r["execution"]["clock_events"].append({"number":n,"start_utc":active["start_utc"],"end_utc":utc,"wall_seconds":t["wall_seconds"],"source":"agent_monotonic" if t["wall_seconds"] is not None else "unavailable"})
        r["tasks"][n-1]=t;put(rp,summarize(r));put(st,{"active":None});print("END",n,t["status"],t["wall_seconds"]);return
    if args.cmd=="checkpoint":
        put(rp,summarize(r));print(json.dumps(r["execution"]["counts"]), "next:",r["execution"]["next_task"],"active:",clock["active"]);return
    require(clock["active"] is None,"Finalize after ending the active task or return checkpoint")
    if args.delivery_log:
        r["delivery_attempts"]=read(args.delivery_log);require(isinstance(r["delivery_attempts"],list),"Delivery log must be an array")
    names=set()
    for t,ct in zip(r["tasks"],c["tasks"]):
        check_task(t,ct,root); names.update(t["artifacts"])
    r["execution"]["artifact_manifest"]=[{"path":n,"bytes":artifact(root,n).stat().st_size,"sha256":sha(artifact(root,n))} for n in sorted(names)]
    put(rp,summarize(r));out=w/"engineering-outputs.zip"
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.write(rp,"engineering-report.json")
        for n in sorted(names):z.write(artifact(root,n),n)
    with zipfile.ZipFile(out) as z:
        require(z.testzip() is None,"Output ZIP corrupted")
        require(json.loads(z.read("engineering-report.json"))==r,"Report differs in ZIP")
        for x in r["execution"]["artifact_manifest"]:
            require(hashlib.sha256(z.read(x["path"])).hexdigest()==x["sha256"],"Artifact hash mismatch")
    print("FINAL",rp,out,json.dumps(r["execution"]["counts"]), "measured",r["execution"]["measured_tasks"])
if __name__=="__main__": main()
