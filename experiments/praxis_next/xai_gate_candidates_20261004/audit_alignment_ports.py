"""Independent raw-header check of uniquely timestamp-matched CSV packet ports."""
import io,json,struct,zipfile
from pathlib import Path
from collections import Counter
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
CACHE=Path('C:/w/px107_source_qualification/cic_browser_20261004')
archives={a['sha256']:a for f in ['CIC_COMPLETE_INVENTORY.json','CIC_NEW_CSV_INVENTORY.json'] for a in json.loads((ROOT/f).read_text())['archives']}
pcaps={Path(m['path']).name:(a,m) for a in archives.values() for m in a['members'] if 'pcap' in m}
reference={r['csv']:r for r in json.loads((ROOT/'STATELESS_ALIGNMENT.json').read_text())['files']}
rows=[]
for a in archives.values():
    for m in a['members']:
        if 'stateless_features-' not in m['path']:continue
        name=Path(m['path']).name.removeprefix('stateless_features-').removesuffix('.csv')
        if name=='light_benign.pcap':name='benign.pcap'
        pa,pm=pcaps[name]
        with zipfile.ZipFile(CACHE/(a['sha256']+'.zip')) as z:
            df=pd.read_csv(io.BytesIO(z.read(m['path'])),usecols=['timestamp'])
        times=pd.to_datetime(df.timestamp,format='mixed').to_numpy(dtype='datetime64[us]').astype('int64')
        with zipfile.ZipFile(CACHE/(pa['sha256']+'.zip')) as z: raw=z.read(pm['path'])
        offset=24; metadata={}
        while offset<len(raw):
            s,u,cap,wire=struct.unpack_from('<IIII',raw,offset);offset+=16
            p=raw[offset:offset+cap];offset+=cap
            transport=None
            if len(p)>=34 and p[12:14]==b'\x08\x00' and p[23]==17:
                ihl=(p[14]&15)*4
                if ihl>=20 and struct.unpack_from('!H',p,20)[0]&8191==0:transport=14+ihl
            elif len(p)>=54 and p[12:14]==b'\x86\xdd' and p[20]==17:transport=54
            ports=struct.unpack_from('!HH',p,transport) if transport is not None and len(p)>=transport+8 else None
            metadata.setdefault(s*1_000_000+u,[]).append(ports)
        counts=Counter();pairs=Counter()
        for t in times:
            candidates=metadata.get(int(t),[])
            if len(candidates)!=1:continue
            ports=candidates[0]
            if ports is None:counts['unsupported_header']+=1
            else:
                sp,dp=ports;pairs[str(ports)]+=1
                counts['UDP53_query_direction' if dp==53 else ('UDP53_response_direction' if sp==53 else 'UDP_other')]+=1
        expected=reference[m['path']]['matched_packet_protocol_counts']
        checks={k:counts[k]==expected.get(k,0) for k in ['UDP53_query_direction','UDP53_response_direction','UDP_other']}
        rows.append({'csv':m['path'],'counts':dict(counts),'port_pairs_top':dict(pairs.most_common(8)),'checks':checks})
out={'files':rows,'all_checks_pass':all(all(r['checks'].values()) for r in rows),'checks':sum(len(r['checks']) for r in rows)}
(ROOT/'ALIGNMENT_PORT_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
assert out['all_checks_pass']
print(json.dumps({'all_checks_pass':out['all_checks_pass'],'checks':out['checks']}))
