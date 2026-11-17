"""Study 3 preprocessing: reading the evidence packages and writing outputs.

The evidence folder is only ever opened for reading. Parts of a split archive
are read in place as one file; no rebuilt archive is written to disk (A1).
"""
import gzip
import hashlib
import io
import json
import os
import time
import zipfile

import s3_config as C

CHUNK = 4 * 1024 * 1024


# ------------------------------------------------------------------ files
class MultiPartFile(io.RawIOBase):
    """Read-only, seekable view of several files laid end to end."""

    def __init__(self, paths):
        super().__init__()
        self.paths = list(paths)
        self.sizes = [os.path.getsize(p) for p in self.paths]
        self.starts = []
        acc = 0
        for s in self.sizes:
            self.starts.append(acc)
            acc += s
        self.total = acc
        self.pos = 0
        self._fh = [None] * len(self.paths)

    def readable(self):
        return True

    def seekable(self):
        return True

    def writable(self):
        return False

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        else:
            self.pos = self.total + offset
        return self.pos

    def _part(self, pos):
        lo, hi = 0, len(self.starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def readinto(self, b):
        n = len(b)
        done = 0
        while done < n and self.pos < self.total:
            i = self._part(self.pos)
            if self._fh[i] is None:
                self._fh[i] = open(self.paths[i], "rb")   # read only
            f = self._fh[i]
            off = self.pos - self.starts[i]
            f.seek(off)
            chunk = f.read(min(n - done, self.sizes[i] - off))
            if not chunk:
                break
            b[done:done + len(chunk)] = chunk
            done += len(chunk)
            self.pos += len(chunk)
        return done

    def close(self):
        for f in self._fh:
            if f is not None:
                f.close()
        super().close()


def open_binary(paths):
    """One path -> ordinary read-only file. Several -> MultiPartFile."""
    if isinstance(paths, str):
        return open(paths, "rb")
    if len(paths) == 1:
        return open(paths[0], "rb")
    return io.BufferedReader(MultiPartFile(paths), buffer_size=CHUNK)


def open_zip(paths):
    return zipfile.ZipFile(open_binary(paths), "r")


def sha256_stream(f, count_lines=False):
    h = hashlib.sha256()
    n = 0
    lines = 0
    while True:
        b = f.read(CHUNK)
        if not b:
            break
        h.update(b)
        n += len(b)
        if count_lines:
            lines += b.count(b"\n")
    return h.hexdigest(), n, lines


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_stream(f)[:2]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ packages
def ev(*parts):
    return os.path.join(C.EVIDENCE, *parts)


def part_paths(folder, name):
    """Paths of name.part001, name.part002, ... in order. A first part that
    arrived as name.part001.zip is accepted (A1); verification checks that its
    size and hash match the manifest's .part001 entry."""
    out = []
    i = 1
    while True:
        base = os.path.join(folder, "%s.part%03d" % (name, i))
        if os.path.exists(base):
            out.append(base)
        elif i == 1 and os.path.exists(base + ".zip"):
            out.append(base + ".zip")
        else:
            break
        i += 1
    return out


def package(sess):
    """Describe where a session's raw records and boundary files are.
    Returns dict: raw (list of (label, paths, member)), boundary (paths), layout."""
    cfg = C.SESSIONS[sess]
    lay = cfg["layout"]
    if lay == "zip":
        p = [ev(cfg["main"])]
        return dict(layout=lay, raw=[("main", p, "raw/events.jsonl")], boundary=p)
    if lay == "parts":
        folder = ev(cfg["folder"])
        p = part_paths(folder, cfg["main_name"])
        if not p:
            raise SystemExit("%s: no parts found for %s" % (sess, cfg["main_name"]))
        return dict(layout=lay, raw=[("main", p, "raw/events.jsonl")], boundary=p)
    if lay == "split":
        folder = ev(cfg["folder"])
        raw = []
        for fn in sorted(os.listdir(folder)):
            if fn.startswith("session-eng-") and fn.endswith(".zip"):
                raw.append((fn[:-4], [os.path.join(folder, fn)], "raw/events.jsonl"))
        ctx = part_paths(folder, "context.zip")
        if not ctx:
            raise SystemExit("%s: context.zip parts not found" % sess)
        raw.append(("context", ctx, "raw/events.jsonl"))
        raw.append(("ambiguous", [os.path.join(folder, "ambiguous.zip")], "raw/events.jsonl"))
        return dict(layout=lay, raw=raw, boundary=[os.path.join(folder, "source-provenance.zip")])
    raise SystemExit("unknown layout " + lay)


def read_boundaries(sess):
    """SESSION_BOUNDARIES.json and the stage-boundary file (the only two
    metadata files the preprocessing reads, design section 2)."""
    cfg = C.SESSIONS[sess]
    pk = package(sess)
    with open_zip(pk["boundary"]) as zf:
        sb = zf.read("SESSION_BOUNDARIES.json")
        st = zf.read(cfg["stage_member"])
    return json.loads(sb), json.loads(st), sha256_bytes(sb), sha256_bytes(st)


def iter_raw_lines(paths, member, start_line=0):
    """Yield (line_number, bytes) of a raw/events.jsonl member, from start_line."""
    zf = open_zip(paths)
    try:
        with zf.open(member) as f:
            bf = io.BufferedReader(f, buffer_size=CHUNK)
            n = 0
            for line in bf:
                if n >= start_line:
                    yield n, line
                n += 1
    finally:
        zf.close()


# ------------------------------------------------------------------ logins
def login_table(sess, sb):
    """Join the configured login decisions to SESSION_BOUNDARIES.json.
    Every recorded login must be configured exactly once and vice versa."""
    cfg = C.SESSIONS[sess]
    seen = {}
    for s in sb["sessions"]:
        seen.setdefault(s["session_id"], {})[s["kind"]] = s
    rows = []
    used = set()
    for sid in sorted(seen, key=lambda k: seen[k].get("start", {}).get("time", "")):
        hits = [l for l in cfg["logins"] if sid.startswith(l["prefix"])]
        if len(hits) != 1:
            raise SystemExit("%s: login %s matches %d configured rows" % (sess, sid, len(hits)))
        l = hits[0]
        used.add(l["prefix"])
        st = seen[sid].get("start", {})
        en = seen[sid].get("end", {})
        rows.append(dict(session=sess, login_id=sid, included=l["included"], typed_by=l["typed_by"],
                         what=l["what"], reason=l["reason"], note=l["note"],
                         uid=st.get("uid"), audit_session=st.get("audit_session"),
                         start_time=st.get("time"), end_time=en.get("time")))
    missing = [l["prefix"] for l in cfg["logins"] if l["prefix"] not in used]
    if missing:
        raise SystemExit("%s: configured logins not in SESSION_BOUNDARIES: %s" % (sess, missing))
    return rows


# ------------------------------------------------------------------ keys
def session_key(sess):
    return "s_" + hashlib.sha256(("study3:" + sess).encode()).hexdigest()[:10]


def login_key(login_id):
    return "l_" + hashlib.sha256(login_id.encode()).hexdigest()[:10]


# ------------------------------------------------------------------ outputs
def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p


def out(*parts):
    p = os.path.join(C.out_root(), *parts)
    ensure_dir(os.path.dirname(p))
    return p


def work(*parts):
    p = os.path.join(C.work_root(), *parts)
    ensure_dir(os.path.dirname(p))
    return p


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dumps(obj):
    """One JSON line, key order as given (records keep the collected order)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


class GzAppend:
    """Deterministic gzip writer that appends one gzip member per block.
    A file written in several runs is byte-identical to one written in a single
    run, because members are closed at fixed record boundaries."""

    def __init__(self, path, level=6):
        self.path = path
        self.level = level
        self.raw = open(path, "ab")
        self.gz = None

    def write(self, b):
        if self.gz is None:
            self.gz = gzip.GzipFile(filename="", mode="wb", fileobj=self.raw,
                                    compresslevel=self.level, mtime=0)
        self.gz.write(b)

    def end_block(self):
        if self.gz is not None:
            self.gz.close()
            self.gz = None
        self.raw.flush()

    def size(self):
        self.raw.flush()
        return self.raw.tell()

    def close(self):
        self.end_block()
        self.raw.close()


def gz_text_writer(path, level=6):
    """Whole-file deterministic gzip (mtime 0, no name)."""
    raw = open(path, "wb")
    return gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=level, mtime=0), raw


class Budget:
    """Each shell call on the user's machine is stopped after 3 minutes, so
    long steps run in slices and stop cleanly before the limit."""

    def __init__(self, seconds=None):
        self.t0 = time.time()
        self.limit = float(os.environ.get("S3_BUDGET", seconds or 140))

    def left(self):
        return self.limit - (time.time() - self.t0)

    def ok(self):
        return self.left() > 0
