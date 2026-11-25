#!/usr/bin/env python3
"""Owner/agent workspace timer. Run only inside a disposable isolated workspace.
Records actual wall time, exit status and command label. Does not create a sandbox."""
import argparse,datetime,json,os,pathlib,subprocess,time,sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--log',type=pathlib.Path,required=True);p.add_argument('--tool',required=True)
p.add_argument('--purpose',required=True);p.add_argument('--timeout',type=float,default=300)
p.add_argument('--command',nargs=argparse.REMAINDER,required=True);a=p.parse_args()
if not a.command or not 0<a.timeout<=1800:p.error('command and valid timeout required')
if os.geteuid()==0:p.error('Refusing root; run as unprivileged user in disposable sandbox')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
start=now();tick=time.monotonic();result=None
try:result=subprocess.run(a.command,timeout=a.timeout,check=False).returncode
except subprocess.TimeoutExpired:result=124
except OSError:result=127
row={'tool':a.tool,'purpose':a.purpose,'started_at':start,'ended_at':now(),'wall_seconds':round(time.monotonic()-tick,6),'exit_code':result,'status':'ok' if result==0 else 'failed'}
a.log.parent.mkdir(parents=True,exist_ok=True)
with a.log.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
sys.exit(result)
