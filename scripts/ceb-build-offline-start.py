from pathlib import Path
import zipfile, hashlib, json
p=Path("docs/ceb/v3")
d=json.loads((p/"engineering-delivery.json").read_text())
a=p/"engineering-inputs.zip"
assert hashlib.sha256(a.read_bytes()).hexdigest()==d["expected_sha256"]
names=["engineering-inputs.zip","engineering-runner.py","engineering-start-offline.txt","engineering-start.txt","engineering-sha256.txt"]
with zipfile.ZipFile(p/"CEB-offline-start.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
    for n in names:z.write(p/n,n)
with zipfile.ZipFile(p/"CEB-offline-start.zip") as z:
    assert z.testzip() is None and z.namelist()==names
    assert hashlib.sha256(z.read("engineering-inputs.zip")).hexdigest()==d["expected_sha256"]
print("Offline launch kit verified: original archive unchanged; runner and both prompts included.")
