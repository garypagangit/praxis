"""Step 3: cleaning the classifier input, first part (design sections 6.1-6.5).

For every login used:
  6.1  Enter key: CRLF and LF become CR in recorder input
  6.3  harness wrapper: wrapped inputs are unwrapped (both forms, A11), the
       readiness probe is dropped, the wrapper's echo and marker lines are
       removed from the output, wrapper text shown as program output is
       unwrapped (A6), and the wrapper's own processes are dropped from audit
  6.2  identity patterns on recorder text, recorder fields and audit fields
  6.5  scratch directory names; collection and acceptance tooling dropped from audit
  6.4  every validator-family audit record group is dropped; each successful
       exec of the validator client that is not a wrapper process leaves a marker

The validator commands themselves are removed in step 4, which needs the
command list. Output of this step goes to scratch (it still holds validator
text); counts and ledgers go to reports/.
"""
import base64
import bisect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_audit as A
import s3_clean as K
import s3_commands as M
import s3_config as C
import s3_io as IO
import s3_term as T
import step02_route as R

STEP = "03_clean"
HEX_KEYS = ("proctitle", "name", "cwd", "exe", "comm", "cmd")


def load_recorder(sess):
    """login id -> list of [outer record, message] in sequence order."""
    logins = {}
    for line in open(IO.work(sess, "ci_recorder.jsonl"), "rb"):
        outer = json.loads(line)
        msg = json.loads(outer["message"])
        logins.setdefault(msg["session_id"], []).append([outer, msg])
    for v in logins.values():
        v.sort(key=lambda x: x[1]["sequence"])
    return logins


def load_audit(sess, bind):
    """login id -> ordered list of parsed exec groups bound to it."""
    msgs = []
    for i, line in enumerate(open(IO.work(sess, "ci_audit.jsonl"), "rb")):
        outer = json.loads(line)
        msgs.append((i, outer, outer["message"]))
    groups, bad = A.build_groups((i, o, m) for i, o, m in msgs)
    if bad:
        raise SystemExit("%s: unparsable audit record in classifier input" % sess)
    by_login = {}
    for g in groups:
        g.parse()
        login = bind.get((g.auid(), g.ses()))
        if login is None or not g.is_exec():
            raise SystemExit("%s: audit group %s is not an exec group of a login used" % (sess, g.gid))
        by_login.setdefault(login, []).append(g)
    for v in by_login.values():
        v.sort(key=lambda g: (g.time, int(g.serial)))
    return by_login


def scrub_audit_message(msg, counts):
    """Identity and scratch-directory rules on one audit message."""
    b = msg.encode("utf-8")
    b2, n = K.RE_UID_FIELD.subn(lambda m: m.group(1) + b"=" + K.UIDNUM, b)
    if n:
        counts["user_number_field"] = counts.get("user_number_field", 0) + n
    b2 = K.scrub_identity_bytes(b2, counts)
    for rx, rep in K.RE_SCRATCH:
        b2, n = rx.subn(rep, b2)
        if n:
            counts["scratch_dir"] = counts.get("scratch_dir", 0) + n
    s = b2.decode("utf-8")
    # hex-encoded values, one by one
    h = A.RE_HEAD.match(s)
    if h is None:
        return s

    def fix(m):
        key, val = m.group(1), m.group(2)
        base = key.split("[")[0]
        if not (A.RE_ARG.match(base) or base in HEX_KEYS):
            return m.group(0)
        if not val or val[0] == '"' or not A.RE_HEX.match(val) or len(val) % 2:
            return m.group(0)
        raw = bytes.fromhex(val)
        c2 = {}
        new = K.scrub_identity_bytes(raw, c2)
        for rx, rep in K.RE_SCRATCH:
            new, n = rx.subn(rep, new)
            if n:
                c2["scratch_dir"] = c2.get("scratch_dir", 0) + n
        if new == raw:
            return m.group(0)
        for k, v in c2.items():
            counts[k + "_hex"] = counts.get(k + "_hex", 0) + v
        return "%s=%s" % (key, new.hex().upper())

    body = s[h.end():]
    return s[:h.end()] + A.RE_KV.sub(fix, body)


def echo_line_count(inner):
    """Lines the shell reads before it runs the text: up to the first point
    where the text is complete by shell syntax (the same count step 4 uses)."""
    lines = inner.decode("utf-8", "replace").split("\r")
    for k in range(1, len(lines) + 1):
        if not M.shell_incomplete("\n".join(lines[:k])):
            return k
    return len(lines)


def clean_login(sess, login, recs, groups):
    st = {}             # counts for the step report
    led = []            # ledger rows
    idx_in = [i for i, (o, m) in enumerate(recs) if m["kind"] == "input"]
    idx_out = [i for i, (o, m) in enumerate(recs) if m["kind"] == "output"]
    seg_in = K.SegStream([base64.b64decode(recs[i][1]["data_base64"]) for i in idx_in])
    seg_out = K.SegStream([base64.b64decode(recs[i][1]["data_base64"]) for i in idx_out])
    st["records"] = len(recs)
    st["input_records"] = len(idx_in)
    st["output_records"] = len(idx_out)
    st["input_bytes_before"] = len(seg_in.data)
    st["output_bytes_before"] = len(seg_out.data)

    def out_pos_at_input(k):
        """Offset in the output stream when the k-th input record arrived."""
        j = bisect.bisect_left(idx_out, idx_in[k])       # output records before it
        return seg_out.start_of(j) if j < len(idx_out) else len(seg_out.data)

    # ---- 6.1 Enter
    st["enter_crlf_to_cr"] = len([1 for m in K.RE_ENTER.finditer(seg_in.data) if m.group(0) == b"\r\n"])
    st["enter_lf_to_cr"] = len([1 for m in K.RE_ENTER.finditer(seg_in.data) if m.group(0) == b"\n"])
    st["enter_cr_already"] = seg_in.data.count(b"\r") - st["enter_crlf_to_cr"]
    seg_in.sub(K.RE_ENTER, b"\r")

    # ---- 6.3 wrapper, input
    wrapped = []
    spans = []
    for m in K.RE_WRAP_INPUT.finditer(seg_in.data):
        inner, ok = K.shell_unquote(m.group(3))
        k = bisect.bisect_right(seg_in.ends, m.start())
        w = dict(id=m.group(1).decode(), k=k, inner=inner, probe=(inner == K.PROBE_INNER),
                 timeout=bool(m.group(2)), unquoted=ok, raw_len=m.end() - m.start())
        wrapped.append(w)
        spans.append((m.start(), m.end(), b"" if w["probe"] else inner + b"\r"))
    # positions in the output stream are taken before the input stream changes shape
    for w in wrapped:
        w["out_pos"] = out_pos_at_input(w["k"])
    seg_in.replace_spans(spans)
    st["wrapped_inputs"] = len(wrapped)
    st["wrapped_with_timeout"] = sum(1 for w in wrapped if w["timeout"] and not w["probe"])
    st["wrapped_without_timeout"] = sum(1 for w in wrapped if not w["timeout"] and not w["probe"])
    st["readiness_probes"] = sum(1 for w in wrapped if w["probe"])
    st["wrapped_not_unquoted"] = sum(1 for w in wrapped if not w["unquoted"])
    st["wrapper_text_left_in_input"] = len(K.RE_MARK_ANY.findall(seg_in.data))

    # ---- 6.3 wrapper, output: echo and BEGIN line of each wrapped input
    spans = []
    last_end = 0
    st["wrapped_begin_not_found"] = 0
    st["wrapped_echo_not_removed"] = 0
    for w in wrapped:
        rx = K.re.compile(rb"(?:\r?\n)?AO_" + w["id"].encode() + rb"_BEGIN\r?\n")
        m = rx.search(seg_out.data, max(w["out_pos"], last_end))
        if m is None:
            st["wrapped_begin_not_found"] += 1
            continue
        a = max(w["out_pos"], last_end)
        n_lines = 0 if w["probe"] else echo_line_count(w["inner"])
        if m.start() - a > 4 * w["raw_len"] + 400:
            st["wrapped_echo_not_removed"] += 1          # too much text to be an echo
            a = m.start()
        spans.append((a, m.end(), b"\r\n" * n_lines))
        last_end = m.end()
    seg_out.replace_spans(spans)

    # ---- A15 cross-check 1: is every END line followed directly by the prompt?
    prompt_begin = {a for a, b in T.prompt_spans(seg_out.data)}
    ends = list(K.RE_MARK_END.finditer(seg_out.data))
    st["end_lines"] = len(ends)
    st["end_lines_followed_by_prompt"] = sum(1 for m in ends if m.end() in prompt_begin)
    end_ids = {m.group(1).decode() for m in ends}
    st["wrapped_without_end_line"] = sum(1 for w in wrapped if w["id"] not in end_ids)
    seg_out.sub(K.RE_MARK_END, b"")

    # ---- A6: wrapper text shown as program output
    def unwrap_text(m):
        inner, ok = K.shell_unquote(m.group(3))
        return inner.replace(b"\r", b"\r\n") if b"\r\n" not in inner else inner
    st["wrapper_text_in_output_unwrapped"] = seg_out.sub(K.RE_WRAP_TEXT, unwrap_text)
    st["scroll_fragments_removed"] = seg_out.sub(K.RE_SCROLL_FRAGMENT, b"")
    st["wrapper_pieces_removed"] = (seg_out.sub(K.RE_WRAP_HEAD_PIECE, b"") + seg_out.sub(K.RE_WRAP_TAIL_PIECE, b"")
                                    + seg_out.sub(K.RE_MARK_BEGIN, b"") + seg_out.sub(K.RE_WRAP_TAIL_CUT, b"")
                                    + seg_out.sub(K.RE_WRAP_HEAD_CUT, b"") + seg_out.sub(K.RE_WRAP_TIMEOUT_PIECE, b"")
                                    + seg_out.sub(K.RE_MARK_ANY, b""))
    st["probe_text_removed"] = seg_out.sub(K.RE_PROBE_TEXT, b"")

    # the output as it was shown, before identity changes text lengths: step 4 replays
    # this copy on its screen and scrubs the command text it reads (scratch only)
    pre_out = seg_out.chunks()

    # ---- 6.2 identity, 6.5 scratch directories
    idc = {}
    K.scrub_identity_stream(seg_in, idc)
    K.scrub_identity_stream(seg_out, idc)
    for rx, rep in K.RE_SCRATCH:
        n = seg_in.sub(rx, rep) + seg_out.sub(rx, rep)
        if n:
            idc["scratch_dir"] = idc.get("scratch_dir", 0) + n
    for rx, rep in K.TOOLING_TEXT_RULES:
        n = seg_in.sub(rx, rep) + seg_out.sub(rx, rep)
        if n:
            idc["tooling_name"] = idc.get("tooling_name", 0) + n
    st["identity_recorder_text"] = idc
    st["matches_split_between_records"] = seg_in.split_matches + seg_out.split_matches

    # ---- rebuild recorder records
    new_in = seg_in.chunks()
    new_out = seg_out.chunks()
    data_of = {}
    for k, i in enumerate(idx_in):
        data_of[i] = new_in[k]
    for k, i in enumerate(idx_out):
        data_of[i] = new_out[k]
    pre_of = {}
    for k, i in enumerate(idx_out):
        if pre_out[k] != new_out[k]:
            pre_of[i] = pre_out[k]
    probe_recs = {idx_in[w["k"]] for w in wrapped if w["probe"]}
    out_recs = []
    fields = {"engineer_id": 0, "linux_user": 0, "uid": 0, "audit_uid": 0, "connection": 0}
    st["records_emptied_dropped"] = 0
    for i, (outer, msg) in enumerate(recs):
        if i in data_of:
            old = base64.b64decode(msg["data_base64"])
            new = data_of[i]
            if not new and old:
                if i in probe_recs:
                    led.append((outer["eventId"], STEP, "readiness_probe", ""))
                    st["records_emptied_dropped"] += 1
                    continue
                if msg["kind"] == "output":
                    # an output record that held nothing but wrapper echo or marker lines
                    led.append((outer["eventId"], STEP, "wrapper_echo_or_marker_only", ""))
                    st["records_emptied_dropped"] += 1
                    continue
            msg["data_base64"] = base64.b64encode(new).decode()
        for key in ("engineer_id", "linux_user"):
            if key in msg:
                msg[key] = K.USER.decode()
                fields[key] += 1
        for key in ("uid", "audit_uid"):
            if key in msg and msg[key] is not None:
                msg[key] = int(K.UIDNUM)
                fields[key] += 1
        if "connection" in msg:
            del msg["connection"]
            fields["connection"] += 1
        outer["message"] = IO.dumps(msg)
        if i in pre_of:
            outer["_shown"] = base64.b64encode(pre_of[i]).decode()
        out_recs.append(outer)
    st["identity_recorder_fields"] = fields
    st["input_bytes_after"] = len(seg_in.data)
    st["output_bytes_after"] = len(seg_out.data)

    # ---- audit
    inner_set = {w["inner"].replace(b"\r", b"\n").decode("utf-8", "replace") for w in wrapped}
    shell_pid = None
    for g in groups:
        if g.success() and g.argv and g.argv[0] == "-bash":
            shell_pid = g.pid()
            break
    timeout_pids = set()
    wrapper_bash_pids = set()
    cls = {}
    for g in groups:                                   # W1: the wrapper's timeout
        av = g.argv or []
        if (g.success() and len(av) == 7 and av[0] == "timeout" and av[1] == "--signal=TERM"
                and K.RE_WRAPPER_TIMEOUT_ARGS[0].match(av[2]) and K.RE_WRAPPER_TIMEOUT_ARGS[1].match(av[3])
                and av[4] == "bash" and av[5] == "-c"):
            cls[g.gid] = "wrapper_timeout"
            timeout_pids.add(g.pid())
    for g in groups:
        if g.gid in cls:
            continue
        av = g.argv or []
        if g.ppid() in timeout_pids and g.exe().endswith("/timeout") and not g.success():
            cls[g.gid] = "wrapper_path_lookup"         # W2: timeout looking for bash
        elif g.success() and len(av) == 3 and av[0] == "bash" and av[1] == "-c" and (
                g.ppid() in timeout_pids or av[2] in inner_set):
            cls[g.gid] = "wrapper_bash"                # W3, W4
            wrapper_bash_pids.add(g.pid())
    markers = []
    review = []
    for g in groups:
        if g.gid in cls:
            continue
        txt = g.text()
        if K.has_family_needle(txt):
            cls[g.gid] = "validator_family"
            if g.success():
                ep = g.exec_path()
                base = ep.rsplit("/", 1)[-1]
                av = g.argv or []
                is_client = bool(K.RE_VALIDATOR_PROGRAM.match(base))
                if not is_client and K.RE_INTERPRETER.match(base):
                    for a in av[1:]:
                        if a.startswith("-"):
                            if a in ("-c", "-m"):
                                break
                            continue
                        is_client = bool(K.RE_FAMILY_SCRIPT.match(a))
                        break
                if is_client:
                    markers.append(g.time)
                review.append(dict(time=g.time, exec_path=ep, argv=av[:6], marker=is_client))
        elif any(n in t for t in txt for n in K.TOOLING_NEEDLES):
            cls[g.gid] = "collection_tooling"
    aud_counts = {}
    aud_recs = []
    idc2 = {}
    for g in groups:
        c = cls.get(g.gid)
        if c is not None:
            aud_counts[c + "_groups"] = aud_counts.get(c + "_groups", 0) + 1
            aud_counts[c + "_records"] = aud_counts.get(c + "_records", 0) + len(g.records)
            for _, outer, _ in g.records:
                led.append((outer["eventId"], STEP, "audit_" + c, ""))
            continue
        aud_counts["kept_groups"] = aud_counts.get("kept_groups", 0) + 1
        aud_counts["kept_records"] = aud_counts.get("kept_records", 0) + len(g.records)
        if g.success():
            aud_counts["kept_successful_execs"] = aud_counts.get("kept_successful_execs", 0) + 1
        for _, outer, msg in g.records:
            outer["message"] = scrub_audit_message(msg, idc2)
            aud_recs.append(outer)
    st["audit"] = aud_counts
    st["audit_groups_in"] = len(groups)
    st["audit_records_in"] = sum(len(g.records) for g in groups)
    st["identity_audit"] = idc2
    st["validator_markers"] = len(markers)
    st["login_shell_found"] = shell_pid is not None
    st["wrapper_bash_not_under_timeout_or_shell"] = sum(
        1 for g in groups if cls.get(g.gid) == "wrapper_bash" and g.ppid() not in timeout_pids and g.ppid() != shell_pid)
    meta = dict(login=login, markers=markers, shell_pid=shell_pid, stats=st)
    return out_recs, aud_recs, meta, led, review


def run_session(sess):
    op = IO.read_json(IO.work(sess, "operator.json"))
    if op is None:
        raise SystemExit("%s: run step 2 first" % sess)
    if IO.sha256_file(IO.work(sess, "ci_recorder.jsonl"))[0] != op["ci_recorder_sha256"] or \
            IO.sha256_file(IO.work(sess, "ci_audit.jsonl"))[0] != op["ci_audit_sha256"]:
        raise SystemExit("%s: classifier-input scratch files do not match step 2's hashes" % sess)
    sb, stg, _, _ = IO.read_boundaries(sess)
    table = [r for r in IO.login_table(sess, sb) if r["included"]]
    recs = load_recorder(sess)
    bind = {}
    for r in table:
        m = recs[r["login_id"]][0][1]
        uid = m["audit_uid"] if m.get("audit_uid") is not None else m["uid"]
        bind[(str(uid), str(m["audit_session"]))] = r["login_id"]
    groups = load_audit(sess, bind)
    R.ledger_reset(sess, STEP)
    res = dict(session=sess, logins={}, review={})
    for r in table:
        login = r["login_id"]
        out_recs, aud_recs, meta, led, review = clean_login(sess, login, recs[login], groups.get(login, []))
        with open(IO.work(sess, "a_%s.rec.jsonl" % login), "w", encoding="utf-8") as f:
            for o in out_recs:
                f.write(IO.dumps(o) + "\n")
        with open(IO.work(sess, "a_%s.aud.jsonl" % login), "w", encoding="utf-8") as f:
            for o in aud_recs:
                f.write(IO.dumps(o) + "\n")
        meta["rec_sha256"] = IO.sha256_file(IO.work(sess, "a_%s.rec.jsonl" % login))[0]
        meta["aud_sha256"] = IO.sha256_file(IO.work(sess, "a_%s.aud.jsonl" % login))[0]
        IO.write_json(IO.work(sess, "a_%s.meta.json" % login), meta)
        R.ledger_append(sess, led)
        st = meta["stats"]
        st["recorder_records_out"] = len(out_recs)
        st["audit_records_out"] = len(aud_recs)
        st["ledger_rows"] = len(led)
        assert st["records"] == len(out_recs) + st["records_emptied_dropped"]
        assert st["audit_records_in"] == len(aud_recs) + sum(
            v for k, v in st["audit"].items() if k.endswith("_records") and not k.startswith("kept"))
        res["logins"][login] = dict(stats=st, rec_sha256=meta["rec_sha256"], aud_sha256=meta["aud_sha256"])
        res["review"][login] = review
    IO.write_json(IO.work(sess, "clean_a.json"), res)
    return res


def main():
    rep = dict(step=STEP, code_version=C.CODE_VERSION, sessions={})
    review = {}
    for sess in C.SESSION_ORDER:
        res = run_session(sess)
        op = IO.read_json(IO.work(sess, "operator.json"))
        rep["sessions"][sess] = dict(
            input_sha256=dict(recorder=op["ci_recorder_sha256"], audit=op["ci_audit_sha256"]),
            logins={k: v for k, v in res["logins"].items()})
        review[sess] = res["review"]
        tot = {}
        for l, v in res["logins"].items():
            s = v["stats"]
            for k in ("wrapped_inputs", "readiness_probes", "wrapped_with_timeout", "wrapped_without_timeout",
                      "end_lines", "end_lines_followed_by_prompt", "wrapped_without_end_line",
                      "wrapped_begin_not_found", "wrapped_echo_not_removed", "validator_markers",
                      "records_emptied_dropped", "matches_split_between_records", "enter_lf_to_cr",
                      "enter_crlf_to_cr", "enter_cr_already", "wrapper_text_in_output_unwrapped",
                      "scroll_fragments_removed", "wrapper_pieces_removed"):
                tot[k] = tot.get(k, 0) + s[k]
            for k, n in s["audit"].items():
                tot["audit_" + k] = tot.get("audit_" + k, 0) + n
        print(sess, json.dumps(tot))
    IO.write_json(IO.out("reports", "03_clean_report.json"), rep)
    # successful execs of the validator family, for the review the design asks for (6.4)
    IO.write_json(IO.out("reports", "03_validator_family_execs_for_review.json"), review)
    print("COMPLETE: clean (first part)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
