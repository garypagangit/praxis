"""Step 4: command reconstruction, validator commands, final cleaned files
(design sections 6.4, 6.6, 6.7; A4, A6, A7, A14, A15).

For every login used:
  1. reconstruct the commands from the cleaned recorder records (s3_commands)
  2. find the validator commands: the command that made each validator call
     (audit marker), and any command whose program is goad-apt29* or goad-challenge
  3. remove each of them with its keystrokes, its echo, its output and the
     prompt that followed, so the stream reads as if it had not been typed
  4. replace validator-family names left in kept text with 'validator' (A6)
  5. reconstruct again on the final stream: this is the command list in data/

Writes data/cleaned/, data/commands/, the ledger rows, the list of removed
validator commands for review, and reports/04_commands_report.json.
"""
import base64
import bisect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_clean as K
import s3_commands as M
import s3_config as C
import s3_io as IO
import s3_term as T
import step02_route as R

STEP = "04_commands"


def load_recs(path):
    outers = []
    recs = []
    for line in open(path, encoding="utf-8"):
        outer = json.loads(line)
        msg = json.loads(outer["message"])
        shown = outer.pop("_shown", None)
        outers.append((outer, msg))
        rec = dict(kind=msg["kind"], t=M.epoch(msg["time"]),
                   data=base64.b64decode(msg["data_base64"]) if "data_base64" in msg else b"")
        if shown is not None:
            rec["shown"] = base64.b64decode(shown)
        recs.append(rec)
    return outers, recs


def scrub_text(text):
    return _scrub_text(text)


def _scrub_text(text):
    """Identity, scratch-directory and validator-name rules on a command text
    that was read from the screen. Returns (text, identity was found)."""
    c = {}
    b = K.scrub_identity_bytes(text.encode("utf-8"), c, bare_uid=True)
    for rx, rep in K.RE_SCRATCH + K.TOOLING_TEXT_RULES:
        b = rx.sub(rep, b)
    return b.decode("utf-8", "replace"), bool(c)


def name_text(text):
    b = text.encode("utf-8")
    for rx, rep in K.VALIDATOR_NAME_RULES:
        b = rx.sub(rep, b)
    return b.decode("utf-8", "replace")


def mark_validator(cmds, markers):
    """Which commands called the validator. Returns {command index: rule}, stats."""
    res = {}
    st = dict(markers=len(markers), marker_within_15s=0, marker_in_running_command=0, marker_unmatched=0)
    enters = [c["t_enter"] for c in cmds]
    for tm in sorted(markers):
        j = bisect.bisect_right(enters, tm + 0.05) - 1
        if j >= 0 and tm - enters[j] <= C.VALIDATOR_MARKER_LOOKBACK_S:
            res.setdefault(j, "marker_within_15s")
            st["marker_within_15s"] += 1
            continue
        k = j
        found = None
        while k >= 0:
            c = cmds[k]
            if c["at_prompt"]:
                if c["t_prompt"] is None or c["t_prompt"] > tm:
                    found = k
                break
            k -= 1
        if found is not None:
            res.setdefault(found, "marker_in_running_command")
            st["marker_in_running_command"] += 1
        else:
            st["marker_unmatched"] += 1
    for j, c in enumerate(cmds):
        if j not in res and K.RE_VALIDATOR_PROGRAM.match(c["program"]):
            res[j] = "program_name"
    st["removed_by_marker_within_15s"] = sum(1 for v in res.values() if v == "marker_within_15s")
    st["removed_by_running_command"] = sum(1 for v in res.values() if v == "marker_in_running_command")
    st["removed_by_program_name"] = sum(1 for v in res.values() if v == "program_name")
    return res, st


def paste_marker_check(out, prompts):
    """A15 cross-check 2: the shell's paste-mode marker against the prompt."""
    marks = []
    pos = 0
    while True:
        i = out.find(b"\x1b[?2004h", pos)
        if i < 0:
            break
        marks.append(i)
        pos = i + 1
    begins = {a for a, b in prompts}
    at_prompt = sum(1 for m in marks if m in begins)
    return dict(paste_mode_markers=len(marks), markers_at_a_shell_prompt=at_prompt,
                markers_elsewhere=len(marks) - at_prompt,
                shell_prompts=len(prompts), shell_prompts_without_marker=len(prompts) - at_prompt)


def process_login(sess, login):
    meta = IO.read_json(IO.work(sess, "a_%s.meta.json" % login))
    rec_path = IO.work(sess, "a_%s.rec.jsonl" % login)
    aud_path = IO.work(sess, "a_%s.aud.jsonl" % login)
    if IO.sha256_file(rec_path)[0] != meta["rec_sha256"] or IO.sha256_file(aud_path)[0] != meta["aud_sha256"]:
        raise SystemExit("%s %s: step 3 output changed" % (sess, login))
    outers, recs = load_recs(rec_path)
    st = {}
    led = []
    # ---- pass 1
    r1 = M.Reconstruction(recs)
    st["screen_texts_identity_scrubbed"] = 0
    for c in r1.commands:
        if c["source"] == "screen":
            c["text"], hit = scrub_text(c["text"])
            st["screen_texts_identity_scrubbed"] += int(hit)
            c["program"] = M.program_name(c["text"])
            c["is_exit"] = c["text"].strip() in ("exit", "logout")
    val, vst = mark_validator(r1.commands, meta["markers"])
    st["validator"] = vst
    st["pass1_commands"] = len(r1.commands)
    st["paste_marker_check"] = paste_marker_check(r1.out, r1.prompts)
    removed = []
    idx_in, idx_out = r1.idx_in, r1.idx_out
    seg_in = K.SegStream([recs[i]["data"] for i in idx_in])
    seg_out = K.SegStream([recs[i]["data"] for i in idx_out])
    in_pos = {i: k for k, i in enumerate(idx_in)}
    spans_in, spans_out = [], []
    t0 = recs[0]["t"]
    for j in sorted(val):
        c = r1.commands[j]
        for (ri, a, b) in c["ranges"]:
            base = seg_in.start_of(in_pos[ri])
            spans_in.append((base + a, base + b, b""))
        a = r1.out_off(c["rec_first"])
        if c["ended_by"] == "prompt":
            b = c["prompt_end"]
        elif c["at_prompt"] and c["next_prompt_end"] is not None:
            # a key was pressed while the validator call was still printing: the cut
            # still runs to the prompt that closes the call
            b = c["next_prompt_end"]
            st["validator_cut_extended_to_prompt"] = st.get("validator_cut_extended_to_prompt", 0) + 1
        else:
            b = c["out_end"]
        if b > a:
            spans_out.append((a, b, b""))
        removed.append(dict(session=sess, login=login, t=round(c["t_enter"] - t0, 3), rule=val[j],
                            at_prompt=c["at_prompt"], text_source=c["source"], ended_by=c["ended_by"],
                            output_bytes=c["out_raw_bytes"], text=c["text"]))

    def merge(spans):
        spans.sort()
        out = []
        for a, b, r in spans:
            if out and a < out[-1][1]:
                out[-1] = (out[-1][0], max(out[-1][1], b), b"")
            else:
                out.append((a, b, r))
        return out
    seg_in.replace_spans(merge(spans_in))
    seg_out.replace_spans(merge(spans_out))
    st["validator_commands_removed"] = len(removed)
    st["validator_input_bytes_removed"] = sum(b - a for a, b, _ in merge(spans_in))
    st["validator_output_bytes_removed"] = sum(b - a for a, b, _ in merge(spans_out))
    # ---- A6: validator-family names left in kept text
    n_names = 0
    for rx, rep in K.VALIDATOR_NAME_RULES:
        n_names += seg_in.sub(rx, rep) + seg_out.sub(rx, rep)
    st["validator_names_replaced"] = n_names
    # ---- final records
    new_in, new_out = seg_in.chunks(), seg_out.chunks()
    data_of = {}
    for k, i in enumerate(idx_in):
        data_of[i] = new_in[k]
    for k, i in enumerate(idx_out):
        data_of[i] = new_out[k]
    final_outers, final_recs = [], []
    st["records_emptied_dropped"] = 0
    for i, (outer, msg) in enumerate(outers):
        if i in data_of:
            if not data_of[i] and recs[i]["data"]:
                led.append((outer["eventId"], STEP, "validator_command", ""))
                st["records_emptied_dropped"] += 1
                continue
            msg["data_base64"] = base64.b64encode(data_of[i]).decode()
            outer["message"] = IO.dumps(msg)
        final_outers.append(outer)
        final_recs.append(dict(kind=msg["kind"], t=recs[i]["t"], data=data_of.get(i, b"")))
    # ---- pass 2: the command list
    r2 = M.Reconstruction(final_recs)
    # screen-read text comes from pass 1, where the screen was replayed as it was shown
    kept1 = {round(c["t_enter"], 6): c for j, c in enumerate(r1.commands) if j not in val}
    st["pass2_commands_not_in_pass1"] = 0
    # leak check by replay: identity that only shows once the final stream is replayed on a screen
    st["identity_after_replay_of_final_stream"] = sum(
        1 for c in r2.commands if scrub_text(c["text"])[1])
    for c in r2.commands:
        c1 = kept1.get(round(c["t_enter"], 6))
        if c1 is None:
            st["pass2_commands_not_in_pass1"] += 1
            continue
        if c1["source"] == "screen" or c["source"] == "screen":
            c["text"], c["source"] = c1["text"], c1["source"]
        c["text"] = name_text(c["text"])
        c["program"] = M.program_name(c["text"])
        c["is_exit"] = c["text"].strip() in ("exit", "logout")
    left = [c for c in r2.commands if K.RE_VALIDATOR_PROGRAM.match(c["program"])]
    st["pass2_commands"] = len(r2.commands)
    st["pass2_validator_programs_left"] = len(left)
    st["pass2_matches_pass1"] = (len(r2.commands) == len(r1.commands) - len(removed))
    st["reconstruction"] = r2.stats
    st["terminal_widths_found"] = sorted({w for _, w in r2.widths})
    st["text_source"] = {}
    st["ended_by"] = {}
    for c in r2.commands:
        st["text_source"][c["source"]] = st["text_source"].get(c["source"], 0) + 1
        st["ended_by"][c["ended_by"]] = st["ended_by"].get(c["ended_by"], 0) + 1
    st["commands_at_shell_prompt"] = sum(1 for c in r2.commands if c["at_prompt"])
    st["commands_typed_into_a_program"] = sum(1 for c in r2.commands if not c["at_prompt"])
    st["exit_lines"] = sum(1 for c in r2.commands if c["is_exit"])
    st["closing_exit"] = bool(r2.commands and r2.commands[-1]["closing_exit"])
    st["output_bytes_by_command"] = sum(c["out_raw_bytes"] for c in r2.commands)
    st["output_bytes_total"] = r2.out_len
    lk = IO.login_key(login)
    cmd_rows = []
    for n, c in enumerate(r2.commands):
        ob = r2.rec_of_out(c["out_begin"])
        oe = r2.rec_of_out(max(c["out_begin"], c["out_end"] - 1)) if c["out_end"] > c["out_begin"] else ob
        cmd_rows.append(dict(
            login_key=lk, n=n, t_enter=round(c["t_enter"] - t0, 6),
            t_first_key=round((c["t_first"] if c["t_first"] is not None else c["t_enter"]) - t0, 6),
            text=c["text"], text_source=c["source"], program=c["program"], lines=c["n_lines"],
            at_prompt=c["at_prompt"], is_exit=c["is_exit"], closing_exit=c["closing_exit"],
            one_write=c["one_write"], input_records=c["in_records"], typed_chars=c["typed"],
            pasted_chars=c["pasted"], backspaces=c["backspaces"], has_history_key=c["history"],
            has_tab=c["tab"], has_cursor_key=c["cursor"], has_paste=c["paste"], has_other_edit_key=c["edit"],
            in_first=c["rec_first"], in_enter=c["rec_enter"],
            out_begin=[ob[0], ob[1]], out_end=[oe[0], oe[1] + (1 if c["out_end"] > c["out_begin"] else 0)],
            out_raw_bytes=c["out_raw_bytes"], out_text_bytes=c["out_text_bytes"],
            ended_by=c["ended_by"], t_out_end=round(c["t_out_end"] - t0, 6)))
    return final_outers, cmd_rows, removed, led, st, r2.disagreements


def main():
    rep = dict(step=STEP, code_version=C.CODE_VERSION, prompt_pattern=T.PROMPT_RE.pattern, sessions={})
    all_removed = []
    for sess in C.SESSION_ORDER:
        res = IO.read_json(IO.work(sess, "clean_a.json"))
        if res is None:
            raise SystemExit("%s: run step 3 first" % sess)
        R.ledger_reset(sess, STEP)
        sk = IO.session_key(sess)
        rs = dict(logins={}, session_key=sk)
        tot = dict(commands=0, removed=0, screen=0, fallback=0, keys=0, agree=0, plain_shell=0, unmatched=0)
        for login in sorted(res["logins"]):
            lk = IO.login_key(login)
            final_outers, cmd_rows, removed, led, st, dis = process_login(sess, login)
            # final cleaned files: recorder from this step, audit from step 3
            rec_out = IO.out("data", "cleaned", sk, lk + ".recorder.jsonl")
            with open(rec_out, "w", encoding="utf-8") as f:
                for o in final_outers:
                    f.write(IO.dumps(o) + "\n")
            aud_out = IO.out("data", "cleaned", sk, lk + ".audit.jsonl")
            with open(aud_out, "wb") as f:
                f.write(open(IO.work(sess, "a_%s.aud.jsonl" % login), "rb").read())
            cmd_out = IO.out("data", "commands", sk, lk + ".commands.jsonl")
            with open(cmd_out, "w", encoding="utf-8") as f:
                for row in cmd_rows:
                    f.write(IO.dumps(row) + "\n")
            R.ledger_append(sess, led)
            st["recorder_records_out"] = len(final_outers)
            st["plain_line_disagreements"] = dis
            rs["logins"][login] = dict(
                login_key=lk, stats=st,
                input_sha256=dict(recorder=res["logins"][login]["rec_sha256"], audit=res["logins"][login]["aud_sha256"]),
                output_sha256=dict(recorder=IO.sha256_file(rec_out)[0], audit=IO.sha256_file(aud_out)[0],
                                   commands=IO.sha256_file(cmd_out)[0]))
            all_removed.extend(removed)
            tot["commands"] += len(cmd_rows)
            tot["removed"] += len(removed)
            for k in ("screen", "keys"):
                tot[k] += st["text_source"].get(k, 0)
            tot["fallback"] += st["text_source"].get("keys_fallback", 0)
            tot["agree"] += st["reconstruction"]["plain_shell_agree"]
            tot["plain_shell"] += st["reconstruction"]["plain_shell_lines"]
            tot["unmatched"] += st["validator"]["marker_unmatched"]
        rs["totals"] = tot
        rep["sessions"][sess] = rs
        print(sess, json.dumps(tot))
    IO.write_json(IO.out("reports", "04_commands_report.json"), rep)
    with open(IO.out("reports", "04_removed_validator_commands.jsonl"), "w", encoding="utf-8") as f:
        for r in all_removed:
            f.write(IO.dumps(r) + "\n")
    print("COMPLETE: commands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
