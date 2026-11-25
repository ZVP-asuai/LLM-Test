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
