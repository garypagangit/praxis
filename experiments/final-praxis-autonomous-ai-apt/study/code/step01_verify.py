"""Step 1: verify first (design section 3).

Before anything is read, every file listed in each package's manifest is checked
against its recorded size and SHA-256:
  - parts against PARTS_MANIFEST.json, and the rebuilt archive (read in place)  (A1)
  - for a split delivery: files against the checksum manifest, the parts of
    context.zip against that manifest's part entries, the contents of each zip
    against the zip's own manifest, the record count against COMPLETE.json    (A9)
  - for a whole zip: every member against the zip's manifest.json
The run stops on any mismatch. Result: reports/01_verification_report.json.

Runs in slices (python3 step01_verify.py, repeat until it prints COMPLETE).
"""
import concurrent.futures as cf
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # allows python3 -I
import s3_config as C
import s3_io as IO

STATE = "01_verify_state.json"


def _zip_manifest(paths):
    with IO.open_zip(paths) as zf:
        names = {i.filename: i.file_size for i in zf.infolist() if not i.is_dir()}
        man = json.loads(zf.read("manifest.json")) if "manifest.json" in names else None
    return names, man


def build_items():
    """List every check to make. Each item is independent and small enough to
    finish inside one slice."""
    items = []

    def add(**k):
        k["id"] = "%s|%s|%s|%s" % (k["session"], k["kind"], k.get("archive", ""), k["name"])
        items.append(k)

    def zip_members(sess, label, paths):
        names, man = _zip_manifest(paths)
        if man is None:
            raise SystemExit("%s: %s has no manifest.json" % (sess, label))
        listed = man["files"]
        for name, meta in sorted(listed.items()):
            if name in names:
                add(session=sess, kind="member", archive=label, paths=paths, name=name,
                    exp_bytes=meta["bytes"], exp_sha=meta["sha256"], size=meta["bytes"])
            else:
                add(session=sess, kind="listed_not_held", archive=label, paths=paths, name=name,
                    exp_bytes=meta["bytes"], exp_sha=meta["sha256"], size=0)
        for name in sorted(set(names) - set(listed)):
            add(session=sess, kind="not_listed", archive=label, paths=paths, name=name,
                size=names[name])
        return man

    for sess in C.SESSION_ORDER:
        cfg = C.SESSIONS[sess]
        lay = cfg["layout"]
        if lay == "zip":
            p = [IO.ev(cfg["main"])]
            add(session=sess, kind="outer", archive="main", paths=p, name=os.path.basename(p[0]),
                size=os.path.getsize(p[0]))
            man = zip_members(sess, "main", p)
            add(session=sess, kind="count", archive="main", name="raw_events", expected=man["raw_events"], size=0)
            if cfg.get("parts_manifest"):
                pm = json.load(open(IO.ev(cfg["parts_manifest"])))
                pm = pm if isinstance(pm, list) else [pm]
                folder = os.path.dirname(IO.ev(cfg["parts_manifest"]))
                for arch in pm:
                    nm = arch.get("original_name") or arch.get("original")
                    pp = IO.part_paths(folder, nm)
                    if len(pp) != len(arch["parts"]):
                        raise SystemExit("%s: %s has %d parts on disk, manifest lists %d" % (sess, nm, len(pp), len(arch["parts"])))
                    for path, pe in zip(pp, arch["parts"]):
                        add(session=sess, kind="part", archive=nm, paths=[path], name=pe["name"],
                            exp_bytes=pe["bytes"], exp_sha=pe["sha256"], size=pe["bytes"],
                            on_disk=os.path.basename(path))
                    add(session=sess, kind="rebuilt", archive=nm, paths=pp, name=nm,
                        exp_bytes=arch["bytes"], exp_sha=arch["sha256"], size=arch["bytes"])
        elif lay == "parts":
            folder = IO.ev(cfg["folder"])
            pm = json.load(open(os.path.join(folder, "PARTS_MANIFEST.json")))
            pm = pm if isinstance(pm, list) else [pm]
            for arch in pm:
                nm = arch.get("original_name") or arch.get("original")
                pp = IO.part_paths(folder, nm)
                if len(pp) != len(arch["parts"]):
                    raise SystemExit("%s: %s has %d parts on disk, manifest lists %d" % (sess, nm, len(pp), len(arch["parts"])))
                for path, pe in zip(pp, arch["parts"]):
                    add(session=sess, kind="part", archive=nm, paths=[path], name=pe["name"],
                        exp_bytes=pe["bytes"], exp_sha=pe["sha256"], size=pe["bytes"],
                        on_disk=os.path.basename(path))
                add(session=sess, kind="rebuilt", archive=nm, paths=pp, name=nm,
                    exp_bytes=arch["bytes"], exp_sha=arch["sha256"], size=arch["bytes"])
            p = IO.part_paths(folder, cfg["main_name"])
            man = zip_members(sess, "main", p)
            add(session=sess, kind="count", archive="main", name="raw_events", expected=man["raw_events"], size=0)
        elif lay == "split":
            folder = IO.ev(cfg["folder"])
            cm = json.load(open(os.path.join(folder, cfg["checksum_manifest"])))
            comp = json.load(open(os.path.join(folder, "COMPLETE.json")))
            comp_by_file = {p_["file"]: p_ for p_ in comp["partitions"]}
            for fe in cm["files"]:
                nm = fe["name"]
                if "parts" in fe:
                    pp = IO.part_paths(folder, nm)
                    if len(pp) != len(fe["parts"]):
                        raise SystemExit("%s: %s has %d parts on disk, manifest lists %d" % (sess, nm, len(pp), len(fe["parts"])))
                    for path, pe in zip(pp, sorted(fe["parts"], key=lambda x: x["order"])):
                        add(session=sess, kind="part", archive=nm, paths=[path],
                            name="%s.part%03d" % (nm, pe["order"]),
                            exp_bytes=pe["bytes"], exp_sha=pe["sha256"], size=pe["bytes"],
                            on_disk=os.path.basename(path))
                    add(session=sess, kind="rebuilt", archive=nm, paths=pp, name=nm,
                        exp_bytes=fe["bytes"], exp_sha=fe["sha256"], size=fe["bytes"])
                    paths = pp
                else:
                    paths = [os.path.join(folder, nm)]
                    add(session=sess, kind="file", archive="checksum_manifest", paths=paths, name=nm,
                        exp_bytes=fe["bytes"], exp_sha=fe["sha256"], size=fe["bytes"])
                if nm in comp_by_file and comp_by_file[nm]["sha256"] != fe["sha256"]:
                    raise SystemExit("%s: COMPLETE.json hash of %s differs from the checksum manifest" % (sess, nm))
                if nm.endswith(".zip"):
                    man = zip_members(sess, nm, paths)
                    if nm in comp_by_file:
                        add(session=sess, kind="count", archive=nm, name="events",
                            expected=comp_by_file[nm]["events"], manifest_events=man.get("events"), size=0)
            missing = [f for f in comp_by_file if f not in {fe["name"] for fe in cm["files"]}]
            if missing:
                raise SystemExit("%s: COMPLETE.json lists files absent from the checksum manifest: %s" % (sess, missing))
            add(session=sess, kind="total", archive="COMPLETE.json", name="total_events",
                expected=comp["total_events"], partitions=sorted(comp_by_file), size=0)
            if comp["total_events"] != sum(p_["events"] for p_ in comp["partitions"]):
                raise SystemExit("%s: COMPLETE.json partitions do not add up to its total" % sess)
        if C.EXPECTED_RAW[sess] is None:
            raise SystemExit("no expected total for " + sess)
    return items


def do_item(it):
    """Hash one file, one rebuilt archive or one zip member. Returns the result."""
    k = it["kind"]
    if k in ("outer", "file", "part"):
        sha, n = IO.sha256_file(it["paths"][0])
        return dict(sha256=sha, bytes=n)
    if k == "rebuilt":
        f = IO.open_binary(it["paths"])
        try:
            sha, n, _ = IO.sha256_stream(f)
        finally:
            f.close()
        return dict(sha256=sha, bytes=n)
    if k == "member":
        with IO.open_zip(it["paths"]) as zf:
            with zf.open(it["name"]) as f:                 # zipfile also checks the CRC
                sha, n, lines = IO.sha256_stream(f, count_lines=it["name"].endswith(".jsonl"))
        return dict(sha256=sha, bytes=n, lines=lines)
    return {}


def main():
    budget = IO.Budget()
    state_path = IO.work(STATE)
    state = IO.read_json(state_path, {})
    items = build_items()
    todo = [it for it in items if it["kind"] in ("outer", "file", "part", "rebuilt", "member")
            and it["id"] not in state]
    todo.sort(key=lambda it: -it["size"])
    RATE = 120e6       # bytes per second per worker, conservative (measured about 300-500e6)
    with cf.ProcessPoolExecutor(max_workers=4) as ex:
        pending = {}
        queue = list(todo)
        while queue or pending:
            while queue and len(pending) < 4:
                # do not start an item that cannot finish inside this slice
                pick = None
                for i, it in enumerate(queue):
                    if it["size"] / RATE < budget.left() - 5:
                        pick = i
                        break
                if pick is None:
                    queue = []
                    break
                it = queue.pop(pick)
                pending[ex.submit(do_item, it)] = it
            if not pending:
                break
            done, _ = cf.wait(list(pending), return_when=cf.FIRST_COMPLETED)
            for fu in done:
                it = pending.pop(fu)
                state[it["id"]] = fu.result()
            IO.write_json(state_path, state)
    left = [it for it in items if it["kind"] in ("outer", "file", "part", "rebuilt", "member")
            and it["id"] not in state]
    if left:
        print("INCOMPLETE: %d of %d hash checks still to run; run again" % (len(left), len(todo) + 0))
        return 2

    # ---------------------------------------------------------------- report
    report = dict(step="01_verify", code_version=C.CODE_VERSION, sessions={}, mismatches=[])
    for sess in C.SESSION_ORDER:
        rs = dict(layout=C.SESSIONS[sess]["layout"], checks=[], summary={})
        lines_by_archive = {}
        for it in items:
            if it["session"] != sess:
                continue
            res = state.get(it["id"], {})
            row = dict(kind=it["kind"], archive=it.get("archive", ""), name=it["name"])
            if it["kind"] in ("file", "part", "rebuilt", "member"):
                ok = (res["sha256"] == it["exp_sha"] and res["bytes"] == it["exp_bytes"])
                row.update(bytes=res["bytes"], sha256=res["sha256"], expected_bytes=it["exp_bytes"],
                           expected_sha256=it["exp_sha"], match=ok)
                if it.get("on_disk") and it["on_disk"] != it["name"]:
                    row["on_disk_name"] = it["on_disk"]            # ...part001.zip (A1)
                if it["kind"] == "member" and it["name"] == "raw/events.jsonl":
                    lines_by_archive[it["archive"]] = res["lines"]
                    row["records"] = res["lines"]
                if not ok:
                    report["mismatches"].append(dict(session=sess, **row))
            elif it["kind"] == "outer":
                row.update(bytes=res["bytes"], sha256=res["sha256"],
                           note="no external manifest records this file's own hash; its members are checked")
            elif it["kind"] == "listed_not_held":
                row.update(expected_bytes=it["exp_bytes"], expected_sha256=it["exp_sha"],
                           note="listed in this archive's manifest but not held in it")
            elif it["kind"] == "not_listed":
                row.update(note="in the archive, not listed in its manifest")
            rs["checks"].append(row)
        # record counts
        for it in items:
            if it["session"] != sess or it["kind"] not in ("count", "total"):
                continue
            if it["kind"] == "count":
                got = lines_by_archive.get(it["archive"])
                ok = (got == it["expected"]) and (it.get("manifest_events") in (None, it["expected"]))
                row = dict(kind="record_count", archive=it["archive"], records=got, expected=it["expected"], match=ok)
            else:
                got = sum(lines_by_archive.get(a, 0) for a in it["partitions"])
                ok = (got == it["expected"])
                row = dict(kind="record_total", archive="COMPLETE.json", records=got, expected=it["expected"], match=ok)
            rs["checks"].append(row)
            if not ok:
                report["mismatches"].append(dict(session=sess, **row))
        total = sum(lines_by_archive.values())
        if total != C.EXPECTED_RAW[sess]:
            report["mismatches"].append(dict(session=sess, kind="expected_total", records=total,
                                             expected=C.EXPECTED_RAW[sess]))
        for kind in ("part", "rebuilt", "file", "member"):
            rows = [r for r in rs["checks"] if r["kind"] == kind]
            if rows:
                rs["summary"][kind] = "%d of %d match" % (sum(1 for r in rows if r["match"]), len(rows))
        rs["summary"]["listed_not_held"] = sum(1 for r in rs["checks"] if r["kind"] == "listed_not_held")
        rs["summary"]["raw_records"] = total
        rs["raw_inputs"] = [dict(archive=r["archive"], sha256=r["sha256"], bytes=r["bytes"], records=r["records"])
                            for r in rs["checks"] if r["kind"] == "member" and r["name"] == "raw/events.jsonl"]
        report["sessions"][sess] = rs
    report["result"] = "PASS" if not report["mismatches"] else "FAIL"
    path = IO.out("reports", "01_verification_report.json")
    IO.write_json(path, report)
    for sess in C.SESSION_ORDER:
        print(sess, report["sessions"][sess]["summary"])
    print("COMPLETE:", report["result"], "->", path)
    if report["mismatches"]:
        print(json.dumps(report["mismatches"], indent=1)[:3000])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
