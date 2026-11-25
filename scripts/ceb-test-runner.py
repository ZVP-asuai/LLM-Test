import json, pathlib, subprocess, sys, tempfile, zipfile, hashlib
p=pathlib.Path("docs/ceb/v3").resolve()
runner=p/"engineering-runner.py"
with tempfile.TemporaryDirectory() as td:
    w=pathlib.Path(td);work=w/"run"
    def call(*args,ok=True):
        a=subprocess.run([sys.executable,str(runner),"--workspace",str(work),*map(str,args)],capture_output=True,text=True)
        assert (a.returncode==0)==ok,(args,a.stdout,a.stderr)
        return a.stdout
    call("start");call("start",ok=False)
    call("init","--catalog",p/"engineering.json","--archive",p/"engineering-inputs.zip","--model","TEST_SYNTHETIC_NOT_BENCHMARK","--run-id","synthetic-ci")
    r=work/"engineering-report.json"
    def read():return json.loads(r.read_text())
    assert len(read()["tasks"])==100
    call("init","--catalog",p/"engineering.json","--model","test","--run-id","no-overwrite",ok=False)
    call("begin",1);call("begin",2,ok=False)
    t=read()["tasks"][0];t.update(status="completed",answer={"fixture":"synthetic test only"},issue=None,calculation_steps=[dict(description="synthetic",inputs={},formula_or_method="synthetic",substitution="none",result=1,unit="test")],sources=[dict(file="engineering.json",locator="synthetic",fact="test")],checks=[dict(name="synthetic",expected=1,observed=1,status="pass",evidence="test")])
    rec=w/"record.json";rec.write_text(json.dumps(t))
    call("end",1,rec);assert read()["tasks"][0]["wall_seconds"]>0
    call("begin",10);t.update(number=10,id=read()["tasks"][9]["id"],artifacts=[]);rec.write_text(json.dumps(t));call("end",10,rec,ok=False)
    t.update(status="partial",issue={"category":"environment","code":"test_missing_outputs","description":"synthetic test","attempts":["check missing outputs"]})
    rec.write_text(json.dumps(t));call("end",10,rec)
    call("begin",2);t=read()["tasks"][1];t.update(status="blocked",issue={"category":"missing_input","code":"synthetic","description":"test","attempts":[]});rec.write_text(json.dumps(t));call("end",2,rec,ok=False)
    t["issue"]["attempts"]=["synthetic read failure"];rec.write_text(json.dumps(t));call("end",2,rec)
    call("checkpoint");call("finalize")
    rr=read();assert rr["timing"]["delivery_seconds"]>0 and rr["timing"]["setup_seconds"]>0 and rr["timing"]["verification_seconds"]>0 and rr["timing"]["total_seconds"]>0
    assert rr["execution"]["measured_tasks"]==3 and rr["execution"]["attempted_tasks"]==3
    assert rr["execution"]["counts"]["not_run"]==97 and rr["execution"]["next_task"]==3 and rr["execution"]["complete_submission"] is False
    assert abs(rr["timing"]["solve_seconds"]-sum(t["wall_seconds"] or 0 for t in rr["tasks"]))<1e-6
    with zipfile.ZipFile(work/"engineering-outputs.zip") as z:assert z.testzip() is None and json.loads(z.read("engineering-report.json"))==rr
    # Test a real required-output acceptance path (synthetic contents, not model answer).
    call("begin",11);t=read()["tasks"][10];t.update(status="completed",answer={"fixture":"synthetic"},issue=None,calculation_steps=[dict(description="test",inputs={},formula_or_method="test",substitution="",result=1,unit="test")],sources=[dict(file="engineering.json",locator="test",fact="test")],checks=[dict(name="test",expected=1,observed=1,status="pass",evidence="test")],artifacts=["connection-points.csv","terminal-functions.csv"])
    rec.write_text(json.dumps(t));call("end",11,rec,ok=False)
    for n in t["artifacts"]:(work/"outputs"/n).write_text("synthetic,fixture\n")
    call("end",11,rec);call("finalize")
    rr=read();assert len(rr["execution"]["artifact_manifest"])==2
    call("verify","--catalog",p/"engineering.json","--zip",work/"engineering-outputs.zip","--report",r)
    bad=w/"tampered.zip"
    with zipfile.ZipFile(work/"engineering-outputs.zip") as src,zipfile.ZipFile(bad,"w") as dst:
        for n in src.namelist():dst.writestr(n,b"changed,content\n" if n=="connection-points.csv" else src.read(n))
    call("verify","--catalog",p/"engineering.json","--zip",bad,ok=False)
    with zipfile.ZipFile(work/"engineering-outputs.zip") as z:
        for x in rr["execution"]["artifact_manifest"]:assert hashlib.sha256(z.read(x["path"])).hexdigest()==x["sha256"]
s=(p/"engineering-start.txt").read_text()
assert s.count("ЗАДАНИЕ ")==100 and "ceb-execution-1" in s and "time.monotonic_ns()" in s
print("Execution ledger tests passed: timing, resume, missing artifacts, blocked attempts, partial checkpoint, ZIP hashes, 100 embedded conditions. Synthetic data only.")
