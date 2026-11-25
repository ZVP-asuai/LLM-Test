import sys,json,pathlib
d=json.loads(pathlib.Path(__file__).with_name('tool-data.json').read_text())
cmd,*args=sys.argv[1:]
if cmd=='query' and args==['BR-72']:print(json.dumps([{"id":v["id"],"rev":v["rev"],"state":v["state"]} for v in d.values()]))
elif cmd=='read' and len(args)==1:
 v=next((v for v in d.values() if v['id']==args[0]),None)
 if not v:sys.exit(2)
 p=pathlib.Path('.ceb-retry-marker')
 if v['state']=='approved' and not p.exists():p.touch();print('{"error":"temporary","retryable":true}');sys.exit(75)
 print(json.dumps(v))
elif cmd=='calculate' and len(args)==2:
 from decimal import Decimal
 print(json.dumps({"product":str(Decimal(args[0])*Decimal(args[1]))}))
else:sys.exit(2)
