"""APIS data layer: SQLite storage, validation, appraisal chain, dashboard maths.

Standard library only, so the app runs with nothing to install except Python.
"""
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets as _secrets
import sqlite3
import threading
import time
import uuid

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("APIS_DATA") or os.path.join(BASE, "data")
DB_PATH = os.path.join(DATA, "apis.db")
UPLOADS = os.path.join(DATA, "uploads")
BACKUPS = os.path.join(DATA, "backups")
SECRETS_PATH = os.path.join(DATA, "secrets.json")
VERSION = "1.0.0"

LOCK = threading.RLock()
_conn = None

IMPACT = ["Low", "Medium", "High"]
STATUS = ["Completed", "In Progress", "Pending"]
CATS = ["Task", "Field visit", "Meeting", "Admin", "Follow-up", "Training", "Study"]
STAGES = ["Prospect", "Doc Verification", "Underwriting", "Sanctioned"]
KINDS = ["Work", "Club", "Volunteer", "Internship", "Academic"]
PROJECT_KINDS = ["Academic", "Personal", "Work", "Competition", "Volunteer"]
ACH_KINDS = ["Award", "Leadership", "Competition", "Publication", "Extracurricular", "Membership", "Other"]
LINK_KINDS = ["LinkedIn", "Instagram", "Facebook", "Website", "Blog", "GitHub", "Other"]
WORKSPACES = ["sales", "banking", "general"]
VISIBILITY = ["public", "private"]
DEFAULT_DOCS = [
    ("Trade License", 1),
    ("Audited Financials", 1),
    ("TIN Certificate", 1),
    ("Bank Statements", 1),
    ("NID of Owners", 1),
    ("Company Profile", 0),
]
DOCS_BY_WORKSPACE = {
    "sales": DEFAULT_DOCS,
    "banking": [("Application form", 1), ("Business registration copy", 1), ("Financial statements", 1), ("Tax certificate", 1),
                ("Bank statement copies", 1), ("Company profile", 0)],
    "general": [("Brief or request", 1), ("Supporting documents", 0), ("Approval", 0)],
}
FILE_RE = re.compile(r"^[a-f0-9]{16,40}\.(jpg|png|webp|gif|pdf)$")


class ApiError(Exception):
    def __init__(self, message, status=400, extra=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra or {}


def F(t, req=False, choices=None, default=""):
    return (t, req, choices, default)


ENT = {
    "logs": {
        "order": "date DESC, created_at DESC",
        "fields": {
            "date": F("d", 1),
            "category": F("s", 1, CATS, "Task"),
            "title": F("s", 1),
            "description": F("S"),
            "location": F("s"),
            "impact": F("s", 1, IMPACT, "Medium"),
            "status": F("s", 1, STATUS, "Pending"),
            "hours": F("n", 0, None, 0),
            "result": F("S"),
        },
    },
    "territory": {
        "order": "date DESC, created_at DESC",
        "fields": {
            "date": F("d", 1),
            "territory": F("s", 1),
            "route": F("s", 1),
            "distributor": F("s"),
            "target": F("n", 1, None, 0),
            "actual": F("n", 1, None, 0),
            "stock_out": F("b"),
            "stock_out_items": F("S"),
            "remarks": F("S"),
        },
    },
    "leads": {
        "order": "created_at DESC",
        "fields": {
            "company": F("s", 1),
            "contact": F("s"),
            "product": F("s"),
            "amount": F("n", 0, None, 0),
            "stage": F("s", 0, STAGES, "Prospect"),
            "stage_since": F("d"),
            "next_action": F("s"),
            "next_action_date": F("d"),
            "notes": F("S"),
        },
    },
    "lead_docs": {
        "order": "rowid ASC",
        "fields": {
            "lead_id": F("s", 1),
            "doc": F("s", 1),
            "required": F("b"),
            "received": F("b"),
            "verified": F("b"),
            "received_date": F("d"),
            "expiry_date": F("d"),
            "note": F("s"),
        },
    },
    "experience": {
        "order": "COALESCE(NULLIF(\"end\",''),'9999-99') DESC, \"start\" DESC",
        "fields": {
            "org": F("s", 1),
            "role": F("s", 1),
            "kind": F("s", 0, KINDS, "Work"),
            "start": F("m", 1),
            "end": F("m"),
            "location": F("s"),
            "description": F("S"),
            "skills": F("s"),
            "image": F("f"),
        },
    },
    "education": {
        "order": "COALESCE(NULLIF(\"end\",''),'9999-99') DESC, \"start\" DESC",
        "fields": {
            "school": F("s", 1),
            "degree": F("s"),
            "field": F("s"),
            "start": F("m"),
            "end": F("m"),
            "grade": F("s"),
            "description": F("S"),
            "image": F("f"),
        },
    },
    "certs": {
        "order": "issued DESC, created_at DESC",
        "fields": {
            "title": F("s", 1),
            "issuer": F("s"),
            "issued": F("m"),
            "credential_id": F("s"),
            "url": F("s"),
            "image": F("f"),
            "skills": F("s"),
            "description": F("S"),
        },
    },
    "skills": {
        "order": "category ASC, name ASC",
        "fields": {"name": F("s", 1), "category": F("s")},
    },
    "posts": {
        "order": "pinned DESC, posted_at DESC",
        "fields": {
            "caption": F("S"),
            "posted_at": F("t"),
            "visibility": F("s", 0, VISIBILITY, "private"),
            "pinned": F("b"),
            "tags": F("s"),
            "photos": F("j"),
            "category": F("s"),
            "archived": F("b"),
            "link": F("s"),
            "related": F("s"),
            "docs": F("j"),
        },
    },
    "projects": {
        "order": "COALESCE(NULLIF(\"end\",''),'9999-99') DESC, \"start\" DESC",
        "fields": {
            "title": F("s", 1),
            "kind": F("s", 0, PROJECT_KINDS, "Academic"),
            "org": F("s"),
            "role": F("s"),
            "start": F("m"),
            "end": F("m"),
            "summary": F("S"),
            "problem": F("S"),
            "methods": F("S"),
            "results": F("S"),
            "link": F("s"),
            "image": F("f"),
            "photos": F("j"),
            "tags": F("s"),
            "public": F("b", 0, None, 1),
        },
    },
    "achievements": {
        "order": "date DESC, created_at DESC",
        "fields": {
            "title": F("s", 1),
            "kind": F("s", 0, ACH_KINDS, "Award"),
            "org": F("s"),
            "date": F("m"),
            "description": F("S"),
            "link": F("s"),
            "image": F("f"),
            "public": F("b", 0, None, 1),
        },
    },
    "links": {
        "order": "rowid ASC",
        "fields": {
            "label": F("s"),
            "kind": F("s", 0, LINK_KINDS, "Website"),
            "url": F("s", 1),
        },
    },
}

PROFILE_KEYS = ["name", "headline", "about", "location", "email", "phone", "linkedin", "avatar", "cover"]

SETTING_DEFAULTS = {
    "currency": "৳",
    "alert_threshold": 80,
    "theme": "auto",
    "eod_enabled": False,
    "eod_time": "18:00",
    "eod_days": [6, 0, 1, 2, 3],  # Sunday to Thursday (Python weekday: Monday=0)
    "eod_catch_up": True,
    "report_to": "",
    "gmail_address": "",
    "subject_template": "EOD report - {date} - {name}",
    "attach_excel": True,
    "attach_full": False,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 465,
    "smtp_ssl": True,
    "drive_dir": "",
    "backups_keep": 30,
    "last_backup": "",
    "last_drive_backup": "",
    "last_drive_error": "",
    "seeded": False,
    "port": 8501,
    "workspace": "sales",
    "doc_dedupe": True,
}
HIDDEN_SETTINGS = {"pin_hash", "pin_salt"}
READONLY_SETTINGS = ("seeded", "last_backup", "last_drive_backup", "last_drive_error")


def now():
    return dt.datetime.now()


def today():
    return now().strftime("%Y-%m-%d")


def new_id():
    return uuid.uuid4().hex[:14]


# ----------------------------------------------------------------- database
def _col_type(t):
    return {"n": "REAL", "b": "INTEGER"}.get(t, "TEXT")


def connect():
    global _conn
    with LOCK:
        if _conn is not None:
            return _conn
        os.makedirs(DATA, exist_ok=True)
        os.makedirs(UPLOADS, exist_ok=True)
        os.makedirs(BACKUPS, exist_ok=True)
        c = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            c.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        c.execute("PRAGMA synchronous=NORMAL")
        _conn = c
        _create_schema(c)
        return c


def close():
    global _conn
    with LOCK:
        if _conn is not None:
            _conn.close()
            _conn = None


def _create_schema(c):
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS profile (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, created REAL, last_seen REAL)")
    for name, spec in ENT.items():
        cols = ["id TEXT PRIMARY KEY", "created_at TEXT", "updated_at TEXT"]
        for col, (t, _r, _c, _d) in spec["fields"].items():
            cols.append('"%s" %s' % (col, _col_type(t)))
        c.execute("CREATE TABLE IF NOT EXISTS %s (%s)" % (name, ", ".join(cols)))
        have = {r["name"] for r in c.execute("PRAGMA table_info(%s)" % name)}
        for col, (t, _r, _c, _d) in spec["fields"].items():
            if col not in have:
                c.execute('ALTER TABLE %s ADD COLUMN "%s" %s' % (name, col, _col_type(t)))
    c.execute(
        """CREATE TABLE IF NOT EXISTS appraisal (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, log_id TEXT UNIQUE, date TEXT, title TEXT,
        impact TEXT, result TEXT, logged_at TEXT, prev_hash TEXT, hash TEXT)"""
    )
    c.execute("CREATE TRIGGER IF NOT EXISTS appraisal_no_update BEFORE UPDATE ON appraisal "
              "BEGIN SELECT RAISE(ABORT, 'The career log cannot be edited'); END")
    c.execute("CREATE TRIGGER IF NOT EXISTS appraisal_no_delete BEFORE DELETE ON appraisal "
              "BEGIN SELECT RAISE(ABORT, 'The career log cannot be edited'); END")
    c.execute("CREATE TABLE IF NOT EXISTS lead_events (id TEXT PRIMARY KEY, lead_id TEXT, at TEXT, from_stage TEXT, to_stage TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS sends (id TEXT PRIMARY KEY, at TEXT, day TEXT, trigger TEXT, to_list TEXT, subject TEXT, ok INTEGER, error TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS i_logs_date ON logs(date)")
    c.execute("CREATE INDEX IF NOT EXISTS i_terr_date ON territory(date)")
    c.execute("CREATE INDEX IF NOT EXISTS i_docs_lead ON lead_docs(lead_id)")


def q(sql, args=()):
    with LOCK:
        return [dict(r) for r in connect().execute(sql, args).fetchall()]


def q1(sql, args=()):
    rows = q(sql, args)
    return rows[0] if rows else None


def run(sql, args=()):
    with LOCK:
        return connect().execute(sql, args)


# ----------------------------------------------------------------- settings
def get_settings():
    out = dict(SETTING_DEFAULTS)
    for r in q("SELECT key, value FROM settings"):
        if r["key"] in HIDDEN_SETTINGS:
            continue
        try:
            out[r["key"]] = json.loads(r["value"])
        except ValueError:
            pass
    return out


def get_setting(key):
    r = q1("SELECT value FROM settings WHERE key=?", (key,))
    if r is None:
        return SETTING_DEFAULTS.get(key)
    try:
        return json.loads(r["value"])
    except ValueError:
        return SETTING_DEFAULTS.get(key)


def set_setting(key, value):
    run("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value, ensure_ascii=False)))


def update_settings(data):
    clean = {}
    for key, val in data.items():
        if key not in SETTING_DEFAULTS or key in READONLY_SETTINGS:
            continue
        default = SETTING_DEFAULTS[key]
        if isinstance(default, bool):
            val = bool(val)
        elif isinstance(default, int):
            try:
                val = int(val)
            except (TypeError, ValueError):
                raise ApiError("%s must be a number" % key.replace("_", " "))
        elif isinstance(default, list):
            if not isinstance(val, list):
                raise ApiError("%s must be a list" % key)
            val = [int(x) for x in val if str(x).isdigit() and 0 <= int(x) <= 6]
        else:
            val = str(val).strip()[:500]
        if key == "eod_time" and not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", val):
            raise ApiError("Send time must look like 18:00")
        if key == "alert_threshold" and not 1 <= val <= 200:
            raise ApiError("Alert level must be between 1 and 200")
        if key == "workspace" and val not in WORKSPACES:
            raise ApiError("Workspace must be sales, banking or general")
        if key == "theme" and val not in ("auto", "light", "dark"):
            raise ApiError("Theme must be auto, light or dark")
        if key == "report_to":
            for addr in [a.strip() for a in val.split(",") if a.strip()]:
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", addr):
                    raise ApiError("'%s' is not a valid email address" % addr)
        if key == "gmail_address" and val and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", val):
            raise ApiError("That Gmail address does not look right")
        clean[key] = val
    for key, val in clean.items():
        set_setting(key, val)
    return get_settings()


def read_secrets():
    try:
        with open(SECRETS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_secret(key, value):
    os.makedirs(DATA, exist_ok=True)
    data = read_secrets()
    if value:
        data[key] = value
    else:
        data.pop(key, None)
    tmp = SECRETS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, SECRETS_PATH)


# ----------------------------------------------------------------- auth
def pin_is_set():
    return bool(q1("SELECT 1 FROM settings WHERE key='pin_hash'"))


def _hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()


def set_pin(pin):
    pin = (pin or "").strip()
    if len(pin) < 4 or len(pin) > 32:
        raise ApiError("Your PIN needs 4 to 32 characters")
    salt = _secrets.token_hex(16)
    run("INSERT INTO settings(key,value) VALUES('pin_salt',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(salt),))
    run("INSERT INTO settings(key,value) VALUES('pin_hash',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(_hash_pin(pin, salt)),))


def check_pin(pin):
    h = q1("SELECT value FROM settings WHERE key='pin_hash'")
    s = q1("SELECT value FROM settings WHERE key='pin_salt'")
    if not h or not s:
        return False
    return hmac.compare_digest(json.loads(h["value"]), _hash_pin((pin or "").strip(), json.loads(s["value"])))


def new_session():
    token = _secrets.token_urlsafe(32)
    th = hashlib.sha256(token.encode()).hexdigest()
    t = time.time()
    run("INSERT INTO sessions(token_hash,created,last_seen) VALUES(?,?,?)", (th, t, t))
    run("DELETE FROM sessions WHERE created < ?", (t - 90 * 86400,))
    return token


def session_ok(token):
    if not token:
        return False
    th = hashlib.sha256(token.encode()).hexdigest()
    r = q1("SELECT created FROM sessions WHERE token_hash=?", (th,))
    return bool(r) and time.time() - r["created"] < 90 * 86400


def end_session(token=None, everywhere=False):
    if everywhere:
        run("DELETE FROM sessions")
    elif token:
        run("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


# ----------------------------------------------------------------- validation
def _label(col):
    return col.replace("_", " ").capitalize()


def _coerce(col, spec, val):
    t, req, choices, default = spec
    if t in ("s", "S", "t", "f"):
        val = "" if val is None else str(val).strip()
        val = val[:10000] if t == "S" else val[:400]
        if t == "f" and val and not FILE_RE.match(val):
            raise ApiError("That picture is not valid")
    elif t == "d":
        val = "" if val is None else str(val).strip()
        if val:
            try:
                dt.datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                raise ApiError("%s must be a date" % _label(col))
    elif t == "m":
        val = "" if val is None else str(val).strip()
        if val and not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", val):
            raise ApiError("%s must be a month and year" % _label(col))
    elif t == "n":
        if val in (None, ""):
            val = 0.0
        try:
            val = float(str(val).replace(",", ""))
        except ValueError:
            raise ApiError("%s must be a number" % _label(col))
        if val < 0:
            raise ApiError("%s cannot be negative" % _label(col))
        if val > 1e12:
            raise ApiError("%s is too large" % _label(col))
    elif t == "b":
        val = 1 if (val is True or str(val).lower() in ("1", "true", "yes", "on")) else 0
    elif t == "j":
        if val in (None, ""):
            val = []
        if not isinstance(val, list):
            raise ApiError("Photos must be a list")
        for item in val:
            if not isinstance(item, str) or not FILE_RE.match(item):
                raise ApiError("One of the photos is not valid")
        val = json.dumps(val[:12])
    if req and t in ("s", "S", "d", "m", "t") and not val:
        raise ApiError("%s is required" % _label(col))
    if choices and val not in choices and not (not req and val == ""):
        raise ApiError("%s must be one of: %s" % (_label(col), ", ".join(choices)))
    return val


def _out(entity, row):
    spec = ENT[entity]["fields"]
    for col, (t, _r, _c, _d) in spec.items():
        if t == "b":
            row[col] = bool(row.get(col))
        elif t == "j":
            try:
                row[col] = json.loads(row.get(col) or "[]")
            except ValueError:
                row[col] = []
    return row


def file_in_use(name):
    if not name:
        return False
    for ent in ("certs", "experience", "education", "projects", "achievements"):
        if q1('SELECT 1 FROM %s WHERE "image"=?' % ent, (name,)):
            return True
    if q1("SELECT 1 FROM profile WHERE value=?", (name,)):
        return True
    for ent, col in (("posts", "photos"), ("posts", "docs"), ("projects", "photos")):
        for r in q('SELECT "%s" AS v FROM %s WHERE "%s" LIKE ?' % (col, ent, col), ("%" + name + "%",)):
            try:
                if name in json.loads(r["v"] or "[]"):
                    return True
            except ValueError:
                pass
    return False


def delete_file_if_unused(name):
    if name and FILE_RE.match(name) and not file_in_use(name):
        try:
            os.remove(os.path.join(UPLOADS, name))
        except OSError:
            pass


def list_items(entity, filters=None):
    spec = ENT[entity]
    sql = "SELECT * FROM %s" % entity
    where, args = [], []
    for key, val in (filters or {}).items():
        if key == "from" and "date" in spec["fields"]:
            where.append("date >= ?"); args.append(val)
        elif key == "to" and "date" in spec["fields"]:
            where.append("date <= ?"); args.append(val)
        elif key == "search":
            cols = [c for c, f in spec["fields"].items() if f[0] in ("s", "S")]
            where.append("(" + " OR ".join('"%s" LIKE ?' % c for c in cols) + ")")
            args.extend(["%" + val + "%"] * len(cols))
        elif key in spec["fields"] and re.match(r"^[\w .-]{1,80}$", val):
            where.append('"%s" = ?' % key); args.append(val)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + spec["order"]
    if entity in ("logs", "territory", "posts") and not filters:
        sql += " LIMIT 2000"
    return [_out(entity, r) for r in q(sql, args)]


def get_item(entity, item_id):
    r = q1("SELECT * FROM %s WHERE id=?" % entity, (item_id,))
    return _out(entity, r) if r else None


def create_item(entity, data):
    spec = ENT[entity]["fields"]
    vals = {}
    for col, fs in spec.items():
        raw = data.get(col, fs[3])
        if entity == "leads" and col in ("stage", "stage_since"):
            raw = fs[3]
        vals[col] = _coerce(col, fs, raw)
    if entity == "posts":
        if not vals["caption"] and vals["photos"] == "[]" and vals["docs"] == "[]":
            raise ApiError("Write something or add a photo first")
        if not vals["posted_at"]:
            vals["posted_at"] = now().strftime("%Y-%m-%d %H:%M")
    if entity == "leads":
        vals["stage"] = "Prospect"
        vals["stage_since"] = today()
    if entity == "lead_docs" and not q1("SELECT 1 FROM leads WHERE id=?", (vals["lead_id"],)):
        raise ApiError("That client was not found", 404)
    item_id = new_id()
    ts = now().strftime("%Y-%m-%d %H:%M:%S")
    cols = ["id", "created_at", "updated_at"] + list(vals)
    marks = ",".join("?" * len(cols))
    with LOCK:
        run('INSERT INTO %s (%s) VALUES (%s)' % (entity, ",".join('"%s"' % c for c in cols), marks),
            [item_id, ts, ts] + list(vals.values()))
        if entity == "leads":
            for doc, required in DOCS_BY_WORKSPACE.get(get_setting("workspace"), DEFAULT_DOCS):
                run("INSERT INTO lead_docs (id,created_at,updated_at,lead_id,doc,required,received,verified) VALUES (?,?,?,?,?,?,0,0)",
                    (new_id(), ts, ts, item_id, doc, required))
            run("INSERT INTO lead_events VALUES (?,?,?,?,?)", (new_id(), item_id, ts, "", "Prospect"))
        if entity == "logs":
            _appraise(item_id)
    return get_item(entity, item_id)


def update_item(entity, item_id, data):
    cur = get_item(entity, item_id)
    if not cur:
        raise ApiError("That item was not found", 404)
    spec = ENT[entity]["fields"]
    vals = {}
    for col, fs in spec.items():
        if entity == "leads" and col in ("stage", "stage_since"):
            continue
        if col in data:
            vals[col] = _coerce(col, fs, data[col])
    if entity == "posts":
        caption = vals.get("caption", cur["caption"])
        photos = json.loads(vals["photos"]) if "photos" in vals else cur["photos"]
        docs = json.loads(vals["docs"]) if "docs" in vals else cur["docs"]
        if not caption and not photos and not docs:
            raise ApiError("A post needs words or a photo")
    if entity == "lead_docs":
        vals.pop("lead_id", None)
    if not vals:
        return cur
    vals["updated_at"] = now().strftime("%Y-%m-%d %H:%M:%S")
    sets = ",".join('"%s"=?' % c for c in vals)
    with LOCK:
        run("UPDATE %s SET %s WHERE id=?" % (entity, sets), list(vals.values()) + [item_id])
        if entity == "logs":
            _appraise(item_id)
    new = get_item(entity, item_id)
    if "image" in spec and cur.get("image") and cur.get("image") != new.get("image"):
        delete_file_if_unused(cur["image"])
    for col in ("photos", "docs"):
        if col in spec and spec[col][0] == "j":
            for f in set(cur.get(col) or []) - set(new.get(col) or []):
                delete_file_if_unused(f)
    return new


def delete_item(entity, item_id):
    cur = get_item(entity, item_id)
    if not cur:
        raise ApiError("That item was not found", 404)
    with LOCK:
        run("DELETE FROM %s WHERE id=?" % entity, (item_id,))
        if entity == "leads":
            run("DELETE FROM lead_docs WHERE lead_id=?", (item_id,))
            run("DELETE FROM lead_events WHERE lead_id=?", (item_id,))
    files = list(cur.get("photos") or []) + list(cur.get("docs") or []) + ([cur["image"]] if cur.get("image") else [])
    for f in files:
        delete_file_if_unused(f)


# ----------------------------------------------------------------- profile
def get_profile():
    out = {k: "" for k in PROFILE_KEYS}
    for r in q("SELECT key, value FROM profile"):
        if r["key"] in out:
            out[r["key"]] = r["value"]
    return out


def update_profile(data):
    old = get_profile()
    for key in PROFILE_KEYS:
        if key not in data:
            continue
        val = str(data[key] or "").strip()
        if key in ("avatar", "cover"):
            if val and not FILE_RE.match(val):
                raise ApiError("That picture is not valid")
        else:
            val = val[:6000 if key == "about" else 300]
        if key == "name" and not val:
            raise ApiError("Your name cannot be empty")
        run("INSERT INTO profile(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, val))
    new = get_profile()
    for key in ("avatar", "cover"):
        if old[key] and old[key] != new[key]:
            delete_file_if_unused(old[key])
    return new


# ----------------------------------------------------------------- appraisal
def _appraise(log_id):
    log = q1("SELECT * FROM logs WHERE id=?", (log_id,))
    if not log or log["status"] != "Completed" or log["impact"] not in ("Medium", "High"):
        return
    if q1("SELECT 1 FROM appraisal WHERE log_id=?", (log_id,)):
        return
    last = q1("SELECT hash FROM appraisal ORDER BY seq DESC LIMIT 1")
    prev = last["hash"] if last else "GENESIS"
    logged_at = now().strftime("%Y-%m-%d %H:%M:%S")
    digest = _appraisal_hash(prev, log_id, log["date"], log["title"], log["impact"], log["result"], logged_at)
    run("INSERT INTO appraisal(log_id,date,title,impact,result,logged_at,prev_hash,hash) VALUES (?,?,?,?,?,?,?,?)",
        (log_id, log["date"], log["title"], log["impact"], log["result"], logged_at, prev, digest))


def _appraisal_hash(prev, log_id, date, title, impact, result, logged_at):
    text = "|".join([prev, log_id, date, title, impact, result or "", logged_at])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def appraisal_list():
    return q("SELECT * FROM appraisal ORDER BY seq DESC")


def appraisal_verify():
    rows = q("SELECT * FROM appraisal ORDER BY seq ASC")
    prev = "GENESIS"
    for r in rows:
        want = _appraisal_hash(prev, r["log_id"], r["date"], r["title"], r["impact"], r["result"], r["logged_at"])
        if r["prev_hash"] != prev or r["hash"] != want:
            return {"ok": False, "count": len(rows), "broken_at": r["seq"], "title": r["title"]}
        prev = r["hash"]
    return {"ok": True, "count": len(rows)}


# ----------------------------------------------------------------- leads
def lead_docs(lead_id):
    return list_items("lead_docs", {"lead_id": lead_id})


def move_lead(lead_id, stage):
    lead = get_item("leads", lead_id)
    if not lead:
        raise ApiError("That client was not found", 404)
    if stage not in STAGES:
        raise ApiError("Unknown stage")
    if stage == lead["stage"]:
        return lead
    if STAGES.index(stage) >= STAGES.index("Underwriting"):
        missing = [d["doc"] for d in lead_docs(lead_id) if d["required"] and not d["verified"]]
        if missing:
            raise ApiError("Verify these documents before moving on: " + ", ".join(missing), 409, {"missing": missing})
    ts = now().strftime("%Y-%m-%d %H:%M:%S")
    with LOCK:
        run("UPDATE leads SET stage=?, stage_since=?, updated_at=? WHERE id=?", (stage, today(), ts, lead_id))
        run("INSERT INTO lead_events VALUES (?,?,?,?,?)", (new_id(), lead_id, ts, lead["stage"], stage))
    return get_item("leads", lead_id)


def leads_with_progress():
    items = list_items("leads")
    docs = q("SELECT lead_id, required, verified FROM lead_docs")
    by = {}
    for d in docs:
        s = by.setdefault(d["lead_id"], {"req": 0, "ver": 0})
        if d["required"]:
            s["req"] += 1
            if d["verified"]:
                s["ver"] += 1
    for it in items:
        s = by.get(it["id"], {"req": 0, "ver": 0})
        it["docs_required"], it["docs_verified"] = s["req"], s["ver"]
    return items


# ----------------------------------------------------------------- territory
def _pct(actual, target):
    return round(actual / target * 100, 1) if target else None


def territory_summary(frm, to, territory=""):
    args = [frm, to]
    extra = ""
    if territory:
        extra = " AND territory=?"
        args.append(territory)
    rows = q("SELECT * FROM territory WHERE date>=? AND date<=?" + extra + " ORDER BY date", args)
    routes, days = {}, {}
    for r in rows:
        key = (r["territory"], r["route"])
        s = routes.setdefault(key, {"territory": r["territory"], "route": r["route"], "target": 0, "actual": 0, "stock_outs": 0, "entries": 0})
        s["target"] += r["target"] or 0
        s["actual"] += r["actual"] or 0
        s["entries"] += 1
        if r["stock_out"]:
            s["stock_outs"] += 1
        d = days.setdefault(r["date"], {"date": r["date"], "target": 0, "actual": 0})
        d["target"] += r["target"] or 0
        d["actual"] += r["actual"] or 0
    route_list = sorted(routes.values(), key=lambda s: s["route"])
    for s in route_list:
        s["pct"] = _pct(s["actual"], s["target"])
    day_list = sorted(days.values(), key=lambda d: d["date"])
    for d in day_list:
        d["pct"] = _pct(d["actual"], d["target"])
    tt = sum(s["target"] for s in route_list)
    ta = sum(s["actual"] for s in route_list)
    opts = {
        "territories": [r["territory"] for r in q("SELECT DISTINCT territory FROM territory ORDER BY territory")],
        "routes": [r["route"] for r in q("SELECT DISTINCT route FROM territory ORDER BY route")],
        "distributors": [r["distributor"] for r in q("SELECT DISTINCT distributor FROM territory WHERE distributor<>'' ORDER BY distributor")],
    }
    return {"routes": route_list, "days": day_list, "target": tt, "actual": ta, "pct": _pct(ta, tt), "options": opts}


# ----------------------------------------------------------------- dashboard
def _days_ago(n):
    return (now() - dt.timedelta(days=n)).strftime("%Y-%m-%d")


def alerts():
    out = []
    thr = get_setting("alert_threshold")
    summ = territory_summary(_days_ago(6), today())
    for s in summ["routes"]:
        if s["pct"] is not None and s["pct"] < thr:
            out.append({"level": "high" if s["pct"] < thr - 20 else "medium", "kind": "route",
                        "title": "%s is at %s%% of target" % (s["route"], round(s["pct"])),
                        "detail": "%s, last 7 days" % s["territory"], "go": "#/routes"})
    seen = set()
    for r in q("SELECT * FROM territory WHERE stock_out=1 AND date>=? ORDER BY date DESC", (_days_ago(2),)):
        key = (r["route"], r["stock_out_items"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"level": "high", "kind": "stock", "title": "Stock-out on %s" % r["route"],
                    "detail": r["stock_out_items"] or "Items not listed", "go": "#/routes"})
    for l in q("SELECT * FROM leads WHERE next_action_date<>'' AND next_action_date<? AND stage<>'Sanctioned' ORDER BY next_action_date", (today(),)):
        out.append({"level": "medium", "kind": "lead", "title": "Follow-up overdue: %s" % l["company"],
                    "detail": "%s, due %s" % (l["next_action"] or "Next step", l["next_action_date"]), "go": "#/leads"})
    for l in q("SELECT id, company FROM leads WHERE stage='Doc Verification'"):
        n = len([d for d in lead_docs(l["id"]) if d["required"] and not d["verified"]])
        if n:
            out.append({"level": "info", "kind": "docs", "title": "%s: %d document%s to verify" % (l["company"], n, "" if n == 1 else "s"),
                        "detail": "Needed before underwriting", "go": "#/leads"})
    order = {"high": 0, "medium": 1, "info": 2}
    out.sort(key=lambda a: order[a["level"]])
    return out


def dashboard():
    t = today()
    logs = q("SELECT status, hours FROM logs WHERE date=?", (t,))
    open_items = q1("SELECT COUNT(*) AS n FROM logs WHERE status<>'Completed'")["n"]
    terr_today = territory_summary(t, t)
    week = territory_summary(_days_ago(6), t)
    stage_counts = {s: {"count": 0, "amount": 0} for s in STAGES}
    for l in q("SELECT stage, amount FROM leads"):
        stage_counts[l["stage"]]["count"] += 1
        stage_counts[l["stage"]]["amount"] += l["amount"] or 0
    sent_today = bool(q1("SELECT 1 FROM sends WHERE day=? AND ok=1", (t,)))
    return {
        "date": t,
        "tasks": {"total": len(logs), "done": len([x for x in logs if x["status"] == "Completed"]),
                  "hours": round(sum(x["hours"] or 0 for x in logs), 1), "open": open_items},
        "territory": {"today": {"target": terr_today["target"], "actual": terr_today["actual"], "pct": terr_today["pct"]},
                      "week": {"target": week["target"], "actual": week["actual"], "pct": week["pct"]}},
        "leads": {"stages": stage_counts, "active": sum(v["count"] for k, v in stage_counts.items() if k != "Sanctioned")},
        "alerts": alerts(),
        "eod_sent": sent_today,
        "posts": q1("SELECT COUNT(*) AS n FROM posts")["n"],
    }
