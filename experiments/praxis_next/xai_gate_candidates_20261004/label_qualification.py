"""Apply the frozen source gate; audit ordering without fitting or inferring labels."""
import collections
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile
import numpy as np
import dpkt

ROOT=Path(__file__).resolve().parent
CACHE=Path('C:/w/px107_source_qualification/cic_browser_20261004')
freeze=json.loads((ROOT/'QUALIFICATION_FREEZE.json').read_text())
assert hashlib.sha256((ROOT/'QUALIFICATION_PROTOCOL.txt').read_bytes()).hexdigest()==freeze['protocol_sha256']
inventory=json.loads((ROOT/'CIC_COMPLETE_INVENTORY.json').read_text())
archives={a['sha256']:a for a in inventory['archives']}
results=[]
for sha,a in archives.items():
    path=CACHE/(sha+'.zip')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    with zipfile.ZipFile(path) as z:
        for m in a['members']:
            if 'pcap' not in m: continue
            raw=z.read(m['path']); assert hashlib.sha256(raw).hexdigest()==m['sha256']
            assert raw[:4]==b'\xd4\xc3\xb2\xa1', 'Unexpected timestamp precision/endianness'
            offset=24; ts=[]; duplicates=0; seen=set(); ip_valid=udp_valid=0
            queries=complete_questions=incomplete_questions=0
            while offset<len(raw):
                sec,usec,cap,wire=struct.unpack_from('<IIII',raw,offset); offset+=16
                packet=raw[offset:offset+cap]; offset+=cap
                t=sec*1_000_000+usec; ts.append(t)
                ident=hashlib.sha256(struct.pack('<QI',t,wire)+packet).digest()
                duplicates+=int(ident in seen); seen.add(ident)
                # Audits only: valid IPv4 headers permit length/direction features.
                if len(packet)>=34 and packet[12:14]==b'\x08\x00':
                    ihl=(packet[14]&15)*4
                    total=struct.unpack_from('!H',packet,16)[0]
                    if ihl>=20 and len(packet)>=14+ihl and total>=ihl:
                        ip_valid+=1
                        frag=struct.unpack_from('!H',packet,20)[0]
                        if packet[23]==17 and frag&8191==0 and len(packet)>=14+ihl+8:
                            udp_valid+=1
                            base=14+ihl
                            sport,dport,ulen,checksum=struct.unpack_from('!HHHH',packet,base)
                            payload=packet[base+8:base+ulen]
                            if dport==53 and len(payload)>=12:
                                _,flags,qd,_,_,_=struct.unpack_from('!HHHHHH',payload)
                                if flags&32768==0 and qd>0:
                                    queries+=1
                                    try:
                                        pos=12
                                        for _ in range(qd):
                                            name,pos=dpkt.dns.unpack_name(payload,pos)
                                            if pos+4>len(payload): raise dpkt.NeedData()
                                            pos+=4
                                        complete_questions+=1
                                    except (dpkt.UnpackError, ValueError, IndexError, UnicodeError):
                                        incomplete_questions+=1
            times=np.asarray(ts,dtype=np.int64); order=np.argsort(times,kind='stable')
            gaps=np.diff(times); sorted_times=times[order]
            assert np.all(np.diff(sorted_times)>=0)
            assert len(times)==m['pcap']['packets']
            results.append({'capture':m['path'],'sha256':m['sha256'],'packets':len(times),
                'backward_steps':int((gaps<0).sum()),
                'maximum_backward_microseconds':int(max(0,-int(gaps.min()))) if len(gaps) else 0,
                'records_moved_by_stable_sort':int((order!=np.arange(len(times))).sum()),
                'exact_duplicate_record_occurrences':duplicates,
                'valid_ipv4_headers':ip_valid,'available_ipv4_udp_headers':udp_valid,
                'ipv4_dns_query_packets':queries,'complete_question_sections':complete_questions,
                'incomplete_or_invalid_question_sections':incomplete_questions,
                'ordering_check_pass':True,
                'author_capture_category':'attack' if m['path'].startswith('Attacks/') else 'benign',
                'packet_attack_membership':'NOT_VERIFIED',
                'successful_transfer_evidence':'NOT_PRESENT_IN_DOWNLOADED_ARCHIVES',
                'verified_successful_episode_count':None})
            print(m['path'], 'ordering audited', flush=True)
out={'protocol_sha256':freeze['protocol_sha256'],'captures':results,
     'summary':{'captures':len(results),'captures_with_backward_steps':sum(r['backward_steps']>0 for r in results),
                'attack_captures_with_backward_steps':sum(r['backward_steps']>0 and r['author_capture_category']=='attack' for r in results),
                'backward_steps':sum(r['backward_steps'] for r in results),
                'records_moved_by_stable_sort':sum(r['records_moved_by_stable_sort'] for r in results),
                'exact_duplicate_record_occurrences':sum(r['exact_duplicate_record_occurrences'] for r in results),
                'affected_verified_episode_count':None},
     'G0':'NOT_PASSED_EPISODE_PROVENANCE_AND_COMPLETION_UNVERIFIED',
     'G1':'NOT_PASSED_COMPLETE_DNS_COMPOSITE_UNAVAILABLE_FROM_TRUNCATED_QUERIES',
     'headroom':'NOT_EVALUABLE_NOT_ZERO',
     'fits_performed':0,'new_aws_spend_usd':0,
     'PX108':'STOP_BEFORE_FITTING_ON_CURRENT_EVIDENCE',
     'PX109':'WAIT_FOR_VERIFIED_DUMMY_TRANSFER_ARM',
     'interpretation':'Author capture categories support a limited capture-level study; they do not establish independent successful exfiltration episodes. Packet-header availability does not remedy missing completion evidence.'}
(ROOT/'LABEL_QUALIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='captures'},indent=2))
