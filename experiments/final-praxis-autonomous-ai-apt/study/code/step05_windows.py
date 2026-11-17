"""Step 5: windows, labels and description files (design sections 5 and 7).

  - 30 s (main) and 60 s (sensitivity) windows, non-overlapping, aligned to the
    login's recorder start
  - kept: at least one terminal input or output record and at least 15 s long
  - a window holding only the login's closing exit is dropped
  - a window with nothing left once validator commands and their output are
    removed is dropped (A4)
  - every time becomes seconds since the login's start; event, login, boot,
    instance and audit ids are dropped; process ids become per-window local
    numbers, the login shell always 1
  - stage: the first stage whose acceptance comes after the window starts, on
    one timeline per session, using the operator's own acceptances (A3, A13)

Labels live in sidecar files only. The class label is read from the study
design (s3_config), never from a record.
"""
import base64
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_audit as A
import s3_commands as M
import s3_config as C
import s3_io as IO

STEP = "05_windows"


def read_recorder(path):
    """[(kind, epoch time, data bytes, message dict)] in file order."""
    out = []
    for line in open(path, encoding="utf-8"):
        msg = json.loads(json.loads(line)["message"])
        out.append((msg["kind"], M.epoch(msg["time"]),
                    base64.b64decode(msg["data_base64"]) if "data_base64" in msg else b"", msg))
    return out


def stage_of(timeline, finished7, t):
    """timeline: sorted [(time, stage)] of the operator's acceptances."""
    for ta, stg in timeline:
        if ta > t:
            return stg
    if finished7:
        return 7
    return (timeline[-1][1] + 1) if timeline else 1


def stage_group(stage):
    return "1-4" if stage <= 4 else str(stage)


def raw_login_stats(sess):
    """Duration, inputs and Enter presses of every recorded login (used or not),
    from the recorder records as collected."""
    logins = {}
    for line in open(IO.work(sess, "op_recorder.jsonl"), "rb"):
        msg = json.loads(json.loads(line)["message"])
        logins.setdefault(msg["session_id"], []).append(msg)
    res = {}
    for sid, ms in logins.items():
        ms.sort(key=lambda m: m["sequence"])
        t0 = M.epoch(ms[0]["time"])
        t1 = M.epoch(ms[-1]["time"])
        inputs = [base64.b64decode(m["data_base64"]) for m in ms if m["kind"] == "input"]
        joined = b"".join(inputs)
        enters = joined.count(b"\r\n") + (joined.count(b"\r") - joined.count(b"\r\n")) + (joined.count(b"\n") - joined.count(b"\r\n"))
        end = [m for m in ms if m["kind"] == "end"]
        # how the login ended (description only, never a feature)
        tail = joined.replace(b"\r\n", b"\n").replace(b"\r", b"\n").rstrip(b"\n").split(b"\n")[-1].strip() if joined.strip() else b""
        last_rec = inputs[-1] if inputs else b""
        if not end:
            how = "no_end_record"
        elif end[0].get("reason") != "shell-exited":
            how = "closed_from_outside"
        elif tail in (b"exit", b"logout"):
            one_write = last_rec.replace(b"\r", b"\n").strip(b"\n").split(b"\n")[-1].strip() in (b"exit", b"logout") and len(last_rec.strip()) >= 4
            how = "exit_in_one_write" if one_write else "typed_exit"
        elif end[0].get("shell_exit_observed"):
            how = "shell_exited_without_exit_line"
        else:
            how = "ended_without_exit"
        res[sid] = dict(duration_s=round(t1 - t0, 3), inputs=len(inputs), enter_presses=enters, how_ended=how,
                        end_reason=end[0].get("reason") if end else None,
                        shell_exit_observed=end[0].get("shell_exit_observed") if end else None,
                        start_epoch=t0, records=len(ms))
    return res


def build_login(sess, r, order, elapsed_before, timeline, finished7, L, rep):
    """Windows of one login at one window length. Returns (rows, kept records by window)."""
    login = r["login_id"]
    sk, lk = IO.session_key(sess), IO.login_key(login)
    final = read_recorder(IO.out("data", "cleaned", sk, lk + ".recorder.jsonl"))
    phase_a = read_recorder(IO.work(sess, "a_%s.rec.jsonl" % login))
    raw = [m for m in (json.loads(json.loads(l)["message"]) for l in open(IO.work(sess, "ci_recorder.jsonl"), "rb"))
           if m["session_id"] == login]
    starts = [x for x in final if x[0] == "start"]
    if len(starts) != 1:
        raise SystemExit("%s %s: %d start records" % (sess, login, len(starts)))
    t0 = starts[0][1]
    ends = [x for x in final if x[0] == "end"]
    t_end = ends[0][1] if ends else max(x[1] for x in final)
    duration = t_end - t0
    n_win = max(1, int(math.ceil(duration / L - 1e-9)))

    def widx(t):
        k = int((t - t0) // L)
        return min(max(k, 0), n_win - 1)

    cnt_raw = [[0, 0] for _ in range(n_win)]
    for m in raw:
        if m["kind"] in ("input", "output"):
            cnt_raw[widx(M.epoch(m["time"]))][0 if m["kind"] == "input" else 1] += 1
    cnt_a = [[0, 0] for _ in range(n_win)]
    for kind, t, d, m in phase_a:
        if kind in ("input", "output"):
            cnt_a[widx(t)][0 if kind == "input" else 1] += 1
    # commands: closing exit
    cmds = [json.loads(l) for l in open(IO.out("data", "commands", sk, lk + ".commands.jsonl"), encoding="utf-8")]
    closing = cmds[-1] if cmds and cmds[-1]["closing_exit"] and cmds[-1]["is_exit"] else None
    cnt_f = [[0, 0] for _ in range(n_win)]
    exit_only = [True] * n_win
    recs_by_w = [[] for _ in range(n_win)]
    for i, (kind, t, d, m) in enumerate(final):
        if kind not in ("input", "output"):
            continue
        k = widx(t)
        cnt_f[k][0 if kind == "input" else 1] += 1
        belongs = closing is not None and (
            (kind == "input" and closing["in_first"] <= i <= closing["in_enter"]) or
            (kind == "output" and i > closing["in_first"]))
        if not belongs:
            exit_only[k] = False
        recs_by_w[k].append(dict(w=k, i=i, t=round(t - t0, 6), src="rec", kind=kind,
                                 data_base64=base64.b64encode(d).decode()))
    # audit exec events of this login
    msgs = []
    for n, line in enumerate(open(IO.out("data", "cleaned", sk, lk + ".audit.jsonl"), encoding="utf-8")):
        o = json.loads(line)
        msgs.append((n, o["eventId"], o["message"]))
    groups, bad = A.build_groups(msgs)
    shell_pid = None
    for g in groups:
        g.parse()
        if shell_pid is None and g.success() and g.argv and g.argv[0] == "-bash":
            shell_pid = g.pid()
    execs_by_w = [[] for _ in range(n_win)]
    n_before = n_after = 0
    for g in sorted(groups, key=lambda g: (g.time, int(g.serial))):
        t = g.time - t0
        if t < 0:
            n_before += 1
            continue
        if t >= duration:
            n_after += 1
            continue
        execs_by_w[int(t // L) if int(t // L) < n_win else n_win - 1].append(g)
    rows = []
    kept_records = {}
    n_exec_kept = 0
    for k in range(n_win):
        ts, te = k * L, min((k + 1) * L, duration)
        base = (cnt_a[k][0] + cnt_a[k][1]) >= 1
        reason = ""
        if not base:
            reason = "no_terminal_record"
        elif te - ts < C.MIN_WINDOW_S:
            reason = "shorter_than_15s"
        elif (cnt_f[k][0] + cnt_f[k][1]) == 0:
            reason = "validator_only"
        elif exit_only[k]:
            reason = "closing_exit_only"
        stg = stage_of(timeline, finished7, t0 + ts)
        wid = "%s_w%04d" % (lk, k)
        raw_keep = (cnt_raw[k][0] + cnt_raw[k][1]) >= 1 and te - ts >= C.MIN_WINDOW_S
        rows.append(dict(window_id=wid, session_key=sk, login_key=lk, login_order=order, w_index=k,
                         t_start=round(ts, 3), t_end=round(te, 3), n_input=cnt_f[k][0], n_output=cnt_f[k][1],
                         n_exec=len(execs_by_w[k]), keep=int(reason == ""), drop_reason=reason,
                         stage=stg, stage_group=stage_group(stg),
                         _kept_before_rules=int(base and te - ts >= C.MIN_WINDOW_S), _raw_keep=int(raw_keep),
                         _elapsed=round(elapsed_before + ts, 3)))
        if reason == "":
            # per-window local process numbers, the login shell always 1
            local = {}
            if shell_pid is not None:
                local[shell_pid] = 1

            def loc(pid):
                if pid not in local:
                    local[pid] = max(local.values(), default=1) + 1
                return local[pid]
            recs = list(recs_by_w[k])
            for g in execs_by_w[k]:
                ppid, pid = loc(g.ppid()), loc(g.pid())
                recs.append(dict(w=k, t=round(g.time - t0, 6), src="exec", ok=g.success(), pid=pid, ppid=ppid,
                                 exe=g.exe(), comm=g.comm(), path=g.exec_path(), argv=g.argv or [], cwd=g.cwd or ""))
                n_exec_kept += 1
            recs.sort(key=lambda x: (x["t"], 0 if x["src"] == "rec" else 1, x.get("i", 0)))
            kept_records[k] = recs
    rep.update(duration_s=round(duration, 3), windows=n_win,
               kept_before_rules=sum(x["_kept_before_rules"] for x in rows),
               kept_before_rules_on_raw_records=sum(x["_raw_keep"] for x in rows),
               kept=sum(x["keep"] for x in rows),
               dropped={d: sum(1 for x in rows if x["drop_reason"] == d) for d in
                        ("no_terminal_record", "shorter_than_15s", "validator_only", "closing_exit_only")},
               exec_events_in_kept_windows=n_exec_kept, exec_groups_before_recorder_start=n_before,
               exec_groups_after_recorder_end=n_after, login_shell_found=shell_pid is not None,
               kept_with_input=sum(1 for x in rows if x["keep"] and x["n_input"] > 0),
               kept_by_stage_group={sg: sum(1 for x in rows if x["keep"] and x["stage_group"] == sg)
                                    for sg in ("1-4", "5", "6", "7")},
               kept_before_rules_by_stage_group={sg: sum(1 for x in rows if x["_kept_before_rules"] and x["stage_group"] == sg)
                                                 for sg in ("1-4", "5", "6", "7")})
    return rows, kept_records, duration


WIN_COLS = ["window_id", "session_key", "login_key", "login_order", "w_index", "t_start", "t_end",
            "n_input", "n_output", "n_exec", "keep", "drop_reason", "stage", "stage_group"]


def main():
    rep = dict(step=STEP, code_version=C.CODE_VERSION, sessions={}, totals={})
    session_rows, login_rows, desc_sessions, acceptance_rows = [], [], [], []
    all_rows = {L: [] for L in C.WINDOW_LENGTHS}
    for sess in C.SESSION_ORDER:
        cfg = C.SESSIONS[sess]
        sk = IO.session_key(sess)
        sb, stg, sb_sha, stg_sha = IO.read_boundaries(sess)
        table = IO.login_table(sess, sb)
        raw_stats = raw_login_stats(sess)
        operator_logins = {r["login_id"] for r in table if r["typed_by"] == "operator"}
        timeline = sorted((M.epoch(m["native_time"]), int(m["accepted_stage"]))
                          for m in stg["markers"] if m["session_id"] in operator_logins)
        left_out_acc = [m for m in stg["markers"] if m["session_id"] not in operator_logins]
        finished7 = any(s == 7 for _, s in timeline)
        used = [r for r in table if r["included"]]
        used.sort(key=lambda r: raw_stats[r["login_id"]]["start_epoch"])
        rs = dict(session_key=sk, boundary_sha256=dict(session=sb_sha, stage=stg_sha),
                  acceptances_used=len(timeline), acceptances_left_out_not_operator=len(left_out_acc),
                  finished_stage_7=finished7, logins={})
        for L in C.WINDOW_LENGTHS:
            elapsed = 0.0
            for order, r in enumerate(used, 1):
                lrep = rs["logins"].setdefault(r["login_id"], dict(login_key=IO.login_key(r["login_id"])))
                wrep = lrep.setdefault("w%d" % L, {})
                rows, kept, duration = build_login(sess, r, order, elapsed, timeline, finished7, L, wrep)
                path = IO.out("data", "windows", "w%d" % L, sk, IO.login_key(r["login_id"]) + ".jsonl")
                with open(path, "w", encoding="utf-8") as f:
                    for k in sorted(kept):
                        for rec in kept[k]:
                            f.write(IO.dumps(rec) + "\n")
                wrep["output_sha256"] = IO.sha256_file(path)[0]
                all_rows[L].extend(rows)
                elapsed += duration
        # labels and description
        session_rows.append(dict(session_key=sk, **{"class": cfg["cls"]}, label_basis="post_collection_study_design",
                                 included=1, logins_used=len(used)))
        used_start = {r["login_id"]: raw_stats[r["login_id"]]["start_epoch"] for r in used}
        offsets = {}
        acc = 0.0
        for r in used:
            offsets[r["login_id"]] = acc
            acc += rs["logins"][r["login_id"]]["w30"]["duration_s"]
        desc_sessions.append(dict(session_key=sk, lab_range=cfg["lab_range"], logins_recorded=len(table),
                                  logins_used=len(used), working_time_s=round(acc, 3),
                                  stages_accepted_by_operator=len({s for _, s in timeline}),
                                  finished_stage_7=int(finished7)))
        for order, r in enumerate(sorted(table, key=lambda r: raw_stats.get(r["login_id"], {}).get("start_epoch", 0)), 1):
            st = raw_stats.get(r["login_id"], {})
            login_rows.append(dict(login_key=IO.login_key(r["login_id"]), session_key=sk,
                                   included=int(r["included"]), reason=r["reason"], typed_by=r["typed_by"],
                                   what=r["what"], duration_s=st.get("duration_s", ""), inputs=st.get("inputs", ""),
                                   enter_presses=st.get("enter_presses", ""), how_ended=st.get("how_ended", ""),
                                   note=r["note"]))
        for ta, s in timeline:
            m = [x for x in stg["markers"] if int(x["accepted_stage"]) == s and abs(M.epoch(x["native_time"]) - ta) < 1e-6][0]
            lid = m["session_id"]
            in_used = lid in offsets
            acceptance_rows.append(dict(session_key=sk, stage=s, in_used_login=int(in_used),
                                        login_key=IO.login_key(lid),
                                        elapsed_working_s=round(offsets[lid] + ta - used_start[lid], 3) if in_used else ""))
        rep["sessions"][sess] = rs
    # ---- write tables
    for L in C.WINDOW_LENGTHS:
        with open(IO.out("data", "windows", "w%d" % L, "windows.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=WIN_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows[L])
        with open(IO.out("data", "description", "window_description_w%d.csv" % L), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["window_id", "session_key", "login_order", "elapsed_working_s", "stage", "stage_group", "keep"])
            for x in all_rows[L]:
                w.writerow([x["window_id"], x["session_key"], x["login_order"], x["_elapsed"], x["stage"], x["stage_group"], x["keep"]])

    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    # private map from keys to original ids: every session and every recorded login
    with open(IO.out("data", "labels", "_private", "key_map.csv"), "w", encoding="utf-8") as f:
        f.write("kind,key,original_id\n")
        for sess in C.SESSION_ORDER:
            f.write("session,%s,%s\n" % (IO.session_key(sess), sess))
            sb, _, _, _ = IO.read_boundaries(sess)
            for r in IO.login_table(sess, sb):
                f.write("login,%s,%s\n" % (IO.login_key(r["login_id"]), r["login_id"]))
    write_csv(IO.out("data", "labels", "sessions.csv"), session_rows)
    write_csv(IO.out("data", "labels", "logins.csv"), login_rows)
    write_csv(IO.out("data", "description", "sessions.csv"), desc_sessions)
    write_csv(IO.out("data", "description", "stage_acceptances.csv"), acceptance_rows)
    # ---- totals by class (description of the design; the class comes from the study design)
    for L in C.WINDOW_LENGTHS:
        tot = {}
        sk_cls = {IO.session_key(s): C.SESSIONS[s]["cls"] for s in C.SESSION_ORDER}
        for x in all_rows[L]:
            c = sk_cls[x["session_key"]]
            d = tot.setdefault(c, dict(kept_before_rules=0, kept=0, by_stage_group_before_rules={}, by_stage_group={}))
            if x["_kept_before_rules"]:
                d["kept_before_rules"] += 1
                d["by_stage_group_before_rules"][x["stage_group"]] = d["by_stage_group_before_rules"].get(x["stage_group"], 0) + 1
            if x["keep"]:
                d["kept"] += 1
                d["by_stage_group"][x["stage_group"]] = d["by_stage_group"].get(x["stage_group"], 0) + 1
        rep["totals"]["w%d" % L] = tot
    rep["outputs"] = {}
    for rel in (["data/windows/w%d/windows.csv" % L for L in C.WINDOW_LENGTHS] +
                ["data/description/window_description_w%d.csv" % L for L in C.WINDOW_LENGTHS] +
                ["data/labels/sessions.csv", "data/labels/logins.csv", "data/description/sessions.csv",
                 "data/description/stage_acceptances.csv"]):
        rep["outputs"][rel] = IO.sha256_file(os.path.join(C.out_root(), rel))[0]
    IO.write_json(IO.out("reports", "05_windows_report.json"), rep)
    for sess in C.SESSION_ORDER:
        rs = rep["sessions"][sess]
        for login, v in rs["logins"].items():
            w = v["w30"]
            print(sess, login[:8], "30s: windows", w["windows"], "kept before rules", w["kept_before_rules"],
                  "(raw %d)" % w["kept_before_rules_on_raw_records"], "kept", w["kept"], w["dropped"], w["kept_by_stage_group"])
    print(json.dumps(rep["totals"]))
    print("COMPLETE: windows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
