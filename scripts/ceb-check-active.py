import json, pathlib, hashlib, zipfile
p=pathlib.Path("docs/ceb")
m=json.loads((p/"v3/manifest.json").read_text())
mirror=json.loads((p/"v3/mirror.json").read_text())
launch=(p/"v3/launch.txt").read_text()
assert m["version"]=="3.0-review" and len(m["tasks"])==100
assert launch.startswith(f'# CEB Engineering Benchmark {m["version"]} — агент, {len(m["tasks"])} задач')
for k in ("sha256","url","pinned_github_raw"):
    assert mirror[k] in launch, k
assert hashlib.sha256((p/"v3/CEB-3.0-inputs.zip").read_bytes()).hexdigest()==mirror["sha256"]
with zipfile.ZipFile(p/"v3/CEB-3.0-inputs.zip") as z:
    assert json.loads(z.read("manifest.json"))==m
assert 'url=./v3/index.html' in (p/"index.html").read_text()
for name, prefix in (("docs/index.html","./ceb/v3/"),("docs/ceb/diagnostics.html","./v3/")):
    html=pathlib.Path(name).read_text()
    assert f'href="{prefix}index.html">Бенчмарк CEB 3.0' in html, name
    assert f'href="{prefix}index.html#comparison">Сравнение моделей' in html, name
html=(p/"v3/index.html").read_text()
assert 'id="comparison"' in html and 'id="copy" disabled' in html and 'id="prompt-status"' in html
print("CEB current page: 100 tasks, pinned archive and launch links verified.")

import re
current=json.loads((p/"v3/engineering.json").read_text())
report=json.loads((p/"v3/engineering-report-template.json").read_text())
assert len(current["tasks"])==100 and [x["number"] for x in current["tasks"]]==list(range(1,101))
assert [(t["number"],t["id"]) for t in current["tasks"]]==[(t["number"],t["id"]) for t in report["tasks"]]
assert report["dataset_id"]==current["dataset_id"]
pack=p/"v3/engineering-inputs.zip"
assert hashlib.sha256(pack.read_bytes()).hexdigest()==(p/"v3/engineering-sha256.txt").read_text().split()[0]
with zipfile.ZipFile(pack) as z:
    assert json.loads(z.read("engineering.json"))==current
    assert all(f in z.namelist() or (f.endswith("/") and any(n.startswith(f) for n in z.namelist())) for t in current["tasks"] for f in t["input_files"])
assert all(f'data-pane="{name}"' in html for name in ["benchmark","comparison","diagnostics"])
print("Unified CEB catalogue, report and archive validated.")
