from pathlib import Path
import hashlib, json, zipfile, io
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,A4
p=Path("docs/ceb/v3")
m=json.loads((p/"engineering.json").read_text())
assert len(m["tasks"])==100 and [t["number"] for t in m["tasks"]]==list(range(1,101)) and len({t["id"] for t in m["tasks"]})==100
files={}
with zipfile.ZipFile(p/"CEB-3.0-inputs.zip") as z:
    for name in z.namelist():
        if name.startswith("legacy/fixtures/") or name.startswith("legacy/context") or name.startswith("extension/"):
            if not name.endswith("/"): files[name]=z.read(name)
for name,pages in json.loads((p/"portable-fixtures.json").read_text()).items():
    b=io.BytesIO(); c=canvas.Canvas(b,pagesize=landscape(A4),invariant=1)
    w,h=landscape(A4)
    for i,lines in enumerate(pages,1):
        c.setFont("Helvetica-Bold",20); c.drawString(38,h-45,"CEB LAB / "+name)
        c.setFont("Helvetica",14)
        for j,line in enumerate(lines):
            assert c.stringWidth(line,"Helvetica",14)<w-76,(name,line)
            c.drawString(38,h-90-30*j,line)
        c.drawString(38,35,"Training fixture / page "+str(i)); c.showPage()
    c.save(); files["portable/"+name]=b.getvalue()
files["portable/pages.json"]=(p/"portable/pages.json").read_bytes()
wanted={f for t in m["tasks"] for f in t["input_files"]}
for f in wanted:
    assert f in files or (f.endswith("/") and any(k.startswith(f) for k in files)),f
# Only required input files; add image previews of all PDF pages for environments without a PDF renderer.
files={k:v for k,v in files.items() if k in wanted or any(f.endswith("/") and k.startswith(f) for f in wanted)}
for name,data in list(files.items()):
    if name.endswith(".pdf"):
        with fitz.open(stream=data,filetype="pdf") as d:
            for i,page in enumerate(d,1):
                files[f"{name}.page-{i:02}.png"]=page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False).tobytes("png")
for name in ["engineering.json","engineering-report-template.json","engineering-method.md","engineering-launch.txt"]:
    files[name]=(p/name).read_bytes()
r=json.loads(files["engineering-report-template.json"])
assert [(t["number"],t["id"]) for t in r["tasks"]]==[(t["number"],t["id"]) for t in m["tasks"]]
files["inventory.json"]=json.dumps([{"path":k,"sha256":hashlib.sha256(v).hexdigest(),"bytes":len(v)} for k,v in sorted(files.items())],ensure_ascii=False,indent=2).encode()
out=p/"engineering-inputs.zip"
with zipfile.ZipFile(out,"w") as z:
    for k,v in sorted(files.items()):
        info=zipfile.ZipInfo(k,(2026,11,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,v)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(x["path"])).hexdigest()==x["sha256"] for x in json.loads(z.read("inventory.json")))
(p/"engineering-sha256.txt").write_text(hashlib.sha256(out.read_bytes()).hexdigest()+"  engineering-inputs.zip\n")
print("CEB engineering: 100 tasks, verified input paths, archive integrity;",len(files),"files",out.stat().st_size)
