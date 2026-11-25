#!/usr/bin/env python3
"""Local input tool emulator; no network. python tool-service.py search KX-215"""
import json, sys, decimal
from pathlib import Path
docs=json.loads((Path(__file__).parent/'fixtures/tool-catalog.json').read_text())
cmd,*args=sys.argv[1:]
if cmd=='search' and len(args)==1:
    print(json.dumps([{'doc_id':k,'snippet':v[:60]} for k,v in docs.items() if args[0].casefold() in v.casefold()]))
elif cmd=='read' and len(args)==1 and args[0] in docs:
    print(json.dumps({'doc_id':args[0],'content':docs[args[0]]}))
elif cmd=='multiply' and len(args)==2:
    print(json.dumps({'value':str(decimal.Decimal(args[0])*decimal.Decimal(args[1]))}))
else:sys.exit('usage: search query | read doc_id | multiply a b')
