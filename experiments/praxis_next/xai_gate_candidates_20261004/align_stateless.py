"""Exact timestamp alignment audit; no inferred row labels and no model fitting."""
import collections
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile
import numpy as np
import pandas as pd
import dpkt

ROOT=Path(__file__).resolve().parent
CACHE=Path('C:/w/px107_source_qualification/cic_browser_20261004')
old=json.loads((ROOT/'CIC_COMPLETE_INVENTORY.json').read_text())
new=json.loads((ROOT/'CIC_NEW_CSV_INVENTORY.json').read_text())
archives={a['sha256']:a for a in old['archives']+new['archives']}
pcaps={Path(m['path']).name:(a,m) for a in archives.values() for m in a['members'] if 'pcap' in m}
results=[]
for a in archives.values():
    for m in a['members']:
        if 'stateless_features-' not in m['path']: continue
        basename=Path(m['path']).name.removeprefix('stateless_features-').removesuffix('.csv')
        if basename=='light_benign.pcap': basename='benign.pcap'
        pa,pm=pcaps[basename]
        with zipfile.ZipFile(CACHE/(a['sha256']+'.zip')) as z:
            data=z.read(m['path'])
        assert hashlib.sha256(data).hexdigest()==m['sha256']
        df=pd.read_csv(io.BytesIO(data))
        parsed=pd.to_datetime(df.timestamp,format='mixed',errors='coerce')
        assert parsed.notna().all(), 'Unparseable timestamp'
        times=parsed.to_numpy(dtype='datetime64[us]').astype('int64')
        with zipfile.ZipFile(CACHE/(pa['sha256']+'.zip')) as z: raw=z.read(pm['path'])
        assert hashlib.sha256(raw).hexdigest()==pm['sha256']
        assert raw[:4]==b'\xd4\xc3\xb2\xa1'
        packet_times=[]; metadata=[]; offset=24
        while offset<len(raw):
            sec,usec,cap,wire=struct.unpack_from('<IIII',raw,offset); offset+=16
            packet=raw[offset:offset+cap];offset+=cap
            packet_times.append(sec*1_000_000+usec)
            proto='other'; qname=None; ports=None
            try:
                net=dpkt.ethernet.Ethernet(packet).data
                transport=net.data
                if isinstance(transport,dpkt.udp.UDP):
                    ports=(int(transport.sport),int(transport.dport))
                    proto='UDP53_query_direction' if transport.dport==53 else ('UDP53_response_direction' if transport.sport==53 else 'UDP_other')
                    if transport.dport==53 and len(transport.data)>=12:
                        _,flags,qd,_,_,_=struct.unpack_from('!HHHHHH',transport.data)
                        if flags&32768==0 and qd:
                            qname,end=dpkt.dns.unpack_name(transport.data,12)
                            if end+4>len(transport.data):qname=None
                elif isinstance(transport,dpkt.tcp.TCP): proto='TCP'
            except (dpkt.UnpackError,ValueError,AttributeError,UnicodeError,IndexError): pass
            metadata.append((proto,qname,ports))
        packet_times=np.asarray(packet_times,dtype=np.int64)
        order=np.argsort(packet_times,kind='stable'); st=packet_times[order]
        lo=np.searchsorted(st,times,side='left'); hi=np.searchsorted(st,times,side='right')
        matches=hi-lo
        protocols=collections.Counter(); port_pairs=collections.Counter(); length_comparisons=length_matches=0
        for row in np.flatnonzero(matches==1):
            proto,name,ports=metadata[order[lo[row]]]; protocols[proto]+=1
            if ports is not None: port_pairs[str(ports)]+=1
            if name is not None:
                length_comparisons+=1
                length_matches+=int(float(df.FQDN_count.iloc[row])==len(name))
        numeric=df.drop(columns=['timestamp','longest_word','sld']).apply(pd.to_numeric,errors='coerce')
        results.append({'csv':m['path'],'csv_sha256':m['sha256'],'pcap':pm['path'],
            'rows':len(df),'literal_time_exact_unique_matches':int((matches==1).sum()),
            'literal_time_ambiguous_matches':int((matches>1).sum()),'unmatched':int((matches==0).sum()),
            'csv_duplicate_timestamps':int(df.timestamp.duplicated().sum()),
            'nonfinite_numeric_cells':int((~np.isfinite(numeric.to_numpy())).sum()),
            'matched_packet_protocol_counts':dict(protocols),
            'matched_udp_port_pairs_top':dict(port_pairs.most_common(12)),
            'complete_question_length_comparisons':length_comparisons,
            'FQDN_count_equals_decoded_name_length':length_matches,
            'sld_top_counts':{str(k):int(v) for k,v in df.sld.value_counts(dropna=False).head(8).items()},
            'first_timestamp':str(parsed.min()),'last_timestamp':str(parsed.max()),
            'label_columns':[c for c in df.columns if c.lower() in ['label','class','attack','malicious']],
            'timestamp_assumption':'Literal CSV clock compared to PCAP epoch as UTC, no fitted offset; coincidence alone is not clock provenance.'})
        print(basename,len(df),int((matches==1).sum()),'unique matches',flush=True)
out={'files':results,'totals':{k:sum(r[k] for r in results) for k in ['rows','literal_time_exact_unique_matches','literal_time_ambiguous_matches','unmatched','complete_question_length_comparisons','FQDN_count_equals_decoded_name_length']},
    'scope':'Alignment and schema audit only; no model fitted, no label inferred from directory.',
    'constraint':'Full DNS properties remain publisher-supplied for truncated questions; no receiver-completion claim.'}
(ROOT/'STATELESS_ALIGNMENT.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out['totals'],indent=2))
