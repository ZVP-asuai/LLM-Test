#!/usr/bin/env python3
"""Build PUBLIC INPUTS only. Does not contain grading keys or execute a model."""
from pathlib import Path
import json, hashlib, zipfile, tempfile, io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white
import fitz
root=Path(__file__).resolve().parents[1]
out=root/'docs/ceb/inputs'
fx=out/'fixtures'; fx.mkdir(parents=True,exist_ok=True)
w,h=landscape(A4)
rows=[
("XR-9084-00",2,18,24,1.7,70,.615),("XR-7148-01",3,32,110,1.09,111,.525),("XR-4212-02",2,32,230,1.77,100,.705),("XR-1846-03",4,18,24,2.05,84,.402),
("XR-5750-04",3,18,48,.84,80,.761),("XR-3460-05",3,9,48,1.86,99,.539),("XR-4544-06",2,18,24,1.76,100,.261),("XR-1659-07",3,32,110,1.69,106,.601),
("XR-7317-08",3,12,48,1.67,91,.624),("XR-5282-09",2,16,24,1.28,90,.712),("XR-1509-10",2,9,48,1.25,108,.606),("XR-8094-11",2,25,230,1.02,101,.804),
("XR-3076-12",4,12,24,1.47,84,.253),("XR-8690-13",3,16,110,1.97,76,.935),("XR-6775-14",4,25,110,1.94,84,.487),("XR-2353-15",3,12,110,1.07,109,.828),
("XR-7144-16",4,25,48,.89,73,.838),("XR-8030-17",2,18,110,1.41,81,.525),("XR-9986-18",4,18,110,1.48,100,.694),("XR-6907-19",2,18,110,1.74,80,.334),
("XR-7475-20",4,18,24,1.98,75,.775),("XR-6621-21",3,32,24,1.65,94,.853),("XR-7355-22",4,9,230,2.09,105,.325),("XR-5923-23",2,16,24,1.1,78,.378)]
buf=io.BytesIO();c=canvas.Canvas(buf,pagesize=(w,h),invariant=1)
for block in range(2):
    for half in range(2):
        page=block*2+half+1
        c.setFillColor(HexColor('#17354a'));c.rect(0,h-78,w,78,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',20);c.drawString(42,h-34,'XR industrial control devices | synthetic catalog')
        c.setFont('Helvetica',11);c.drawString(42,h-56,f'Table 7  /  group {block+1}  /  '+('left half' if half==0 else 'right half - continuation'))
        heads=['Order reference','Poles','AC-3 (A)','Coil (V)'] if half==0 else ['Terminal torque (Nm)','Depth (mm)','Net mass (kg)']
        widths=[245,145,145,145] if half==0 else [230,225,225]
        x0=65;y=h-128;rh=30
        c.setFillColor(HexColor('#dce8ef'));c.rect(x0,y-rh,sum(widths),rh,fill=1,stroke=0)
        for j,head in enumerate(heads):
            c.setFillColor(HexColor('#17354a'));c.setFont('Helvetica-Bold',12);c.drawString(x0+sum(widths[:j])+10,y-19,head)
        for i,row in enumerate(rows[block*12:(block+1)*12]):
            yy=y-(i+1)*rh
            if i%2==0:
                c.setFillColor(HexColor('#eef3f5'));c.rect(x0,yy-rh,sum(widths),rh,fill=1,stroke=0)
            for j,val in enumerate(row[:4] if half==0 else row[4:]):
                c.setFillColor(HexColor('#17242d'));c.setFont('Helvetica',13);c.drawString(x0+sum(widths[:j])+10,yy-19,str(val))
            c.setStrokeColor(HexColor('#b6c6cf'));c.line(x0,yy-rh,x0+sum(widths),yy-rh)
        c.setFillColor(HexColor('#17354a'));c.setFont('Helvetica',10);c.drawString(42,24,'CEB synthetic fixture - not a manufacturer specification');c.drawRightString(w-42,24,str(page));c.showPage()
c.save()
with fitz.open(stream=buf.getvalue(),filetype='pdf') as src, fitz.open() as scan:
    for p in src:
        pix=p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);q=scan.new_page(width=p.rect.width,height=p.rect.height);q.insert_image(q.rect,stream=pix.tobytes('png'))
    scan.save(fx/'spread.pdf',garbage=4,deflate=True)
c=canvas.Canvas(str(fx/'eplan.pdf'),pagesize=(w,h),invariant=1)
def page(title,num,total):
    c.setFont('Helvetica-Bold',19);c.drawString(36,h-42,title);c.setFont('Helvetica',10);c.drawRightString(w-36,24,f'CEB IEC-style synthetic | sheet {num}/{total}')
def box(x,y,ww,hh,t):
    c.rect(x,y,ww,hh);c.setFont('Helvetica',11);c.drawCentredString(x+ww/2,y+hh/2-3,t)
def line(x,y,x2,y2):c.line(x,y,x2,y2)
def text(x,y,t):c.setFont('Helvetica',11);c.drawString(x,y,t)
page('Field signals and cable cores',1,3)
for i,(tag,wire,core) in enumerate([('B17','W470','3'),('B18','W471','4'),('B19','W472','5')]):
    y=450-i*140;box(40,y-38,140,76,'-'+tag+' PNP sensor')
    for j,(pin,net) in enumerate([('1 BN','+24V'),('4 BK',wire),('3 BU','0V')]):
        yy=y+25-j*25;line(180,yy,315,yy);text(185,yy+5,pin);box(315,yy-9,120,18,'-X10:'+str(i*3+j+1));line(435,yy,725,yy);text(445,yy+5,(f'-W7:{core} / '+net+' / 2' if j==1 else net))
c.showPage();page('Marshalling cabinet - cable / terminal mapping',2,3)
for i,(wire,core,term,refid) in enumerate([('W472','5','29','3:C1'),('W470','3','30','3:C2'),('W471','4','31','3:C3')]):
    y=440-i*115;text(45,y+12,'-W7:'+core+' / '+wire+' / 1');line(45,y,300,y);box(300,y-15,130,30,'-X1:'+term);line(430,y,755,y);text(450,y+12,wire+' / '+refid)
text(45,92,'+24V and 0V are separate power nets; not connected to signal lines.');c.showPage();page('PLC rack - channel mapping',3,3)
for i,(wire,addr,refid) in enumerate([('W471','0.3','2:C3'),('W472','0.1','2:C1'),('W470','0.2','2:C2')]):
    y=440-i*115;text(45,y+12,wire+' / '+refid);line(45,y,535,y);box(535,y-18,160,36,'-A1:I'+addr)
c.showPage();c.save()
c=canvas.Canvas(str(fx/'pid.pdf'),pagesize=(w,h),invariant=1);page('Transfer skid / control and trip loop',1,1)
box(36,265,95,100,'TK-101');box(704,265,95,100,'TK-102');line(131,310,185,310);c.circle(205,310,20);text(182,278,'P-101');line(225,310,355,310)
for x,y,tag in [(375,310,'FV-101'),(365,145,'HV-102')]:
    line(x-20,y-12,x+20,y+12);line(x-20,y+12,x+20,y-12);line(x-20,y-12,x-20,y+12);line(x+20,y-12,x+20,y+12);text(x-24,y-34,tag)
line(395,310,704,310);line(620,310,608,316);line(620,310,608,304);line(275,310,275,145);c.circle(275,310,3,fill=1);line(275,145,345,145);line(385,145,470,145);line(470,145,470,92);line(470,92,80,92);line(80,92,80,265);line(170,92,182,98);line(170,92,182,86)
for x,y,tag in [(500,375,'FT-101'),(500,465,'FIC-101'),(750,405,'LSHH-102'),(630,465,'ESD-101')]:
    c.circle(x,y,29);c.setFont('Helvetica',9);c.drawCentredString(x,y-3,tag)
line(500,346,500,310);line(750,376,750,365);c.setDash(4,3);line(500,404,500,436);line(471,465,375,465);line(375,465,375,322);line(721,405,630,405);line(630,405,630,436);line(601,465,575,465);line(575,465,575,520);line(575,520,205,520);line(205,520,205,330);c.setDash();text(36,55,'Solid: process/sensing; dashed: instrument signal. ESD-101 trips P-101 on LSHH-102.');c.showPage();c.save()
intro='Ниже длинный корпус текста с перемешанными служебными записями. Найдите связанные записи. Не используйте внешние источники.\n'
base=''.join('Архив технического отдела. Запись %06d. В отчёте отмечены проверка маркировки кабелей, испытание оборудования без нагрузки, сверка исполнительной документации, резервирование питания, контроль температур и журнал обслуживания. Итоговая редакция согласуется ответственным инженером после проверки исходных данных.\n'%i for i in range(5000))
question='\nВопрос: для устройства %s найдите действующую редакцию, предел, диапазон, поправку, контрольный идентификатор. Вычислите предел с учётом поправки (сумма). JSON: revision, pressure_kpa, span_kpa, offset_kpa, archive_key, corrected_kpa, missing_parameter (null: если частота коммутации не указана).'
def ctx(n,size,device,records,expected_hash):
    s=base[:size]
    for offset,record in reversed(records):s=s[:offset]+'\n'+record+'\n'+s[offset:]
    data=(intro+s+question%device).encode('utf-8')
    assert hashlib.sha256(data).hexdigest()==expected_hash, f'context {n} byte mismatch'
    (out/f'context{n}-preview.txt').write_bytes(data)
ctx(32,141358,'R28203434',[(48065,'Действующий выпуск 64, площадка R26307664: предел 201 кПа; калибровочная карточка R18486692.'),(74927,'Карточка R18486692: диапазон 1586 кПа, поправка 71 кПа; ключ архива R94666609.'),(86224,'Запись инвентаризации: устройство R28203434 имеет площадку R26307664; для окончательного выбора применяется выпуск 64.'),(97541,'Выпуск 63, площадка R26307664: предел 291 кПа, отменён.'),(113085,'Площадка R54215023: похожее оборудование, предел 211 кПа.'),(118746,'Архив R94666609: контрольный идентификатор R66800689.')],'e478e2214c9bbdd48685ab2058145a52d901733b194eb118f893b6c18da8991d')
ctx(256,1203913,'R58667135',[(276903,'Выпуск 24, площадка R70321206: предел 830 кПа, отменён.'),(445444,'Действующий выпуск 25, площадка R70321206: предел 740 кПа; калибровочная карточка R23495381.'),(650117,'Архив R82981903: контрольный идентификатор R96697823.'),(842724,'Карточка R23495381: диапазон 1792 кПа, поправка 59 кПа; ключ архива R82981903.'),(1059425,'Площадка R98172385: похожее оборудование, предел 750 кПа.'),(1107584,'Запись инвентаризации: устройство R58667135 имеет площадку R70321206; для окончательного выбора применяется выпуск 25.')],'19937aa16e99f78d8a3e81d965c3e10744c6dfb251eaacddfa8b9ab727955afe')
filler='В учебном архиве перечислены протоколы проверки и монтажные отчёты. Запись не содержит целевых параметров.\n'*12000
facts=['Актив R128-C9: актуальная редакция 18, площадка NORTH.','R128-C9 NORTH редакция 17: предел 99 kPa, отменена.','R128-C9 NORTH редакция 18: предел 428 kPa, диапазон 1000 kPa.','R128-C9 NORTH редакция 18: поправка -13 kPa.','R128-C9 NORTH редакция 18: архив AX-9473.','R128-C9 SOUTH редакция 18: предел 822 kPa; другая площадка.']
(out/'context128-preview.txt').write_text(''.join(filler[i*len(filler)//7:(i+1)*len(filler)//7]+('\n'+facts[i]+'\n' if i<6 else '') for i in range(7)),encoding='utf-8')
for name,n in [('spread.pdf',4),('eplan.pdf',3),('pid.pdf',1)]:
    with fitz.open(fx/name) as d:
        assert len(d)==n
        if name=='spread.pdf':assert all(not p.get_text().strip() for p in d)
        for i,p in enumerate(d):
            p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(fx/f'{name[:-4]}-page-{i+1}.png')
files=[f for f in out.rglob('*') if f.is_file() and f.name not in ('input-pack.zip','inventory.json')]
inventory=[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(files)]
(out/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
with zipfile.ZipFile(out/'input-pack.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for f in files+[out/'inventory.json']:
        z.write(f,f.relative_to(out))
print('CEB public input pack:',len(inventory),'files; no keys or reference answers')
