"""Publish metadata-only qualification; original and prepared flow rows stay private."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def feature_description(name):
    """Field meanings paraphrase author README Table3; unresolved units are explicit."""
    inferred='Unit inferred from CICFlowMeter convention; not stated for this row in author Table3.'
    direct='Unit or dimension stated by the author feature description.'
    if name=='Protocol':return 'Transport/network protocol identifier','integer protocol code',direct
    if name=='Flow Duration':return 'Elapsed flow duration','microseconds',direct
    if name in ['Total Fwd Packet','Total Bwd packets']:
        return 'Total packets in '+('forward' if 'Fwd' in name else 'backward')+' direction','packets',direct
    if name.startswith('Total Length of '):return 'Sum of packet sizes in '+('forward' if 'Fwd' in name else 'backward')+' direction','bytes',inferred
    if 'Packet Length' in name or name in ['Average Packet Size','Fwd Segment Size Avg','Bwd Segment Size Avg','Fwd Seg Size Min']:
        direction='forward ' if name.startswith('Fwd') else ('backward ' if name.startswith('Bwd') else '')
        statistic={'Max':'maximum','Min':'minimum','Mean':'mean','Std':'standard deviation','Variance':'variance','Avg':'mean'}.get(name.split()[-1],'mean')
        return f'{statistic.capitalize()} {direction}packet/segment size','bytes squared' if name.endswith('Variance') else 'bytes',inferred+' Header/payload inclusion and exact segment semantics are not independently implementation-verified.'
    if name.endswith('Bytes/s'):return 'Flow byte rate','bytes/second',direct
    if name.endswith('Packets/s'):return ('Forward' if name.startswith('Fwd') else ('Backward' if name.startswith('Bwd') else 'Flow'))+' packet rate','packets/second',direct
    if ' IAT ' in name:
        direction={'Flow':'bidirectional flow','Fwd':'forward direction','Bwd':'backward direction'}[name.split()[0]]
        statistic={'Mean':'mean','Std':'standard deviation','Max':'maximum','Min':'minimum','Total':'total'}[name.split()[-1]]
        return f'{statistic.capitalize()} inter-arrival interval in {direction}','microseconds',inferred
    if ' Flags' in name or name.endswith('Flag Count'):
        flag=name.split()[1] if name.startswith(('Fwd','Bwd')) else name.split()[0]
        direction=' in '+('forward' if name.startswith('Fwd') else 'backward')+' direction' if name.startswith(('Fwd','Bwd')) else ''
        return f'Packets with TCP {flag} flag{direction}','count',direct+' Exact extractor flag-count behavior remains version-dependent and unqualified.'
    if name.endswith('Header Length'):return 'Summed '+('forward' if name.startswith('Fwd') else 'backward')+' header size','bytes',direct
    if name=='Down/Up Ratio':return 'Download-to-upload traffic ratio','dimensionless',direct+' README does not specify packet-versus-byte denominator or zero-denominator handling.'
    if '/Bulk ' in name or 'Bulk Rate' in name:
        direction='forward' if name.startswith('Fwd') else 'backward'
        unit='bytes/bulk' if 'Bytes/Bulk' in name else ('packets/bulk' if 'Packet/Bulk' in name else 'bytes/second')
        return f'Mean {direction} '+('bulk throughput' if 'Rate' in name else ('bulk byte size' if 'Bytes/' in name else 'bulk packet count')),unit,'Inferred CICFlowMeter convention only; the author bulk-rate wording is underspecified, and bulk grouping/settings are unqualified.'
    if name.startswith('Subflow '):
        unit='bytes/subflow' if name.endswith('Bytes') else 'packets/subflow'
        return 'Mean '+('forward' if 'Fwd' in name else 'backward')+' '+('byte' if name.endswith('Bytes') else 'packet')+' amount per subflow',unit,direct+' Subflow timeout/grouping settings are unqualified.'
    if 'Init Win' in name:return 'Initial '+('forward' if name.startswith('FWD') else 'backward')+' TCP window measurement','bytes',direct+' Exact window extraction and missing/sentinel behavior are unqualified; source values are not reinterpreted.'
    if name=='Fwd Act Data Pkts':return 'Forward packets with at least one TCP payload byte','packets',direct
    if name.startswith('Active '):
        statistic={'Mean':'mean','Std':'standard deviation','Max':'maximum','Min':'minimum'}[name.split()[-1]]
        return f'{statistic.capitalize()} duration of an active interval before idleness','microseconds',inferred+' Active/idle timeout settings are unqualified.'
    raise ValueError('Feature has no explicit semantic mapping: '+name)


def qualify(private_root,output):
    source=private_root/'sandworm';prepared=private_root/'sandworm_prepared_v3'
    manifest_path=prepared/'MANIFEST.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if sha(prepared/'DATA.npz')!=manifest['target_data_npz_sha256']:raise ValueError('Target binding changed.')
    if sha(Path(__file__).with_name('prepare_sandworm.py'))!=manifest['adapter_sha256']:raise ValueError('Adapter changed since preparation.')
    metadata_path=source/'ZENODO_METADATA.json';metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
    landing=private_root/'source_metadata'/'sandworm_landing.html'
    landing_text=landing.read_text(encoding='utf-8')
    if metadata['metadata']['license']['id']!='cc-by-4.0' or 'CC BY-NC-ND 4.0' not in landing_text:raise ValueError('Recheck rights fields.')
    acquisition=source/'ACQUISITION.json'
    rights={'schema_version':1,'amends_acquisition_sha256':sha(acquisition),'original_acquisition_preserved':True,
            'metadata_sha256':sha(metadata_path),'landing_html_sha256':sha(landing),'dataset_doi':'10.5281/zenodo.16911636',
            'api_license_field':'cc-by-4.0','landing_license_field':'Creative Commons Attribution 4.0 International',
            'landing_copyright_field':'CC BY-NC-ND 4.0 Attribution-NonCommercial-NoDerivatives 4.0 International',
            'correction':'The first acquisition receipt copied only API license metadata. It is incomplete as a rights summary; use this amendment and preserve the original.',
            'use_scope':'Private noncommercial research/evaluation. Publish code, provenance, hashes and aggregate statistics only. Do not redistribute original or adapted data.',
            'rights_resolved':False,'new_permissions_obtained':False}
    rights_path=source/'RIGHTS_AMENDMENT.json';encoded=json.dumps(rights,indent=2,sort_keys=True)+'\n'
    if rights_path.exists() and rights_path.read_text(encoding='utf-8')!=encoded:raise ValueError('Existing amendment differs; preserve and version a new one.')
    if not rights_path.exists():rights_path.write_text(encoded,encoding='utf-8')
    fields=[]
    for index,name in enumerate(manifest['feature_names']):
        meaning,unit,qualification=feature_description(name)
        fields.append({'index':index,'source_name':name,'target_name':name,'name_match':'exact',
                       'meaning':meaning,'unit_convention':unit,'unit_qualification':qualification,
                       'extractor_implementation_equivalence':'NOT_QUALIFIED','transform':'identity; no target-fitted transform'})
    if len(fields)!=73:raise ValueError('Feature count differs.')
    compatibility={'schema_version':1,'feature_count':73,'field_name_order_matches_source':True,
                   'basis':'Author Sandworm README Table3, printed pages9-11; source uses frozen SCVIC CICFlowMeter names in the existing E1 manifest.',
                   'source_manifest_sha256':manifest['source_manifest_sha256'],'target_manifest_sha256':sha(manifest_path),
                   'author_readme_sha256':sha(source/'APT_Dataset_Readme.pdf'),
                   'exact_extractor_revisions_settings_qualified':False,
                   'interpretation':'Name/field compatibility permits a descriptive external transfer test. Unknown extractor versions/settings, omitted metadata and inferred units prevent a claim of bitwise semantic equivalence. No unit conversion is applied.',
                   'features':fields}
    output.mkdir(parents=True,exist_ok=True)
    (output/'FEATURE_COMPATIBILITY.json').write_text(json.dumps(compatibility,indent=2)+'\n',encoding='utf-8')
    lines=['# Sandworm feature compatibility','',
           'All 73 frozen SCVIC predictor names occur exactly in the author Sandworm CSV. The adapter preserves their order and numeric values. This qualifies a descriptive transfer test; it does not establish identical extractor implementations.','',
           'Meanings below paraphrase [author README Table 3, pages 9–11](https://zenodo.org/records/16911636/files/APT_Dataset_Readme.pdf). Microseconds are explicit for Flow Duration. Other time units and bulk units follow CICFlowMeter conventions and are marked as inferred in the [machine-readable record](FEATURE_COMPATIBILITY.json). Counts, bytes and rates use the dimensions stated or implied by their feature definitions. Exact extractor revisions, timeout settings, sentinel handling, packet/header treatment and bulk grouping were not supplied sufficiently to prove equivalence. No target-fitted conversion is applied.','',
           '| Source and target column (same spelling/order) | Meaning | Unit convention |','|---|---|---|']
    lines.extend(f"| {f['source_name']} | {f['meaning']} | {f['unit_convention']} |" for f in fields)
    lines.extend(['','The source feature exclusion rule remains frozen: identifiers, IPs, ports, timestamps, labels and all Idle summaries are excluded. Target-only RST direction flags, backward payload/segment fields, ICMP metadata, retransmission counters and Total Connection Flow Time are also excluded. They are not padded into the source model.',''])
    (output/'FEATURE_COMPATIBILITY.md').write_text('\n'.join(lines),encoding='utf-8')
    report={k:v for k,v in manifest.items()}
    report.update({'qualification':'QUALIFIED_FOR_DESCRIPTIVE_FRESH_BINARY_TRANSFER_ONLY','target_manifest_sha256':sha(manifest_path),
                   'source_acquisition_sha256':sha(acquisition),'rights_amendment_sha256':sha(rights_path),
                   'rights_amendment':rights,'feature_compatibility_sha256':sha(output/'FEATURE_COMPATIBILITY.json'),
                   'target_observed_outcomes':False,'scientific_fits':0,'canonical_private_directory_name':'sandworm_prepared_v3',
                   'preserved_development_attempts':{'sandworm_prepared':'Manifest serialization failed after writing DATA; not qualified.',
                                                     'sandworm_prepared_v2':'Procedure labels were stored as object dtype and rejected by allow_pickle=False; no fits or predictions; superseded by v3.'}})
    (output/'SANDWORM_QUALIFICATION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    unraveled=json.loads((private_root/'UNRAVELED_SOURCE_AUDIT.json').read_text(encoding='utf-8'))
    safe={k:v for k,v in unraveled.items() if k not in {'files','capture_directory_stage_counts','stage_signature_counts'}}
    safe['private_source_audit_sha256']=sha(private_root/'UNRAVELED_SOURCE_AUDIT.json')
    (output/'UNRAVELED_QUALIFICATION.json').write_text(json.dumps(safe,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'feature_count':len(fields),'unique_rows':manifest['unique_rows'],'rights_discrepancy_documented':True,'models_fit':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();qualify(args.private_root,args.output)
