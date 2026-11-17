"""Study 3 preprocessing: Linux audit record groups.

One audit event is several records that share audit(<time>:<serial>):
SYSCALL, EXECVE, CWD, PATH..., PROCTITLE. Records of one group are not always
next to each other in the stream, so groups are built by (time, serial).
"""
import re

RE_HEAD = re.compile(r"^type=(\S+) msg=audit\((\d+\.\d+):(\d+)\): ?")
RE_KV = re.compile(r'(\w[\w\[\]-]*)=("(?:[^"\\]|\\.)*"|\S*)')
RE_HEX = re.compile(r"^(?:[0-9A-Fa-f]{2})+$")
RE_ARG = re.compile(r"^a(\d+)$")
RE_ARGPART = re.compile(r"^a(\d+)\[(\d+)\]$")
# The enriched tail auditd appends (ARCH=... AUID="name" ...) starts at the first
# upper-case key glued to the previous value, after an \x1d separator when present.
RE_ENRICH = re.compile(r"\x1d?(?=(?:ARCH|SYSCALL|AUID|UID|GID|EUID|SUID|FSUID|EGID|SGID|FSGID|OUID|OGID|ID|OLD-AUID)=)")


def head(message):
    """(type, time string, serial) of one audit message, or None."""
    m = RE_HEAD.match(message)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def decode_value(v):
    """Audit value -> text. Quoted values are literal; bare hex is decoded."""
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    if v and RE_HEX.match(v) and len(v) % 2 == 0:
        try:
            return bytes.fromhex(v).decode("utf-8", "replace")
        except ValueError:
            return v
    return v


def fields(message):
    """Key/value pairs of the body of one audit message (enriched tail removed)."""
    m = RE_HEAD.match(message)
    body = message[m.end():] if m else message
    cut = None
    for mm in re.finditer(r'(?:\x1d|(?<=[^ ]))(ARCH|SYSCALL|AUID|UID|OUID|OLD-AUID|ID)=', body):
        cut = mm.start()
        break
    if cut is not None:
        body = body[:cut]
    return RE_KV.findall(body)


class Group:
    """One audit event."""
    __slots__ = ("gid", "time", "serial", "records", "types", "sys", "argv", "cwd", "paths", "proctitle")

    def __init__(self, gid, time, serial):
        self.gid = gid
        self.time = float(time)
        self.serial = serial
        self.records = []        # (index, event id, message)
        self.types = []
        self.sys = None          # dict of SYSCALL fields
        self.argv = None
        self.cwd = None
        self.paths = []
        self.proctitle = None

    def add(self, idx, event_id, message, typ):
        self.records.append((idx, event_id, message))
        self.types.append(typ)

    def parse(self):
        argparts = {}
        argc = None
        args = {}
        for _, _, msg in self.records:
            h = head(msg)
            typ = h[0]
            if typ == "SYSCALL":
                self.sys = {k: v for k, v in fields(msg)}
            elif typ == "EXECVE":
                for k, v in fields(msg):
                    if k == "argc":
                        argc = int(v)
                    else:
                        m = RE_ARG.match(k)
                        if m:
                            args[int(m.group(1))] = decode_value(v)
                            continue
                        m = RE_ARGPART.match(k)
                        if m:
                            argparts.setdefault(int(m.group(1)), {})[int(m.group(2))] = v
            elif typ == "CWD":
                for k, v in fields(msg):
                    if k == "cwd":
                        self.cwd = decode_value(v)
            elif typ == "PATH":
                d = {k: v for k, v in fields(msg)}
                self.paths.append((int(d.get("item", "0")), decode_value(d.get("name", ""))))
            elif typ == "PROCTITLE":
                for k, v in fields(msg):
                    if k == "proctitle":
                        self.proctitle = decode_value(v).replace("\x00", " ")
        for n, parts in argparts.items():
            hexs = "".join(parts[i] for i in sorted(parts))
            args[n] = decode_value(hexs)
        if args:
            self.argv = [args[i] for i in sorted(args)]
        self.paths.sort()
        return self

    # convenience -------------------------------------------------------
    def is_exec(self):
        return self.sys is not None and self.sys.get("syscall") == "59"

    def success(self):
        return self.sys is not None and self.sys.get("success") == "yes"

    def key(self):
        return (self.sys or {}).get("key", "").strip('"')

    def auid(self):
        return (self.sys or {}).get("auid")

    def ses(self):
        return (self.sys or {}).get("ses")

    def pid(self):
        return (self.sys or {}).get("pid")

    def ppid(self):
        return (self.sys or {}).get("ppid")

    def exe(self):
        return decode_value((self.sys or {}).get("exe", ""))

    def comm(self):
        return decode_value((self.sys or {}).get("comm", ""))

    def exec_path(self):
        """The file that was executed: PATH item 0 (the script for a script)."""
        for item, name in self.paths:
            if item == 0:
                return name
        return ""

    def text(self):
        """Every decoded string of the group, for pattern searches."""
        out = []
        if self.sys:
            out.append(self.exe())
            out.append(self.comm())
        if self.argv:
            out.extend(self.argv)
        if self.cwd:
            out.append(self.cwd)
        out.extend(n for _, n in self.paths)
        if self.proctitle:
            out.append(self.proctitle)
        return out


def build_groups(messages):
    """messages: iterable of (index, event id, message). Returns ordered list of
    Groups (order of first appearance) and the list of unparsable records."""
    groups = {}
    order = []
    bad = []
    for idx, eid, msg in messages:
        h = head(msg)
        if h is None:
            bad.append((idx, eid, msg))
            continue
        typ, t, serial = h
        gid = t + ":" + serial
        g = groups.get(gid)
        if g is None:
            g = groups[gid] = Group(gid, t, serial)
            order.append(g)
        g.add(idx, eid, msg, typ)
    return order, bad
