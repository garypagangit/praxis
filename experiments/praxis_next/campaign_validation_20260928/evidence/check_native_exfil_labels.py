"""Describe native exfiltration labels without modifying any frozen model input."""
from pathlib import Path
import json,zipfile
import pandas as pd
ROOT=Path(__file__).resolve().parent
DATA=Path('C:/w/campaign_validation_20260928/ait')
out=[]
for p in sorted(DATA.glob('*_netflows.zip')):
    with zipfile.ZipFile(p) as z:
        with z.open('udp_complete.csv') as r:
            d=pd.read_csv(r,usecols=['label','c_port:2','s_port:11','role_cli','role_serv'])
    e=d[d.label.eq('data exfiltration')]
    dns=e['c_port:2'].eq(53)|e['s_port:11'].eq(53)
    attacker=e.role_cli.eq('attacker_0')|e.role_serv.eq('attacker_0')
    out.append({'execution':p.stem.replace('_netflows',''),'native_exfil_rows':len(e),
                'dns_port_rows':int(dns.sum()),'publisher_attacker_endpoint_rows':int(attacker.sum()),
                'dns_and_publisher_attacker_endpoint':int((dns&attacker).sum()),
                'non_dns_native_exfil_rows':int((~dns).sum()),
                'interpretation':'Consistency with publisher topology/port rule only; not payload verification. These fields are excluded from predictors.'})
(ROOT/'NATIVE_LABEL_DIAGNOSTIC.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
