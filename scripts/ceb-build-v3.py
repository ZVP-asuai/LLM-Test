#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, zipfile, io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
import fitz
root=Path(__file__).resolve().parents[1]; out=root/'docs/ceb/v3'; extra=out/'extension'
extra.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def pdf(name,pages,scan=False,rotate=False):
    b=io.BytesIO();c=canvas.Canvas(b,pagesize=landscape(A4),invariant=1)
    w,h=landscape(A4)
    for i,lines in enumerate(pages,1):
        c.setFont('Helvetica-Bold',20);c.drawString(40,h-45,'CEB LAB / '+name)
        c.setFont('Helvetica',13)
        for j,line in enumerate(lines):c.drawString(42,h-90-27*j,line)
        c.setFont('Helvetica',11);c.drawString(42,26,'Synthetic technical document / page '+str(i));c.showPage()
    c.save()
    if not scan:(extra/name).write_bytes(b.getvalue());return
    with fitz.open(stream=b.getvalue(),filetype='pdf') as src,fitz.open() as dst:
        for i,p in enumerate(src):
            pix=p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);q=dst.new_page(width=p.rect.width,height=p.rect.height);q.insert_image(q.rect,stream=pix.tobytes('png'))
            if rotate and i==1:q.set_rotation(90)
        dst.save(extra/name,garbage=4,deflate=True)
pdf('rotated-catalog.pdf', [['Order code       Voltage V       Continuous A       Net mass kg       Variant','RZ-17              24                    3,6                       0,145                    L2','RZ-71              48                    6,3                       0,154                    L7'],['Order code       Voltage V       Continuous A       Net mass kg       Variant','RZ-17A            24                    5,1                       0,184                    A2','RZ-71              48                    6,3                       0,154                    L7','RZ-17B            110                  3,6                       0,201                    B2']],True,True)
pdf('selection.pdf',[['Module          Voltage        Continuous A @40C       Peak A       Width mm','M11                24 VDC                  12                          20                  45','M12                24 VDC                  10                          18                  48','M13                24 VAC                  16                          30                  40','M14                24 VDC                  18                          25                  60'],['Notes: above 40C reduce continuous current by 2% per degree for M11.','M12 is rated for 50C maximum; above 50C it must not be used.','M13 is AC only. M14: no temperature derating up to 60C.','Peak current is not continuous current.']])
pdf('revisions.pdf',[['REV R2 / APPROVED','Tag        Range        Unit        Signal','PT-41     0..10         bar          4-20 mA','FT-42     0..50         m3/h        4-20 mA','LS-43     ON/OFF     -             NC'],['REV R3 / DRAFT','Tag        Range        Unit        Signal','PT-41     0..16         bar          4-20 mA','FT-42     0..50         l/min        0-10 V','LS-43     ON/OFF     -             NO']])
pdf('crossrefs.pdf',[['Index / source field signals','PT-41 -> cable W41 core 2 -> sheet 2','LS-42 -> cable W42 core 1 -> sheet 2'],['Terminal plan','W41:2 -> X3:7 -> net N411 -> sheet 3','W42:1 -> X3:8 -> net N422 -> sheet 3'],['PLC channel map','N411 -> A5 AI2 -> IW68','N423 -> A6 DI1 -> I2.1','Note: N422 not present on this sheet.']])
pdf('bom-scan.pdf',[['Article     Unit     Quantity    Price RUB     Type','B-172       pcs            3                 650            ITEM','R-044       pcs            2                 820            ITEM','B-172       pcs            3                 650            REF'],['Article     Unit     Quantity    Price RUB     Type','B-172       pcs            5                 650            ITEM','C-019       m              12                90             ITEM','R-044       pcs            1                 820            ITEM']],True)
backup=extra/'backup'; actual=backup/'files'
manifest=[{'path':'a.txt','sha256':sha((actual/'a.txt').read_bytes())},{'path':'b.txt','sha256':sha(b'original content\n')},{'path':'c.txt','sha256':sha(b'not delivered\n')}]
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Reuse exact public 2.0 fixture bytes from this CI build. Third party sources not redistributed.
base=root/'docs/ceb/inputs/CEB-offline-inputs.zip'
with zipfile.ZipFile(base) as z:files={'legacy/'+n:z.read(n) for n in z.namelist()}
for f in extra.rglob('*'):
    if f.is_file():files[f.relative_to(out).as_posix()]=f.read_bytes()
for n in ['manifest.json','extension-tasks.json','launch.txt','run-template.json','SETUP.md']:
    files[n]=(out/n).read_bytes()
files['setup-timer.py']=(root/'scripts/ceb-setup-timer.py').read_bytes()
inventory=[{'path':n,'bytes':len(b),'sha256':sha(b)} for n,b in sorted(files.items())]
files['inventory.json']=json.dumps(inventory,ensure_ascii=False,indent=2).encode()
p=out/'CEB-3.0-inputs.zip'
with zipfile.ZipFile(p,'w') as z:
    for n,b in sorted(files.items()):
        info=zipfile.ZipInfo(n,(2026,11,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    assert all(sha(z.read(x['path']))==x['sha256'] for x in inventory)
    m=json.loads(z.read('manifest.json'));assert len(m['tasks'])==100 and len({t['id'] for t in m['tasks']})==100
    for t in m['tasks'][50:]:
        for f in t['input_files']:assert f in z.namelist() or any(n.startswith(f) for n in z.namelist()),(t['id'],f)
    assert not any('reference' in n or 'answer' in n or 'validator' in n for n in z.namelist())
(out/'sha256.txt').write_text(sha(p.read_bytes())+'  '+p.name+'\n')
print('CEB 3.0',len(files),'files',p.stat().st_size,sha(p.read_bytes()))
