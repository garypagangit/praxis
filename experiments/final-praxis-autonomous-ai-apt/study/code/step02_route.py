"""Step 2: where every record goes (design section 4).

Every record of a package ends in exactly one of three places:
  classifier input   operator machine: terminal recorder records of the logins
                     used, and the audit exec record groups bound to those logins
                     (same user number and audit session number)
  set aside          everything else, stored as collected, split by machine and
                     stream, unscrubbed, never an input to the classifier
  dropped, ledger    eng_feature_* audit record groups (Original Austin range, A2)

Sub-steps (each runs in slices; repeat a command until it prints COMPLETE):
  scan       one fast pass per package: stream inventory, and the operator
             recorder and audit records copied to scratch
  operator   decide the destination of every operator recorder and audit record
  setaside   write every other record to set_aside/<session>/<machine>/<stream>.jsonl.gz
  report     counts must add up to the package total; reports/02_route_report.json
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_config as C
import s3_io as IO

P_STREAM = b'{"logStreamName":"'
P_GROUP = b'","logGroup":"'
BLOCK = 200000          # records per set-aside block (one gzip member per file per block)

RE_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
RE_INSTANCE = re.compile(r"^i-[0-9a-f]+/(.+)$")
RE_SSM = re.compile(r"^[0-9a-f-]{36}/i-[0-9a-f]+/(aws-run\w+)/(\w+)$")
RE_ENI = re.compile(r"^eni-[0-9a-f]+-(\w+)$")
RE_LAMBDA = re.compile(r"^\d{4}/\d{2}/\d{2}/\[\$LATEST\][0-9a-f]+$")


def group_stream(line):
    """(logGroup, logStreamName) of one raw line, without parsing the message."""
    if line.startswith(P_STREAM) and line.endswith(b'"}\n'):
        j = line.find(b'"', len(P_STREAM))
        i = line.rfind(P_GROUP)
        if j > 0 and i > j:
            return line[i + len(P_GROUP):-3].decode(), line[len(P_STREAM):j].decode()
    r = json.loads(line)
    return r["logGroup"], r["logStreamName"]


def machine_of(group):
    if group.startswith("/aws/lambda/"):
        return "validator-service"
    m = re.match(r"^/eng-[0-9a-z-]+/([A-Za-z0-9_-]+)$", group)
    if m:
        return m.group(1)
    return RE_SAFE.sub("_", group.strip("/"))


def leaf_of(stream):
    m = RE_INSTANCE.match(stream)
    if m:
        return RE_SAFE.sub("_", m.group(1))
    m = RE_SSM.match(stream)
    if m:
        return "ssm-%s-%s" % (m.group(1), m.group(2))
    m = RE_ENI.match(stream)
    if m:
        return "eni-" + m.group(1)
    if RE_LAMBDA.match(stream):
        return "lambda"
    return RE_SAFE.sub("_", stream)


def is_operator_core(machine, leaf):
    return machine == "operator" and leaf in (C.RECORDER_STREAM, C.AUDIT_STREAM)


# ------------------------------------------------------------------ scan
def scan_session(sess):
    pk = IO.package(sess)
    inv = {}
    per_stream = {}
    rec_path = IO.work(sess, "op_recorder.jsonl")
    aud_path = IO.work(sess, "op_audit.jsonl")
    n_total = 0
    with open(rec_path + ".tmp", "wb") as fr, open(aud_path + ".tmp", "wb") as fa:
        for label, paths, member in pk["raw"]:
            n = 0
            for ln, line in IO.iter_raw_lines(paths, member):
                g, s = group_stream(line)
                mach, leaf = machine_of(g), leaf_of(s)
                k = mach + "|" + leaf
                inv[k] = inv.get(k, 0) + 1
                if mach == "operator":
                    if leaf == C.RECORDER_STREAM:
                        fr.write(line)
                    elif leaf == C.AUDIT_STREAM:
                        fa.write(line)
                n += 1
            per_stream[label] = n
            n_total += n
    os.replace(rec_path + ".tmp", rec_path)
    os.replace(aud_path + ".tmp", aud_path)
    res = dict(session=sess, records=n_total, per_raw_stream=per_stream, inventory=inv,
               op_recorder_sha256=IO.sha256_file(rec_path)[0], op_audit_sha256=IO.sha256_file(aud_path)[0])
    IO.write_json(IO.work(sess, "scan.json"), res)
    return sess, n_total


def cmd_scan():
    budget = IO.Budget()
    todo = [s for s in C.SESSION_ORDER if not os.path.exists(IO.work(s, "scan.json"))]
    todo.sort(key=lambda s: -C.EXPECTED_RAW[s])
    with cf.ProcessPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(scan_session, s): s for s in todo}
        for fu in cf.as_completed(futs):
            s, n = fu.result()
            if n != C.EXPECTED_RAW[s]:
                raise SystemExit("%s: %d records read, %d expected" % (s, n, C.EXPECTED_RAW[s]))
            print("scanned", s, n, "records; %.0f s left" % budget.left())
    print("COMPLETE: scan")
    return 0



# ------------------------------------------------------------------ operator
def ledger_path(sess):
    return IO.out("reports", "ledgers", "%s_dropped.csv" % sess)


def ledger_reset(sess, step):
    """Start (or restart) the ledger rows of one step for one session."""
    path = ledger_path(sess)
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rows = [l for l in f.read().splitlines()[1:] if l and l.split(",")[1] != step]
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write("event_id,step,rule,detail\n")
        for l in rows:
            f.write(l + "\n")
    os.replace(path + ".tmp", path)


def ledger_append(sess, rows):
    """rows: (event id, step, rule, detail)."""
    with open(ledger_path(sess), "a", encoding="utf-8") as f:
        for eid, step, rule, detail in rows:
            f.write("%s,%s,%s,%s\n" % (eid, step, rule, str(detail).replace(",", ";")))


def operator_session(sess):
    import s3_audit as A
    sb, st, _, _ = IO.read_boundaries(sess)
    logins = IO.login_table(sess, sb)
    inc_ids = {r["login_id"] for r in logins if r["included"]}
    counts = dict(recorder_classifier_input=0, recorder_left_out_logins=0,
                  audit_classifier_input=0, audit_groups_classifier_input=0,
                  audit_set_aside=0, audit_eng_feature_dropped=0, audit_eng_feature_groups=0,
                  audit_unparsed_set_aside=0)
    per_login = {}
    sa_dir = IO.ensure_dir(os.path.join(C.out_root(), "set_aside", sess, "operator"))
    # ---- recorder
    gz, raw = IO.gz_text_writer(os.path.join(sa_dir, C.RECORDER_STREAM + ".logins-left-out.jsonl.gz"))
    seen_logins = {}
    with open(IO.work(sess, "ci_recorder.jsonl"), "wb") as ci:
        for line in open(IO.work(sess, "op_recorder.jsonl"), "rb"):
            msg = json.loads(json.loads(line)["message"])
            sid = msg["session_id"]
            seen_logins.setdefault(sid, dict(uid=msg.get("uid"), audit_uid=msg.get("audit_uid"),
                                             audit_session=msg.get("audit_session")))
            if sid in inc_ids:
                ci.write(line)
                counts["recorder_classifier_input"] += 1
                per_login.setdefault(sid, dict(recorder=0, audit_records=0, audit_groups=0))["recorder"] += 1
            else:
                gz.write(line)
                counts["recorder_left_out_logins"] += 1
    gz.close()
    raw.close()
    unknown = set(seen_logins) - {r["login_id"] for r in logins}
    if unknown:
        raise SystemExit("%s: recorder holds logins that SESSION_BOUNDARIES does not list: %s" % (sess, sorted(unknown)))
    # binding: user number and audit session number of each login used, from its own recorder records
    bind = {}
    for sid in inc_ids:
        if sid not in seen_logins:
            raise SystemExit("%s: login %s has no recorder records" % (sess, sid))
        m = seen_logins[sid]
        uid = m["audit_uid"] if m["audit_uid"] is not None else m["uid"]
        bind[(str(uid), str(m["audit_session"]))] = sid
    # ---- audit, pass 1: destination of every group from its SYSCALL record
    cls = {}
    for line in open(IO.work(sess, "op_audit.jsonl"), "rb"):
        msg = json.loads(line)["message"]
        h = A.head(msg)
        if h is None or h[0] != "SYSCALL":
            continue
        f = dict(A.fields(msg))
        gid = h[1] + ":" + h[2]
        key = f.get("key", "").strip('"')
        if key.startswith(C.ENG_FEATURE_KEY_PREFIX):
            cls[gid] = ("eng", key)
        elif f.get("syscall") == "59" and (f.get("auid"), f.get("ses")) in bind:
            cls[gid] = ("bound", bind[(f.get("auid"), f.get("ses"))])
    # ---- audit, pass 2
    ledger_reset(sess, "02_route")
    led = []
    gz, raw = IO.gz_text_writer(os.path.join(sa_dir, C.AUDIT_STREAM + ".not-classifier-input.jsonl.gz"))
    seen_groups = set()
    with open(IO.work(sess, "ci_audit.jsonl"), "wb") as ci:
        for line in open(IO.work(sess, "op_audit.jsonl"), "rb"):
            rec = json.loads(line)
            h = A.head(rec["message"])
            if h is None:
                gz.write(line)
                counts["audit_unparsed_set_aside"] += 1
                continue
            gid = h[1] + ":" + h[2]
            d = cls.get(gid)
            if d is None:
                gz.write(line)
                counts["audit_set_aside"] += 1
            elif d[0] == "eng":
                led.append((rec["eventId"], "02_route", "eng_feature_audit_group", d[1]))
                counts["audit_eng_feature_dropped"] += 1
                if gid not in seen_groups:
                    seen_groups.add(gid)
                    counts["audit_eng_feature_groups"] += 1
            else:
                ci.write(line)
                counts["audit_classifier_input"] += 1
                pl = per_login.setdefault(d[1], dict(recorder=0, audit_records=0, audit_groups=0))
                pl["audit_records"] += 1
                if gid not in seen_groups:
                    seen_groups.add(gid)
                    counts["audit_groups_classifier_input"] += 1
                    pl["audit_groups"] += 1
    gz.close()
    raw.close()
    ledger_append(sess, led)
    scan = IO.read_json(IO.work(sess, "scan.json"))
    inv = scan["inventory"]
    n_rec = inv.get("operator|" + C.RECORDER_STREAM, 0)
    n_aud = inv.get("operator|" + C.AUDIT_STREAM, 0)
    assert n_rec == counts["recorder_classifier_input"] + counts["recorder_left_out_logins"]
    assert n_aud == (counts["audit_classifier_input"] + counts["audit_set_aside"]
                     + counts["audit_eng_feature_dropped"] + counts["audit_unparsed_set_aside"])
    res = dict(session=sess, counts=counts, per_login=per_login,
               ci_recorder_sha256=IO.sha256_file(IO.work(sess, "ci_recorder.jsonl"))[0],
               ci_audit_sha256=IO.sha256_file(IO.work(sess, "ci_audit.jsonl"))[0])
    IO.write_json(IO.work(sess, "operator.json"), res)
    return sess, counts


def cmd_operator():
    for s in C.SESSION_ORDER:
        if not os.path.exists(IO.work(s, "scan.json")):
            raise SystemExit("run scan first")
    with cf.ProcessPoolExecutor(max_workers=4) as ex:
        for sess, counts in ex.map(operator_session, C.SESSION_ORDER):
            print(sess, counts)
    print("COMPLETE: operator")
    return 0


# ------------------------------------------------------------------ set aside
def setaside_session(args):
    sess, seconds = args
    budget = IO.Budget(seconds)
    pk = IO.package(sess)
    rename = C.SESSIONS[sess]["lab_range"] == C.ORIGINAL_AUSTIN
    state_path = IO.work(sess, "setaside_state.json")
    state = IO.read_json(state_path)
    root = os.path.join(C.out_root(), "set_aside", sess)
    if state is None:
        state = dict(stream=0, line=0, files={}, counts={}, renamed=0, done=False)
    if state["done"]:
        return sess, True, sum(state["counts"].values())
    # bring every file back to the size recorded at the last completed block
    for rel, size in state["files"].items():
        with open(os.path.join(root, rel), "r+b") as f:
            f.truncate(size)
    writers = {}

    def writer(mach, leaf):
        rel = os.path.join(mach, leaf + ".jsonl.gz")
        w = writers.get(rel)
        if w is None:
            path = os.path.join(root, rel)
            IO.ensure_dir(os.path.dirname(path))
            if rel not in state["files"]:
                open(path, "wb").close()             # new file, or one left by an unfinished run
            w = writers[rel] = IO.GzAppend(path)
        return rel, w

    def checkpoint(si, ln, done=False):
        for rel, w in writers.items():
            w.end_block()
            state["files"][rel] = w.size()
        state["stream"], state["line"], state["done"] = si, ln, done
        IO.write_json(state_path, state)

    counts = state["counts"]
    si = state["stream"]
    while si < len(pk["raw"]):
        label, paths, member = pk["raw"][si]
        start = state["line"] if si == state["stream"] else 0
        n_in_block = 0
        last = start
        stopped = False
        for ln, line in IO.iter_raw_lines(paths, member, start):
            g, s = group_stream(line)
            mach, leaf = machine_of(g), leaf_of(s)
            if not is_operator_core(mach, leaf):
                if rename and mach == "operator" and leaf in C.OPERATOR_STREAM_RENAME:
                    new = C.OPERATOR_STREAM_RENAME[leaf]
                    j = line.find(b'"', len(P_STREAM))
                    name = line[len(P_STREAM):j]
                    line = P_STREAM + name[:len(name) - len(leaf)] + new.encode() + line[j:]
                    leaf = new
                    state["renamed"] += 1
                rel, w = writer(mach, leaf)
                w.write(line)
                counts[rel] = counts.get(rel, 0) + 1
            n_in_block += 1
            last = ln + 1
            if n_in_block >= BLOCK:
                checkpoint(si, last)
                n_in_block = 0
                if not budget.ok():
                    stopped = True
                    break
        if stopped:
            for w in writers.values():
                w.close()
            return sess, False, sum(counts.values())
        si += 1
        checkpoint(si, 0)
    checkpoint(si, 0, done=True)
    for w in writers.values():
        w.close()
    return sess, True, sum(counts.values())


def cmd_setaside():
    budget = IO.Budget()
    todo = []
    for s in C.SESSION_ORDER:
        st = IO.read_json(IO.work(s, "setaside_state.json"))
        if not (st and st["done"]):
            todo.append(s)
    todo.sort(key=lambda s: -C.EXPECTED_RAW[s])
    all_done = True
    with cf.ProcessPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(setaside_session, (s, budget.left() - 8)) for s in todo]
        for fu in futs:
            sess, done, n = fu.result()
            print(sess, "done" if done else "in progress", n, "records set aside so far")
            all_done = all_done and done
    print("COMPLETE: setaside" if all_done else "INCOMPLETE: setaside; run again")
    return 0 if all_done else 2


# ------------------------------------------------------------------ report
def cmd_report():
    ver = IO.read_json(IO.out("reports", "01_verification_report.json"))
    if not ver or ver.get("result") != "PASS":
        raise SystemExit("verification report missing or not PASS")
    rep = dict(step="02_route", code_version=C.CODE_VERSION, sessions={},
               notes=["Set-aside files are gzip-compressed JSONL (the collected lines, unscrubbed), one file per machine and stream.",
                      "Operator streams 'authentication' and 'system' (Original Austin range) are renamed to 'auth' and 'syslog' in the file name and in logStreamName (D31, A2).",
                      "Operator recorder records of logins that are not used, and operator audit records that are not exec record groups bound to a login used, are kept with the set-aside files and are never cleaned or windowed.",
                      "Classifier-input records are passed to the cleaning step through scratch files; their hashes are recorded here and checked there."])
    ok = True
    for sess in C.SESSION_ORDER:
        scan = IO.read_json(IO.work(sess, "scan.json"))
        op = IO.read_json(IO.work(sess, "operator.json"))
        sa = IO.read_json(IO.work(sess, "setaside_state.json"))
        if not (scan and op and sa and sa["done"]):
            raise SystemExit("%s: route not complete" % sess)
        c = op["counts"]
        root = os.path.join(C.out_root(), "set_aside", sess)
        files = {}
        for rel in sorted(sa["files"]):
            sha, size = IO.sha256_file(os.path.join(root, rel))
            files[rel] = dict(records=sa["counts"].get(rel, 0), bytes=size, sha256=sha)
        for rel in ("operator/%s.logins-left-out.jsonl.gz" % C.RECORDER_STREAM,
                    "operator/%s.not-classifier-input.jsonl.gz" % C.AUDIT_STREAM):
            sha, size = IO.sha256_file(os.path.join(root, rel))
            files[rel] = dict(bytes=size, sha256=sha,
                              records=(c["recorder_left_out_logins"] if "logins-left-out" in rel
                                       else c["audit_set_aside"] + c["audit_unparsed_set_aside"]))
        set_aside = sum(f["records"] for f in files.values())
        classifier = c["recorder_classifier_input"] + c["audit_classifier_input"]
        dropped = c["audit_eng_feature_dropped"]
        total = set_aside + classifier + dropped
        inputs = ver["sessions"][sess]["raw_inputs"]
        match = (total == scan["records"] == C.EXPECTED_RAW[sess] == sum(i["records"] for i in inputs))
        ok = ok and match
        rep["sessions"][sess] = dict(
            inputs=inputs, package_records=scan["records"],
            classifier_input=dict(records=classifier, recorder=c["recorder_classifier_input"],
                                  audit_records=c["audit_classifier_input"],
                                  audit_exec_groups=c["audit_groups_classifier_input"],
                                  per_login=op["per_login"],
                                  scratch_sha256=dict(recorder=op["ci_recorder_sha256"], audit=op["ci_audit_sha256"])),
            set_aside=dict(records=set_aside, renamed_stream_records=sa["renamed"], files=files),
            dropped_with_ledger=dict(records=dropped, eng_feature_groups=c["audit_eng_feature_groups"],
                                     ledger="reports/ledgers/%s_dropped.csv" % sess),
            counts_add_up=match, stream_inventory=scan["inventory"])
    rep["result"] = "PASS" if ok else "FAIL"
    IO.write_json(IO.out("reports", "02_route_report.json"), rep)
    for sess in C.SESSION_ORDER:
        r = rep["sessions"][sess]
        print(sess, "package", r["package_records"], "= classifier", r["classifier_input"]["records"],
              "+ set aside", r["set_aside"]["records"], "+ dropped", r["dropped_with_ledger"]["records"],
              "OK" if r["counts_add_up"] else "MISMATCH")
    print("COMPLETE:", rep["result"])
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"scan": cmd_scan, "operator": cmd_operator, "setaside": cmd_setaside, "report": cmd_report}.get(cmd)
    if fn is None:
        raise SystemExit(__doc__)
    sys.exit(fn())
