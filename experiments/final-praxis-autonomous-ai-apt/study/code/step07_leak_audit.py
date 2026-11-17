"""Step 7: leak audit (design section 6.6).

After cleaning, every output file in data/ is searched for everything sections
6.2-6.5 should have removed, using the same patterns (s3_clean.LEAK_PATTERNS):
identity, wrapper text anywhere in the output, validator-family names in kept
text, collection tooling, scratch directory names. Recorder text is searched
as one stream per login, so a token cut between two records is still found.
Audit arguments are checked one by one. The count must be zero.

Target content is not flagged (the target web server has a /goad-autonomy/ path).
The private key map is the one file that holds original ids by design; it is
not searched.
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_audit as A
import s3_clean as K
import s3_config as C
import s3_io as IO

STEP = "07_leak_audit"
INFO_PATTERNS = [("setup_check_sentinel", K.re.compile(rb"AHIR_CHECK"))]   # reported, not part of 6.2-6.5


def search(data, hits, where, info, bare_uid=False, uid_field=False):
    for name, rx in K.LEAK_PATTERNS:
        n = len(rx.findall(data))
        if n:
            hits.append(dict(pattern=name, count=n, where=where,
                             sample=rx.search(data).group(0).decode("utf-8", "replace")[:60]))
    if bare_uid:
        n = len(K.LEAK_UID_BARE.findall(data))
        if n:
            hits.append(dict(pattern="user_number_bare", count=n, where=where, sample=""))
    if uid_field:
        n = len(K.LEAK_UID_FIELD.findall(data))
        if n:
            hits.append(dict(pattern="user_number_field", count=n, where=where, sample=""))
    for name, rx in INFO_PATTERNS:
        n = len(rx.findall(data))
        if n:
            info[name] = info.get(name, 0) + n


def main():
    root = os.path.join(C.out_root(), "data")
    hits = []
    info = {}
    files = 0
    checked = dict(recorder_streams=0, recorder_messages=0, audit_messages=0, audit_arguments=0,
                   window_records=0, command_texts=0, table_files=0)
    for dirpath, dirs, names in os.walk(root):
        dirs.sort()
        if os.path.basename(dirpath) == "_private":
            continue
        for name in sorted(names):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, C.out_root())
            files += 1
            if name.endswith(".recorder.jsonl"):
                ins, outs = [], []
                for line in open(path, encoding="utf-8"):
                    o = json.loads(line)
                    msg = json.loads(o["message"])
                    slim = {k: v for k, v in msg.items() if k != "data_base64"}
                    search(json.dumps(slim).encode(), hits, rel + " (message fields)", info, uid_field=False)
                    for key in ("uid", "audit_uid"):
                        if str(msg.get(key, "")) not in ("", "None", K.UIDNUM.decode()):
                            hits.append(dict(pattern="user_number_field", count=1, where=rel, sample=key))
                    if "connection" in msg:
                        hits.append(dict(pattern="client_address", count=1, where=rel, sample="connection field"))
                    checked["recorder_messages"] += 1
                    if msg["kind"] == "input":
                        ins.append(base64.b64decode(msg["data_base64"]))
                    elif msg["kind"] == "output":
                        outs.append(base64.b64decode(msg["data_base64"]))
                search(b"".join(ins), hits, rel + " (input stream)", info, bare_uid=True)
                search(b"".join(outs), hits, rel + " (output stream)", info, bare_uid=True)
                checked["recorder_streams"] += 2
            elif name.endswith(".audit.jsonl"):
                for line in open(path, encoding="utf-8"):
                    msg = json.loads(line)["message"]
                    search(msg.encode(), hits, rel, info, uid_field=True)
                    checked["audit_messages"] += 1
                    for k, v in A.fields(msg):
                        base = k.split("[")[0]
                        if A.RE_ARG.match(base) or base in ("proctitle", "name", "cwd", "exe", "comm", "cmd"):
                            search(A.decode_value(v).encode(), hits, rel + " (argument)", info)
                            checked["audit_arguments"] += 1
            elif name.endswith(".commands.jsonl"):
                for line in open(path, encoding="utf-8"):
                    search(json.loads(line)["text"].encode(), hits, rel, info, bare_uid=True)
                    checked["command_texts"] += 1
            elif name.endswith(".jsonl"):                      # window files
                ins, outs = [], []
                for line in open(path, encoding="utf-8"):
                    r = json.loads(line)
                    checked["window_records"] += 1
                    if r["src"] == "rec":
                        (ins if r["kind"] == "input" else outs).append(base64.b64decode(r["data_base64"]))
                    else:
                        for v in [r["exe"], r["comm"], r["path"], r["cwd"]] + list(r["argv"]):
                            search(v.encode(), hits, rel + " (exec field)", info)
                            checked["audit_arguments"] += 1
                    forbidden = set(r) & {"eventId", "session_id", "run_id", "boot_id", "instance_id", "audit_session",
                                          "ses", "auid", "uid", "logGroup", "logStreamName", "sequence", "serial"}
                    if forbidden:
                        hits.append(dict(pattern="id_left_in_window_record", count=1, where=rel, sample=",".join(sorted(forbidden))))
                search(b"".join(ins), hits, rel + " (input stream)", info, bare_uid=True)
                search(b"".join(outs), hits, rel + " (output stream)", info, bare_uid=True)
            else:
                search(open(path, "rb").read(), hits, rel, info)
                checked["table_files"] += 1
    total = sum(h["count"] for h in hits)
    rep = dict(step=STEP, code_version=C.CODE_VERSION, files_searched=files, checked=checked,
               patterns=[n for n, _ in K.LEAK_PATTERNS] + ["user_number_bare (recorder text)", "user_number_field (audit)",
                                                           "id_left_in_window_record"],
               hits=hits, total_hits=total, result="PASS" if total == 0 else "FAIL",
               reported_only=info,
               note="reported_only counts are outside sections 6.2-6.5: AHIR_CHECK is the setup check's own "
                    "sentinel, which a login used may show when it prints the shell history.")
    IO.write_json(IO.out("reports", "07_leak_audit_report.json"), rep)
    print("files", files, checked)
    print("reported only:", info)
    for h in hits[:40]:
        print("HIT", h)
    print("COMPLETE: leak audit", rep["result"], "total hits", total)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
