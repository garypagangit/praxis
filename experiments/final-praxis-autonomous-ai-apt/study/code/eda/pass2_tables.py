"""EDA Pass 2, tables (handoff section 6): T4 to T9 and the tables the figures are drawn from.

Run after the trials, as a report only (handoff 12a; F16 of the feature and trial design).
Nothing here can change a feature, a model or a score.

Rows (handoff rule 3): feature values and command text are read from rows marked `train`
in the frozen split file and from no other row. Class comes from the session table, the
stage group and the lab range from the description files. No model is fitted (rule 4):
every statistic is a rank statistic of one or two columns.

T4 to T8 are written for 30 s windows and again for 60 s windows. T9 and the figure
tables are written for 30 s windows.
"""
import base64
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import pass2_common as C

E = C.E
np = C.np

GROUP_KEY = {"1-4": "s1_4", "5": "s5", "6": "s6", "7": "s7"}

# E5: the lab's machines. Names and last octets are the GOAD layout the lab was built from;
# the addresses are the ones the commands use. Cross-checked against program output in the
# training windows (machine_crosscheck).
MACHINES = [
    ("kingslanding", "DC01", "sevenkingdoms.local", "10.78.40.10"),
    ("winterfell", "DC02", "north.sevenkingdoms.local", "10.78.40.11"),
    ("meereen", "DC03", "essos.local", "10.78.40.12"),
    ("castelblack", "SRV02", "north.sevenkingdoms.local", "10.78.40.22"),
    ("braavos", "SRV03", "essos.local", "10.78.40.23"),
]

# E1: the example windows are picked by a fixed rule, never by reading them.
E1_PROGRAMS = ("nmap", "ping", "fping", "dig", "host", "nslookup", "hostname", "whoami", "id", "uname",
               "curl", "wget", "gobuster")
E1_SCREEN = re.compile(r"(?i)pass|pwd|secret|cred|hash|ntlm|token|ticket|key|:\S*@|%")
E1_WEB = {                                     # these can carry a login, a header, a cookie or form data:
    "curl": re.compile(r"(?:^|\s)(?:-[uUHdbF]\b|--user\S*|--proxy-\S+|--header\S*|--data\S*|--cookie\S*|--form\S*)"),
    "wget": re.compile(r"(?:^|\s)(?:--user\S*|--http-\S+|--proxy-\S+|--header\S*|--post-\S+|--load-cookies\S*)"),
    "gobuster": re.compile(r"(?:^|\s)(?:-[UPHc]\b|--user\S*|--header\S*|--cookie\S*)"),
}
E1_TEXT_MAX = 38

RANGE_COMPARISONS = [                      # (key, class, first range, second range)
    ("human_OA_vs_AHIR-03", "human", "Original Austin", "AHIR-03"),
    ("ai_OA_vs_AHIR-03", "ai", "Original Austin", "AHIR-03"),
    ("human_AHIR-01_vs_AHIR-03", "human", "AHIR-01", "AHIR-03"),
    ("ai_AHIR-01_vs_AHIR-03", "ai", "AHIR-01", "AHIR-03"),
    ("human_AHIR-01_vs_OA", "human", "AHIR-01", "Original Austin"),
]
RANGE_PAIRS = [("OA_vs_AHIR-03", "human_OA_vs_AHIR-03", "ai_OA_vs_AHIR-03"),
               ("AHIR-01_vs_AHIR-03", "human_AHIR-01_vs_AHIR-03", "ai_AHIR-01_vs_AHIR-03")]


# ------------------------------------------------------------------------------------- T4
def indicator(rows, col, cls):
    return [0.0 if r["x"][col] is None else 1.0 for r in rows if r["class"] == cls]


def profile(rows, cols, sessions):
    labels = [s["session"] for s in sessions]
    subsets = {s: [r for r in rows if r["session"] != s] for s in labels}
    out = []
    for order, c in enumerate(cols):
        col = c["column"]
        rec = dict(c)
        rec["order"] = order
        for cls in E.CLASSES:
            n = sum(1 for r in rows if r["class"] == cls)
            v = np.array(C.values(rows, col, cls), dtype=float)
            rec["n_" + cls] = n
            rec["defined_" + cls] = int(len(v))
            rec["defined_share_" + cls] = len(v) / n
            rec["zero_share_" + cls] = float((v == 0).mean()) if len(v) else None
            q = np.percentile(v, [25, 50, 75]) if len(v) else [None, None, None]
            rec["q1_" + cls], rec["median_" + cls], rec["q3_" + cls] = (None if x is None else float(x) for x in q)
        a = C.a_stat(C.values(rows, col, "ai"), C.values(rows, col, "human"))
        ia = C.a_stat(indicator(rows, col, "ai"), indicator(rows, col, "human"))
        rec["a"], rec["auc"] = a, C.auc_of(a)
        rec["higher_in"] = "" if a is None else ("ai" if a >= 0.5 else "human")
        rec["ind_a"], rec["ind_auc"] = ia, C.auc_of(ia)
        rec["ind_more_in"] = "" if ia == 0.5 else ("ai" if ia > 0.5 else "human")
        drops, ind_drops = [], []
        for s in labels:
            sub = subsets[s]
            d = C.directed(C.a_stat(C.values(sub, col, "ai"), C.values(sub, col, "human")), a)
            if d is not None:
                drops.append((d, s))
            idd = C.directed(C.a_stat(indicator(sub, col, "ai"), indicator(sub, col, "human")), ia)
            ind_drops.append((idd, s))
        rec["drops"] = len(drops)
        rec["drop_min"], rec["drop_min_s"] = min(drops) if drops else (None, "")
        rec["drop_max"], rec["drop_max_s"] = max(drops, key=lambda t: (t[0], [-ord(ch) for ch in t[1]])) if drops else (None, "")
        rec["ind_drop_min"], rec["ind_drop_max"] = min(ind_drops)[0], max(ind_drops)[0]
        basis = []
        if rec["auc"] is not None and rec["auc"] >= C.FLAG:
            basis.append("AUC, all training rows")
        if rec["ind_auc"] >= C.FLAG:
            basis.append("is-defined indicator, all training rows")
        if not basis:
            if rec["drop_max"] is not None and rec["drop_max"] >= C.FLAG:
                basis.append("AUC, only with one session left out (%s)" % rec["drop_max_s"])
            if rec["ind_drop_max"] >= C.FLAG:
                basis.append("is-defined indicator, only with one session left out")
        rec["flag"] = "yes" if basis else "no"
        rec["flag_all_rows"] = bool(basis) and "only with" not in basis[0]
        rec["flag_basis"] = "; ".join(basis)
        out.append(rec)
    ranked = sorted(out, key=lambda r: (r["auc"] is None, -(r["auc"] or 0.0), r["order"]))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return ranked


# ------------------------------------------------------------------------------------- T6
def merge_duplicates(rows, ranked):
    """Walking down the AUC ranking, a feature with |rho| > 0.98 against a higher-ranked
    feature joins that feature's group. Returns (head_of, links, rho cache)."""
    cache, head_of, links = {}, {}, []

    def rho(c1, c2):
        key = (c1, c2) if c1 < c2 else (c2, c1)
        if key not in cache:
            cache[key] = C.spearman(rows, key[0], key[1])
        return cache[key]

    for i, p in enumerate(ranked):
        hit = None
        for q in ranked[:i]:
            r, n = rho(p["column"], q["column"])
            if r is not None and n >= C.DUP_MIN_ROWS and abs(r) > C.DUP_RHO:
                hit = (q, r, n)
                break
        if hit is None:
            head_of[p["column"]] = p["column"]
        else:
            head_of[p["column"]] = head_of[hit[0]["column"]]
            links.append({"member": p["column"], "member_rank": p["rank"], "matched": hit[0]["column"],
                          "head": head_of[p["column"]], "rho": hit[1], "n": hit[2]})
    for p in ranked:
        p["merged_into"] = "" if head_of[p["column"]] == p["column"] else head_of[p["column"]]
    heads = [p for p in ranked if not p["merged_into"] and p["auc"] is not None]
    for i, p in enumerate(heads[:C.TOP_N]):
        p["top_rank"] = i + 1
    return head_of, links, rho, heads[:C.TOP_N]


# ------------------------------------------------------------------------------------- T7, T8
def stage_counts(rows):
    out = {}
    for cls in E.CLASSES:
        for g in E.STAGE_GROUPS:
            count = collections.Counter(r["session"] for r in rows if r["class"] == cls and r["stage_group"] == g)
            n = sum(count.values())
            top = sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))[0] if n else ("", 0)
            out[(cls, g)] = {"n": n, "sessions": len(count), "largest": top[0], "largest_n": top[1],
                             "largest_share": "%.1f" % (100.0 * top[1] / n) if n else ""}
    return out


def same_stage(rows, p):
    col, res = p["column"], {}
    for g in E.STAGE_GROUPS:
        keep = lambda r, g=g: r["stage_group"] == g
        a = C.a_stat(C.values(rows, col, "ai", keep), C.values(rows, col, "human", keep))
        nh, sh, th, shh = C.sessions_behind(rows, col, "human", keep)
        na, sa, ta, sha = C.sessions_behind(rows, col, "ai", keep)
        res[g] = {"a": a, "auc": C.auc_of(a), "auc_dir": C.directed(a, p["a"]),
                  "higher_in": "" if a is None else ("ai" if a >= 0.5 else "human"),
                  "n_human": nh, "sessions_human": sh, "largest_human": th, "largest_human_share": shh,
                  "n_ai": na, "sessions_ai": sa, "largest_ai": ta, "largest_ai_share": sha,
                  "indicative": "" if a is None else ("yes" if min(nh, na) < C.MIN_WINDOWS else "no")}
    return res


def mean(vals):
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


# ------------------------------------------------------------------------------------- E1
def show_text(raw):
    """Terminal bytes as printable text: control characters are written out, long text is cut."""
    s = raw.decode("utf-8", "replace")
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\r":
            out.append("\\r")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif o == 27:
            out.append("\\e")
        elif o < 32 or o == 127:
            out.append("\\x%02x" % o)
        else:
            out.append(ch)
    s = "".join(out)
    return s if len(s) <= E1_TEXT_MAX else s[:E1_TEXT_MAX - 1] + "…"


def e1_example(inp, wl, rows, cmds, top6, checks_log):
    by_win = collections.defaultdict(list)
    for c in cmds:
        by_win[c["window_id"]].append(c)
    lines_out, feat_out, picked = [], {}, {}
    for cls in E.CLASSES:
        tried = 0
        for r in rows:                                     # table order: the first window that passes
            if r["class"] != cls or r["stage_group"] != "1-4":
                continue
            cs = by_win.get(r["window_id"], [])
            if len(cs) != 1:
                continue
            c = cs[0]
            starts = c["programs_started"]
            if (not c["at_prompt"] or c["lines"] != 1 or c["program"] not in E1_PROGRAMS or c["failed"]
                    or not any(s["window_id"] == r["window_id"] for s in starts)
                    or E1_SCREEN.search(c["text"])
                    or (c["program"] in E1_WEB and E1_WEB[c["program"]].search(c["text"]))):
                continue
            tried += 1
            login_key, w = r["window_id"].rsplit("_w", 1)
            rel = C.window_file(r["session_key"], login_key, wl)
            inp.allow.add(rel)
            recs = []
            with open(inp.path(rel), encoding="utf-8") as f:
                for line in f:
                    o = json.loads(line)
                    if o["w"] == int(w):
                        recs.append(o)
            ins = [o for o in recs if o["src"] == "rec" and o["kind"] == "input"]
            outs = [o for o in recs if o["src"] == "rec" and o["kind"] == "output"]
            execs = [o for o in recs if o["src"] == "exec" and o["ok"]]
            enter = [o for o in ins if b"\r" in base64.b64decode(o["data_base64"])]
            if not ins or len(enter) != 1 or not outs:
                continue
            t_enter = enter[0]["t"]
            ex = [o for o in execs if o["t"] >= t_enter][:2]
            shown_in = [ins[0]] + ([enter[0]] if enter[0] is not ins[0] else [])
            want_out = 1 if len(shown_in) + len(ex) >= 3 else 2          # four to six lines in all
            after = [o for o in outs if o["t"] >= (ex[0]["t"] if ex else t_enter)
                     and base64.b64decode(o["data_base64"]).strip()][:want_out]
            if not ex or not after:
                continue
            chosen = shown_in + ex + after
            chosen.sort(key=lambda o: (o["t"], 0 if o["src"] == "rec" else 1))
            texts = []
            for o in chosen:
                if o["src"] == "rec":
                    raw = base64.b64decode(o["data_base64"])
                    texts.append(("recorder", o["kind"], "%d bytes" % len(raw), show_text(raw)))
                else:
                    texts.append(("audit", "exec", "process %d, parent %d" % (o["pid"], o["ppid"]),
                                  show_text(("%s  cwd %s" % (o["path"], o["cwd"])).encode("utf-8"))))
            if any(E1_SCREEN.search(t[3]) for t in texts):
                continue
            t0 = int(w) * int(wl[1:])                      # shown from the start of the window
            for i, (o, t) in enumerate(zip(chosen, texts)):
                lines_out.append([cls, r["session"], "1-4", i + 1, "%.3f" % (o["t"] - t0), t[0], t[1], t[2], t[3]])
            picked[cls] = {"session": r["session"], "candidates_tried": tried, "input_records": len(ins),
                           "output_records": len(outs), "program_starts": len(execs), "lines_shown": len(chosen)}
            feat_out[cls] = {p["column"]: r["x"][p["column"]] for p in top6}
            break
        if cls not in picked:
            picked[cls] = {"session": "", "candidates_tried": tried, "note": "no window passed the rule"}
    E.write_csv("E1_data_example.csv",
                ["class", "session", "stage_group", "line", "t_in_window_s", "source", "kind", "detail", "text"], lines_out)
    E.write_csv("E1_window_summary.csv", ["class", "session", "input_records", "output_records", "program_starts", "lines_shown"],
                [[cls, picked[cls].get("session", ""), picked[cls].get("input_records", ""),
                  picked[cls].get("output_records", ""), picked[cls].get("program_starts", ""),
                  picked[cls].get("lines_shown", "")] for cls in E.CLASSES])
    E.write_csv("E1_feature_rows.csv", ["feature", "tier", "human", "ai"],
                [[p["column"], p["tier"]] + [("" if cls not in feat_out else
                                               ("undefined" if feat_out[cls][p["column"]] is None
                                                else C.g6(feat_out[cls][p["column"]]))) for cls in E.CLASSES]
                 for p in top6])
    checks_log["E1"] = {"rule": "first training window of stage group 1-4, in table order, that holds one command, "
                                "submitted at the shell prompt on one line, whose program is on the fixed list %s, did "
                                "not fail, started at least one program in that window, and whose text and shown lines "
                                "pass the credential screen (for %s the options that carry a login, a header, a cookie "
                                "or form data are screened as well)" % (list(E1_PROGRAMS), sorted(E1_WEB)),
                        "picked": picked,
                        "to_be_read_by_a_person_before_use": True}


# ------------------------------------------------------------------------------------- E5
def machine_tables(rows, cmds, sessions):
    cls_of = {s["session"]: s["class"] for s in sessions}
    ses_of = {r["window_id"]: r["session"] for r in rows}
    pats = []
    for name, role, domain, addr in MACHINES:
        pats.append((name, re.compile(r"(?i)(?<![a-z0-9])%s(?![a-z0-9])|(?<![\d.])%s(?![\d.])"
                                      % (re.escape(name), re.escape(addr)))))
    n_cmd = collections.Counter(cls_of[ses_of[c["window_id"]]] for c in cmds)
    n_cmd_s = collections.Counter(ses_of[c["window_id"]] for c in cmds)
    hit = collections.defaultdict(collections.Counter)            # machine -> session -> commands
    for c in cmds:
        for name, rx in pats:
            if rx.search(c["text"]):
                hit[name][ses_of[c["window_id"]]] += 1
    out, detail = [], []
    for name, role, domain, addr in MACHINES:
        for cls in E.CLASSES:
            ses = [s["session"] for s in sessions if s["class"] == cls]
            n = sum(hit[name][s] for s in ses)
            out.append([name, role, domain, addr, cls, n, n_cmd[cls], "%.1f" % (100.0 * n / n_cmd[cls]),
                        sum(1 for s in ses if hit[name][s]), len(ses)])
        for s in sessions:
            detail.append([name, s["session"], s["class"], hit[name][s["session"]], n_cmd_s[s["session"]]])
    E.write_csv("E5_machines_by_class.csv",
                ["machine", "role", "domain", "address", "class", "commands_naming", "class_commands", "share_pct",
                 "sessions_addressing", "sessions_in_class"], out)
    E.write_csv("E5_machines_by_session.csv", ["machine", "session", "class", "commands_naming", "session_commands"], detail)
    return dict(n_cmd)


def scan_training_windows(inp, wl, rows):
    """One read of the cleaned records of the training windows (never of another window).

    Returns (machine cross-check, input-record counts per window). The cross-check compares
    name (address) pairs that programs printed with the fixed machine list. The input-record
    counts are what the T5 review of the input-channel columns rests on.
    """
    want = {name: addr for name, _, _, addr in MACHINES}
    rx = re.compile(rb"(?i)\b(kingslanding|winterfell|meereen|castelblack|braavos)(?:\.[a-z0-9.-]+)?\s*\((10\.78\.40\.\d{1,3})\)")
    by_file = collections.defaultdict(dict)
    for r in rows:
        login_key, w = r["window_id"].rsplit("_w", 1)
        by_file[C.window_file(r["session_key"], login_key, wl)][int(w)] = r["window_id"]
    pairs = collections.Counter()
    stats = {r["window_id"]: {"input_records": 0, "input_bytes": 0, "enter_records": 0, "enter_records_with_text": 0}
             for r in rows}
    for rel in sorted(by_file):
        inp.allow.add(rel)
        with open(inp.path(rel), encoding="utf-8") as f:
            for line in f:
                o = json.loads(line)
                if o["src"] != "rec" or o["w"] not in by_file[rel]:
                    continue
                data = base64.b64decode(o["data_base64"])
                if o["kind"] == "output":
                    for m in rx.finditer(data):
                        pairs[(m.group(1).decode().lower(), m.group(2).decode())] += 1
                elif o["kind"] == "input":
                    st = stats[by_file[rel][o["w"]]]
                    st["input_records"] += 1
                    st["input_bytes"] += len(data)
                    if b"\r" in data:
                        st["enter_records"] += 1
                        if data.strip(b"\r"):
                            st["enter_records_with_text"] += 1
    against = sorted("%s (%s)" % k for k in pairs if want[k[0]] != k[1])
    if against:
        raise SystemExit("STOP: program output contradicts the machine list: %s" % against)
    cross = {"window_files_read": len(by_file), "pairs_found": {"%s (%s)" % k: v for k, v in sorted(pairs.items())},
             "machines_confirmed": sorted(set(k[0] for k in pairs)), "contradictions": 0}
    return cross, stats


def review_table(rows, cmds, sessions, stats, seconds):
    """T5 review, by session: how the commands of the training windows reached the shell,
    counted from the cleaned recorder records and from the per-command table."""
    styles = ["typed", "paste", "recall", "line"]
    ses_of = {r["window_id"]: r["session"] for r in rows}
    ent = collections.defaultdict(collections.Counter)
    for c in cmds:
        ent[ses_of[c["window_id"]]][c["entry_style"]] += 1
    out, tot = [], {}
    for s in sessions:
        ws = [r for r in rows if r["session"] == s["session"] and r["x"]["cmd_count"] > 0]
        rec = {"windows": len(ws), "commands": int(sum(r["x"]["cmd_count"] for r in ws))}
        for k in ("input_records", "input_bytes", "enter_records", "enter_records_with_text"):
            rec[k] = sum(stats[r["window_id"]][k] for r in ws)
        for k in styles:
            rec[k] = ent[s["session"]][k]
        t = tot.setdefault(s["class"], collections.Counter())
        t.update(rec)
        out.append((s["class"], s["session"], rec))
    for cls in E.CLASSES:
        out.append((cls, "all %s sessions" % E.CLASS_LABEL[cls], tot[cls]))
    E.write_csv("T5_review_input_records_w%d.csv" % seconds,
                ["class", "session", "training_windows_with_a_command", "commands", "typed", "pasted", "recalled",
                 "whole_line", "input_records", "input_records_per_command", "input_bytes", "enter_records",
                 "enter_records_that_carry_text", "share_of_enter_records_that_carry_text_pct"],
                [[cls, name, r["windows"], r["commands"], r["typed"], r["paste"], r["recall"], r["line"],
                  r["input_records"], "%.2f" % (r["input_records"] / r["commands"]) if r["commands"] else "",
                  r["input_bytes"], r["enter_records"], r["enter_records_with_text"],
                  "%.1f" % (100.0 * r["enter_records_with_text"] / r["enter_records"]) if r["enter_records"] else ""]
                 for cls, name, r in out])
    return {cls: {k: int(v) for k, v in sorted(tot[cls].items())} for cls in E.CLASSES}


# ------------------------------------------------------------------------------------- E7, E8
def activity_tables(rows, cmds):
    by_win = collections.defaultdict(list)
    for c in cmds:
        by_win[c["window_id"]].append(c)
    kinds = ["quiet", "no_program", "programs"]
    cnt = {cls: collections.Counter() for cls in E.CLASSES}
    for r in rows:
        cs = by_win.get(r["window_id"], [])
        if (r["x"]["cmd_count"] > 0) != bool(cs):
            raise SystemExit("STOP: cmd_count and the per-command table disagree for a window")
        k = "quiet" if not cs else ("programs" if any(c["programs_started"] for c in cs) else "no_program")
        cnt[r["class"]][k] += 1
    out = []
    for cls in E.CLASSES:
        n = sum(cnt[cls].values())
        for k in kinds:
            out.append([cls, k, cnt[cls][k], n, "%.1f" % (100.0 * cnt[cls][k] / n)])
    E.write_csv("E7_window_activity_by_class.csv", ["class", "window_type", "windows", "class_windows", "share_pct"], out)

    cls_of = {r["window_id"]: r["class"] for r in rows}
    styles = ["typed", "paste", "recall", "line"]
    ent = {cls: collections.Counter() for cls in E.CLASSES}
    where = {cls: collections.Counter() for cls in E.CLASSES}
    for c in cmds:
        cls = cls_of[c["window_id"]]
        ent[cls][c["entry_style"]] += 1
        where[cls][("at_prompt" if c["at_prompt"] else "in_program", "started" if c["programs_started"] else "none")] += 1
    out = []
    for cls in E.CLASSES:
        n = sum(ent[cls].values())
        if set(ent[cls]) - set(styles):
            raise SystemExit("STOP: unknown entry style")
        for k in styles:
            out.append([cls, k, ent[cls][k], n, "%.1f" % (100.0 * ent[cls][k] / n)])
    E.write_csv("E7_entry_style_by_class.csv", ["class", "entry_style", "commands", "class_commands", "share_pct"], out)
    out = []
    for cls in E.CLASSES:
        n = sum(where[cls].values())
        for place in ("at_prompt", "in_program"):
            for st in ("started", "none"):
                out.append([cls, place, st, where[cls][(place, st)], n, "%.1f" % (100.0 * where[cls][(place, st)] / n)])
    E.write_csv("E7_commands_by_place.csv", ["class", "typed_where", "programs", "commands", "class_commands", "share_pct"], out)
    return {cls: dict(cnt[cls]) for cls in E.CLASSES}


def program_tables(rows, cmds, counts):
    info = {r["window_id"]: r for r in rows}
    ran = collections.defaultdict(set)                          # program -> training windows in which it ran
    for c in cmds:
        for s in c["programs_started"]:
            ran[s["program"]].add(s["window_id"])
    top = sorted(ran.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:15]
    t_out, h_out = [], []
    for i, (prog, wins) in enumerate(top):
        by_g = collections.Counter(info[w]["stage_group"] for w in wins)
        by_c = collections.Counter(info[w]["class"] for w in wins)
        ses = {cls: len(set(info[w]["session"] for w in wins if info[w]["class"] == cls)) for cls in E.CLASSES}
        only = [cls for cls in E.CLASSES if by_c[cls] == len(wins)]
        t_out.append([i + 1, prog, len(wins)] + [by_g[g] for g in E.STAGE_GROUPS]
                     + [by_c["human"], by_c["ai"], ses["human"], ses["ai"], only[0] if only else ""])
        for cls in E.CLASSES:
            for g in E.STAGE_GROUPS:
                n_cell = counts[(cls, g)]["n"]
                n_ran = sum(1 for w in wins if info[w]["class"] == cls and info[w]["stage_group"] == g)
                h_out.append([i + 1, prog, cls, g, n_ran, n_cell, "" if not n_cell else "%.1f" % (100.0 * n_ran / n_cell)])
    E.write_csv("E8_top_programs.csv",
                ["rank", "program", "training_windows"] + ["windows_stage_" + g for g in E.STAGE_GROUPS]
                + ["windows_human", "windows_ai", "sessions_human", "sessions_ai", "only_class"], t_out)
    E.write_csv("E8_program_stage_heatmap.csv",
                ["rank", "program", "class", "stage_group", "windows_ran", "class_windows_in_stage_group", "share_pct"], h_out)
    return {"distinct_programs": len(ran), "windows_with_a_program_start": len(set(w for v in ran.values() for w in v))}


# ------------------------------------------------------------------------------------- one window length
REVIEW_ROWS = []          # T5 review: training windows by session, both window lengths


def windows_by_session(rows, sessions, seconds):
    out = []
    for s in sessions:
        ws = [r for r in rows if r["session"] == s["session"]]
        with_cmd = [r for r in ws if r["x"]["cmd_count"] > 0]
        out.append([seconds, s["class"], s["session"], len(ws), len(with_cmd), len(ws) - len(with_cmd),
                    sum(1 for r in with_cmd if r["x"]["line_ratio"] > 0),
                    sum(1 for r in with_cmd if r["x"]["compose_time_median"] == 0),
                    sum(1 for r in with_cmd if r["x"]["input_writes_per_cmd"] <= 1)])
    return out


def tables_for(inp, wl, seconds, sessions, check, log, review):
    rows, columns, load_log = C.load_training(inp, wl, sessions)
    REVIEW_ROWS.extend(windows_by_session(rows, sessions, seconds))
    cols, meta = C.load_columns(inp, wl)
    if [c["column"] for c in cols] != columns:
        raise SystemExit("STOP: the feature table and the column file differ (%s)" % wl)
    log["training_rows"][wl] = load_log

    # check 1: class, session and stage-group totals equal Pass 1's T3
    t3 = [r for r in C.pass1_table(inp, "T3_split_counts.csv", ["window_s", "row_type", "session", "class", "train"])
          if r["window_s"] == str(seconds)]
    for r in t3:
        if r["row_type"] == "session":
            check("%s training rows %s" % (wl, r["session"]), int(r["train"]), sum(1 for x in rows if x["session"] == r["session"]))
        elif r["row_type"] == "class_total":
            check("%s training rows %s" % (wl, r["class"]), int(r["train"]), sum(1 for x in rows if x["class"] == r["class"]))
        else:
            check("%s training rows all" % wl, int(r["train"]), len(rows))
    counts = stage_counts(rows)
    for r in C.pass1_table(inp, "T3_split_rows_by_stage_group.csv",
                           ["window_s", "class", "stage_group", "train", "train_sessions_supplying"]):
        if r["window_s"] != str(seconds):
            continue
        k = (r["class"], r["stage_group"])
        check("%s training rows %s stage %s" % (wl, k[0], k[1]), int(r["train"]), counts[k]["n"])
        check("%s sessions %s stage %s" % (wl, k[0], k[1]), int(r["train_sessions_supplying"] or 0), counts[k]["sessions"])

    # T4 with the ranking, T6 merge, top 20
    ranked = profile(rows, cols, sessions)
    head_of, links, rho, top = merge_duplicates(rows, ranked)
    for p in ranked:
        check("%s %s class totals" % (wl, p["column"]), (counts_class(rows, "human"), counts_class(rows, "ai")),
              (p["n_human"], p["n_ai"]))
    yn = lambda b: "yes" if b else "no"
    E.write_csv("T4_feature_profile_%s.csv" % wl,
                ["window_s", "rank", "feature", "tier", "goes_with", "in_main_configuration", "kind",
                 "n_human", "n_ai", "defined_human", "defined_ai", "defined_share_human", "defined_share_ai",
                 "zero_share_human", "zero_share_ai", "median_human", "q1_human", "q3_human",
                 "median_ai", "q1_ai", "q3_ai", "a_ai_higher", "auc", "higher_in",
                 "auc_drop_min", "auc_drop_min_without", "auc_drop_max", "auc_drop_max_without", "drops_computed",
                 "indicator_auc", "defined_more_often_in", "indicator_drop_min", "indicator_drop_max",
                 "flag", "flag_basis", "merged_into", "top20_rank"],
                [[seconds, p["rank"], p["column"], p["tier"], p["goes_with"], yn(p["in_main"]), p["kind"],
                  p["n_human"], p["n_ai"], p["defined_human"], p["defined_ai"],
                  C.f4(p["defined_share_human"]), C.f4(p["defined_share_ai"]),
                  C.f4(p["zero_share_human"]), C.f4(p["zero_share_ai"]),
                  C.g6(p["median_human"]), C.g6(p["q1_human"]), C.g6(p["q3_human"]),
                  C.g6(p["median_ai"]), C.g6(p["q1_ai"]), C.g6(p["q3_ai"]),
                  C.f4(p["a"]), C.f4(p["auc"]), p["higher_in"],
                  C.f4(p["drop_min"]), p["drop_min_s"], C.f4(p["drop_max"]), p["drop_max_s"], p["drops"],
                  C.f4(p["ind_auc"]), p["ind_more_in"], C.f4(p["ind_drop_min"]), C.f4(p["ind_drop_max"]),
                  p["flag"], p["flag_basis"], p["merged_into"], p.get("top_rank", "")] for p in ranked])

    # T5
    flagged = [p for p in ranked if p["flag"] == "yes"]
    notes = review.get(wl, {})
    t5 = []
    for p in flagged:
        note = notes.get(p["column"], {})
        t5.append([seconds, p["column"], p["tier"], yn(p["in_main"]), p["flag_basis"], C.f4(p["auc"]), p["higher_in"],
                   C.f4(p["drop_min"]), C.f4(p["drop_max"]), p["drop_max_s"], C.f4(p["ind_auc"]), p["ind_more_in"],
                   C.f4(p["ind_drop_max"]), note.get("finding", "review pending"),
                   note.get("action", "Reported beside the results; not corrected (handoff 12a, F16)")])
    if not t5:
        t5.append([seconds, "none flagged", "", "", "", "", "", "", "", "", "", "", "",
                   "No feature and no is-defined indicator reaches %.2f on the training rows, with all sessions or "
                   "with any one session left out" % C.FLAG, "none needed"])
    E.write_csv("T5_shortcut_audit_%s.csv" % wl,
                ["window_s", "feature", "tier", "in_main_configuration", "flag_basis", "auc", "higher_in",
                 "auc_drop_min", "auc_drop_max", "auc_drop_max_without", "indicator_auc", "defined_more_often_in",
                 "indicator_drop_max", "review_finding", "action"], t5)

    # T6
    rank_of = {p["column"]: p["rank"] for p in ranked}
    t6 = [[seconds, l["head"], rank_of[l["head"]], l["member"], l["member_rank"], l["matched"], C.f4(l["rho"]), l["n"]]
          for l in sorted(links, key=lambda l: (rank_of[l["head"]], l["member_rank"]))]
    if not t6:
        t6 = [[seconds, "none", "", "", "", "", "", ""]]
    E.write_csv("T6_near_duplicates_%s.csv" % wl,
                ["window_s", "group_head", "head_rank", "member", "member_rank", "matched_feature", "spearman_rho",
                 "rows_both_defined"], t6)
    members = collections.defaultdict(list)
    for l in links:
        members[l["head"]].append(l["member"])

    # T7: same-stage AUC for every feature (long) and the top 20 (wide)
    stage = {p["column"]: same_stage(rows, p) for p in ranked}
    long_rows = []
    for p in ranked:
        for g in E.STAGE_GROUPS:
            s = stage[p["column"]][g]
            long_rows.append([seconds, p["rank"], p["column"], p["tier"], yn(p["in_main"]), g, C.f4(s["a"]), C.f4(s["auc"]),
                              C.f4(s["auc_dir"]), s["higher_in"], s["n_human"], s["sessions_human"], s["largest_human"],
                              s["largest_human_share"], s["n_ai"], s["sessions_ai"], s["largest_ai"],
                              s["largest_ai_share"], s["indicative"]])
    E.write_csv("T7_same_stage_auc_all_features_%s.csv" % wl,
                ["window_s", "rank", "feature", "tier", "in_main_configuration", "stage_group", "a_ai_higher", "auc",
                 "auc_in_all_rows_direction", "higher_in", "n_human", "sessions_human", "largest_human",
                 "largest_human_share_pct", "n_ai", "sessions_ai", "largest_ai", "largest_ai_share_pct", "indicative"],
                long_rows)
    head = ["window_s", "top20_rank", "feature", "merged_members", "tier", "in_main_configuration", "higher_in",
            "auc_all", "n_human", "n_ai"]
    per_g = ["auc", "auc_dir", "higher_in", "n_human", "sessions_human", "largest_human", "largest_human_share",
             "n_ai", "sessions_ai", "largest_ai", "largest_ai_share", "indicative"]
    for g in E.STAGE_GROUPS:
        head += ["%s_%s" % (GROUP_KEY[g], k) for k in per_g]
    head += ["eps2_human", "eps2_human_groups", "eps2_human_n", "eps2_ai", "eps2_ai_groups", "eps2_ai_n"]
    t7 = []
    for p in top:
        row = [seconds, p["top_rank"], p["column"], " ".join(members.get(p["column"], [])), p["tier"], yn(p["in_main"]),
               p["higher_in"], C.f4(p["auc"]), p["defined_human"], p["defined_ai"]]
        for g in E.STAGE_GROUPS:
            s = stage[p["column"]][g]
            row += [C.f4(s["auc"]), C.f4(s["auc_dir"]), s["higher_in"], s["n_human"], s["sessions_human"],
                    s["largest_human"], s["largest_human_share"], s["n_ai"], s["sessions_ai"], s["largest_ai"],
                    s["largest_ai_share"], s["indicative"]]
        for cls in E.CLASSES:
            e2, used, n = C.epsilon2(rows, p["column"], cls)
            row += [C.f4(e2), " ".join(used), n]
        t7.append(row)
    E.write_csv("T7_top20_by_stage_%s.csv" % wl, head, t7)

    qualifies = [g for g in E.STAGE_GROUPS if min(counts[("human", g)]["n"], counts[("ai", g)]["n"]) >= C.MIN_WINDOWS]
    E.write_csv("T7_stage_group_training_windows_%s.csv" % wl,
                ["window_s", "class", "stage_group", "training_windows", "sessions", "largest_session",
                 "largest_session_windows", "largest_session_share_pct", "at_least_10_in_both_classes"],
                [[seconds, cls, g, counts[(cls, g)]["n"], counts[(cls, g)]["sessions"], counts[(cls, g)]["largest"],
                  counts[(cls, g)]["largest_n"], counts[(cls, g)]["largest_share"], yn(g in qualifies)]
                 for cls in E.CLASSES for g in E.STAGE_GROUPS])

    # T8
    sets = [(t, [p for p in ranked if p["tier"] == t]) for t in C.TIERS]
    sets.append(("main_configuration", [p for p in ranked if p["in_main"]]))
    sets.append(("all_columns", list(ranked)))
    t8 = []
    for name, ps in sets:
        with_auc = [p for p in ps if p["auc"] is not None]
        t8.append([seconds, name, len(ps), "all", counts_class(rows, "human"), n_sessions(rows, "human"),
                   counts_class(rows, "ai"), n_sessions(rows, "ai"), len(with_auc), C.f4(mean(p["auc"] for p in with_auc)),
                   C.f4(mean(p["auc"] for p in with_auc)), C.f4(mean(p["auc"] for p in with_auc)), 0])
        for g in qualifies:
            have = [p for p in ps if stage[p["column"]][g]["auc"] is not None]
            t8.append([seconds, name, len(ps), g, counts[("human", g)]["n"], counts[("human", g)]["sessions"],
                       counts[("ai", g)]["n"], counts[("ai", g)]["sessions"], len(have),
                       C.f4(mean(stage[p["column"]][g]["auc"] for p in have)),
                       C.f4(mean(stage[p["column"]][g]["auc_dir"] for p in have)),
                       C.f4(mean(p["auc"] for p in have)),
                       sum(1 for p in have if stage[p["column"]][g]["indicative"] == "yes")])
    E.write_csv("T8_tier_means_%s.csv" % wl,
                ["window_s", "tier", "columns", "scope", "human_windows", "human_sessions", "ai_windows", "ai_sessions",
                 "columns_with_auc", "mean_auc", "mean_auc_in_all_rows_direction", "mean_auc_all_rows_same_columns",
                 "columns_indicative"], t8)

    log["summary"][wl] = {
        "training_rows": {"human": counts_class(rows, "human"), "ai": counts_class(rows, "ai")},
        "columns": len(cols), "columns_with_auc": sum(1 for p in ranked if p["auc"] is not None),
        "flagged_all_rows": [p["column"] for p in ranked if p["flag_all_rows"]],
        "flagged_only_with_a_session_left_out": [p["column"] for p in flagged if not p["flag_all_rows"]],
        "near_duplicate_links": len(links),
        "top20": [p["column"] for p in top],
        "stage_groups_with_10_in_both_classes": qualifies,
        "highest_auc": [[p["column"], round(p["auc"], 4)] for p in ranked[:3]],
        "highest_indicator_auc": sorted([[p["column"], round(p["ind_auc"], 4)] for p in ranked], key=lambda t: -t[1])[:3],
    }
    return rows, cols, ranked, top, rho, counts, stage


def counts_class(rows, cls):
    return sum(1 for r in rows if r["class"] == cls)


def n_sessions(rows, cls):
    return len(set(r["session"] for r in rows if r["class"] == cls))


# ------------------------------------------------------------------------------------- T9
def range_tables(rows, ranked, sessions):
    by_range = collections.defaultdict(list)
    for s in sessions:
        by_range[(s["class"], s["lab_range"])].append(s["session"])
    E.write_csv("T9_range_groups.csv", ["class", "lab_range", "sessions", "training_windows"],
                [[cls, rg, " ".join(by_range[(cls, rg)]),
                  sum(1 for r in rows if r["class"] == cls and r["lab_range"] == rg)]
                 for cls in E.CLASSES for rg in C.RANGES])
    res = {}
    for key, cls, first, second in RANGE_COMPARISONS:
        for p in ranked:
            va = C.values(rows, p["column"], cls, lambda r: r["lab_range"] == first)
            vb = C.values(rows, p["column"], cls, lambda r: r["lab_range"] == second)
            a = C.a_stat(va, vb)
            res[(key, p["column"])] = {"a": a, "auc": C.auc_of(a), "n1": len(va), "n2": len(vb),
                                       "higher": "" if a is None else (first if a >= 0.5 else second)}
    head = ["feature", "tier", "in_main_configuration", "class_auc_30s"]
    for key, _, _, _ in RANGE_COMPARISONS:
        head += [key + "_auc", key + "_higher_in", key + "_n_first", key + "_n_second"]
    out = []
    for p in sorted(ranked, key=lambda p: p["order"]):
        row = [p["column"], p["tier"], "yes" if p["in_main"] else "no", C.f4(p["auc"])]
        for key, _, _, _ in RANGE_COMPARISONS:
            r = res[(key, p["column"])]
            row += [C.f4(r["auc"]), r["higher"], r["n1"], r["n2"]]
        out.append(row)
    E.write_csv("T9_range_check.csv", head, out)
    summ = []
    for name, kh, ka in RANGE_PAIRS:
        both = [p["column"] for p in ranked if res[(kh, p["column"])]["a"] is not None and res[(ka, p["column"])]["a"] is not None]
        sh = [res[(kh, c)]["a"] - 0.5 for c in both]
        sa = [res[(ka, c)]["a"] - 0.5 for c in both]
        rho = float(C.sps.spearmanr(sh, sa).statistic) if len(both) >= 3 else None
        top_h = sorted(both, key=lambda c: -res[(kh, c)]["auc"])[:10]
        top_a = sorted(both, key=lambda c: -res[(ka, c)]["auc"])[:10]
        shared = [c for c in top_h if c in top_a]
        same = [c for c in shared if res[(kh, c)]["higher"] == res[(ka, c)]["higher"]]
        summ.append([name, len(both), C.f4(rho), len(shared), len(same), " ".join(shared), " ".join(same),
                     " ".join(top_h), " ".join(top_a)])
    E.write_csv("T9_range_check_summary.csv",
                ["comparison", "features_with_auc_in_both_classes", "spearman_rho_of_signed_auc_between_classes",
                 "top10_shared", "top10_shared_same_direction", "shared_features", "shared_same_direction",
                 "top10_human", "top10_ai"], summ)


# ------------------------------------------------------------------------------------- main
def main():
    inp = C.Inputs2(C.pass2_inputs())
    sessions, _ = E.session_table(inp)
    checks = []

    def check(name, expected, found):
        checks.append({"check": name, "expected": expected, "found": found, "ok": expected == found})

    review_path = os.path.join(C.HERE, "pass2_review_notes.json")
    review = E.read_json_file(review_path) if os.path.exists(review_path) else {}
    log = {"pass": "EDA Pass 2 (tables)", "eda_version": E.EDA_VERSION, "pass2_version": C.PASS2_VERSION,
           "run_after_the_trials_as_a_report_only": "handoff 12a; F16 of the feature and trial design",
           "freeze_1_sha256": inp.freeze_sha256, "freeze_2_sha256": inp.freeze2_sha256,
           "training_rows": {}, "summary": {}, "figure_tables": {}}

    # 30 s: every table
    rows, cols, ranked, top, rho, counts, stage = tables_for(inp, "w30", 30, sessions, check, log, review)
    range_tables(rows, ranked, sessions)

    cmds, cmd_log = C.load_training_commands(inp, "w30", rows)
    log["figure_tables"]["per_command"] = cmd_log
    check("w30 commands in the per-command table against cmd_count",
          int(sum(r["x"]["cmd_count"] for r in rows)), len(cmds))
    log["figure_tables"]["E7_window_types"] = activity_tables(rows, cmds)
    check("E7 windows human", counts_class(rows, "human"), sum(log["figure_tables"]["E7_window_types"]["human"].values()))
    check("E7 windows ai", counts_class(rows, "ai"), sum(log["figure_tables"]["E7_window_types"]["ai"].values()))
    log["figure_tables"]["E8_programs"] = program_tables(rows, cmds, counts)
    log["figure_tables"]["E5_class_commands"] = machine_tables(rows, cmds, sessions)
    cross, win_stats = scan_training_windows(inp, "w30", rows)
    log["figure_tables"]["E5_machine_list_crosscheck"] = cross
    log["figure_tables"]["T5_review_input_records"] = review_table(rows, cmds, sessions, win_stats, 30)
    for r in rows:                      # the recomputed input-record count equals the feature built from it
        if r["x"]["cmd_count"] > 0:
            check("input records per command, window %s" % r["window_id"],
                  round(win_stats[r["window_id"]]["input_records"] / r["x"]["cmd_count"], 4),
                  round(r["x"]["input_writes_per_cmd"], 4))

    # E9: Spearman among the top 20; E11: values of the top 12
    e9 = []
    for i, p in enumerate(top):
        for q in top[:i]:
            r, n = rho(p["column"], q["column"])
            e9.append([p["top_rank"], p["column"], q["top_rank"], q["column"], C.f4(r), n])
    E.write_csv("E9_spearman_top20.csv", ["rank_a", "feature_a", "rank_b", "feature_b", "spearman_rho", "rows_both_defined"], e9)
    pts, med = [], []
    for p in top[:12]:
        for r in rows:
            v = r["x"][p["column"]]
            if v is not None:
                pts.append([p["top_rank"], p["column"], r["class"], r["session"], C.g6(v)])
        for s in sessions:
            v = C.values(rows, p["column"], keep=lambda r, s=s: r["session"] == s["session"])
            med.append([p["top_rank"], p["column"], p["kind"], s["class"], s["session"], len(v),
                        C.g6(float(np.median(v))) if v else ""])
    E.write_csv("E11_points.csv", ["top20_rank", "feature", "class", "session", "value"], pts)
    E.write_csv("E11_session_medians.csv", ["top20_rank", "feature", "kind", "class", "session", "defined_windows", "median"], med)

    # E1: data example (to be read by a person before use)
    e1_log = {}
    e1_example(inp, "w30", rows, cmds, top[:6], e1_log)
    log["figure_tables"].update(e1_log)

    # E2 overview with the two Pass 2 lines filled in (the Pass 1 table is frozen and is not rewritten)
    rep10 = inp.read_json("reports/10_features_report.json")
    undefined_cols = sum(1 for c, v in rep10["w30"]["undefined_share_by_session"].items() if any(float(x) > 0 for x in v.values()))
    tiers = rep10["tiers"]
    check("tier counts in the column file against the feature report",
          {t: sum(1 for c in cols if c["tier"] == t) for t in C.TIERS}, {t: tiers[t] for t in C.TIERS})
    check("columns undefined in some training row are among those undefined in some kept window", True,
          set(p["column"] for p in ranked if min(p["defined_share_human"], p["defined_share_ai"]) < 1.0)
          <= set(rep10["w30"]["undefined_share_by_session"]))
    ov = []
    for r in inp.read_csv("reports/eda/tables/E2_overview.csv", ["item", "human", "ai", "all", "note"]):
        if r["item"] == "feature_columns_by_tier":
            r = {"item": r["item"], "human": "", "ai": "", "all": str(len(cols)),
                 "note": "; ".join("%s %d" % (C.TIER_LABEL[t].lower(), tiers[t]) for t in C.TIERS)}
        elif r["item"] == "columns_with_undefined_values":
            r = {"item": r["item"], "human": "", "ai": "", "all": str(undefined_cols),
                 "note": "columns undefined in at least one kept window, from the feature step's report; "
                         "%d of %d are never undefined" % (len(cols) - undefined_cols, len(cols))}
        ov.append([r["item"], r["human"], r["ai"], r["all"], r["note"]])
    E.write_csv("E2_overview_pass2.csv", ["item", "human", "ai", "all", "note"], ov)

    # 60 s: T4 to T8 as tables only
    tables_for(inp, "w60", 60, sessions, check, log, review)
    E.write_csv("T5_review_windows_by_session.csv",
                ["window_s", "class", "session", "training_windows", "windows_with_a_command",
                 "windows_without_a_command", "with_a_whole_line_command", "with_compose_time_0",
                 "at_or_under_one_input_record_per_command"], REVIEW_ROWS)

    failed = [c for c in checks if not c["ok"]]
    log["checks_run"] = len(checks)
    log["checks_failed"] = len(failed)
    log["checks"] = checks
    log["inputs_opened"] = dict(sorted(inp.opened.items()))
    log["never_opened"] = "the evidence folder, set_aside/, the private key map, the test-label files, " \
                          "the train and validation label files, results/"
    E.write_json(os.path.join(E.OUT, "pass2_tables_log.json"), log)
    if failed:
        for c in failed:
            print("CHECK FAILED:", c)
        raise SystemExit("STOP: %d Pass 2 count checks failed" % len(failed))
    print("COMPLETE: Pass 2 tables; checks", len(checks), "failed 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
