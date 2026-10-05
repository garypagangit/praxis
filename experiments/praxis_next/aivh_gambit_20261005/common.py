"""Common read-only command representation; never executes input."""
import re,shlex
from pathlib import PurePosixPath
ALLOW={'id','whoami','uname','hostname','pwd','ls','cat','find','grep','head',
       'tail','wc','file','stat','env','printenv','groups','ps','ip','ifconfig',
       'netstat','ss','route','arp','df','du','free','uptime','which','whereis',
       'getent','lscpu','lsblk','mount','nmap'}
def command(text):
    if not isinstance(text,str) or any(c in text for c in ['\n','\r',';','|','&','>','<','`','$']):return None
    try:parts=shlex.split(text)
    except ValueError:return None
    if not parts:return None
    verb=PurePosixPath(parts[0]).name
    if verb not in ALLOW:return None
    args=[]
    for x in parts[1:]:
        x=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d+)?\b','IP_ADDRESS',x)
        if x.startswith('/'):x='PATH'
        x=re.sub(r'\b\d+\b','NUMBER',x)
        args.append(x)
    return ' '.join([verb]+args)

def inputs(rows,kind):
    if kind=='length':
        return [[sum(len(c) for c in r['commands'])/10,
                 sum(len(c.split()) for c in r['commands'])/10] for r in rows]
    if kind=='verbs':return [' '.join(c.split()[0] for c in r['commands']) for r in rows]
    return ['\n'.join(r['commands']) for r in rows]
