#!/usr/bin/env python3
"""APIS - Automated Performance & Integrated System. Runs on your own laptop.

Needs only Python 3.9 or newer. No extra packages.
"""
import argparse
import json
import logging
import logging.handlers
import os
import re
import secrets
import socket
import sys
import threading
import time
import urllib.parse as up
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import store  # noqa: E402

WEB = os.path.join(HERE, "web")
log = logging.getLogger("apis")

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".json": "application/json", ".webmanifest": "application/manifest+json", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".ico": "image/x-icon", ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8", ".pdf": "application/pdf",
}
CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
ENTITIES = "logs|territory|leads|lead_docs|experience|education|certs|skills|posts|projects|achievements|links"
PUBLIC_API = {"/api/ping", "/api/auth/status", "/api/auth/setup", "/api/auth/login"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_JSON = 2 * 1024 * 1024
MAX_UPLOAD = 15 * 1024 * 1024
STATE = {"port": 8501, "server": None, "shutdown_token": "", "stop": threading.Event()}
FAILS = {}  # ip -> (count, locked_until)
ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


class Raw:
    def __init__(self, data, ctype, status=200, headers=None):
        self.data, self.ctype, self.status, self.headers = data, ctype, status, headers or {}


# ====================================================================== handler
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "APIS"
    sys_version = ""

    def log_message(self, fmt, *args):
        log.debug("%s - %s", self.address_string(), fmt % args)

    # ---- plumbing
    def cookie(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "apis_session":
                return v
        return ""

    def authed(self):
        return store.session_ok(self.cookie())

    def is_local(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def read_body(self, limit):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n > limit:
            self.close_connection = True
            raise store.ApiError("That file is too large", 413)
        return self.rfile.read(n) if n else b""

    def json_body(self):
        raw = self.read_body(MAX_JSON)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise store.ApiError("That request was not understood")
        if not isinstance(data, dict):
            raise store.ApiError("That request was not understood")
        return data

    def send_raw(self, status, data, ctype, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Frame-Options", "DENY")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def send_json(self, obj, status=200, headers=None):
        h = {"Cache-Control": "no-store"}
        h.update(headers or {})
        self.send_raw(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", h)

    # ---- dispatch
    def do_GET(self):
        self.dispatch("GET")

    def do_HEAD(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def dispatch(self, method):
        try:
            parsed = up.urlsplit(self.path)
            path = up.unquote(parsed.path)
            self.query = {k: v[0] for k, v in up.parse_qs(parsed.query).items()}
            if path.startswith("/api/"):
                return self.api(method, path)
            if method != "GET":
                raise store.ApiError("Not found", 404)
            if path == "/cv":
                if not self.authed():
                    return self.send_raw(302, b"", "text/plain", {"Location": "/"})
                import publish
                return self.send_raw(200, publish.cv_html().encode("utf-8"), "text/html; charset=utf-8", {"Cache-Control": "no-store"})
            if path == "/portfolio-print":
                if not self.authed():
                    return self.send_raw(302, b"", "text/plain", {"Location": "/"})
                import builder
                try:
                    cfg = json.loads(self.query.get("c") or "{}")
                except ValueError:
                    cfg = {}
                html = builder.render_html(builder.assemble(cfg), False, True)
                return self.send_raw(200, html.encode("utf-8"), "text/html; charset=utf-8", {"Cache-Control": "no-store"})
            if path.startswith("/files/"):
                return self.serve_upload(path[7:])
            return self.serve_static(path)
        except store.ApiError as e:
            body = {"error": e.message}
            body.update(e.extra)
            self.send_json(body, e.status)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception:
            log.exception("Request failed: %s %s", method, self.path)
            try:
                self.send_json({"error": "Something went wrong. Details are saved in data/apis.log"}, 500)
            except Exception:
                self.close_connection = True

    def api(self, method, path):
        if method in ("POST", "PUT", "DELETE") and self.headers.get("X-APIS") != "1":
            raise store.ApiError("Request blocked", 403)
        if path not in PUBLIC_API and not self.authed():
            if path == "/api/shutdown" and self.is_local() and STATE["shutdown_token"] and \
                    self.headers.get("X-Shutdown-Token") == STATE["shutdown_token"]:
                pass
            else:
                raise store.ApiError("Please sign in", 401)
        for m, rx, fn in ROUTES:
            if m == method:
                match = rx.match(path)
                if match:
                    result = fn(self, *match.groups())
                    if isinstance(result, Raw):
                        return self.send_raw(result.status, result.data, result.ctype, result.headers)
                    if isinstance(result, tuple):
                        return self.send_json(result[1], result[0], result[2] if len(result) > 2 else None)
                    return self.send_json(result)
        raise store.ApiError("Not found", 404)

    # ---- static
    def serve_static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        rel = os.path.normpath(path.lstrip("/"))
        full = os.path.join(WEB, rel)
        if not full.startswith(WEB + os.sep) or not os.path.isfile(full):
            raise store.ApiError("Not found", 404)
        st = os.stat(full)
        etag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
        ctype = MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        if self.headers.get("If-None-Match") == etag:
            return self.send_raw(304, b"", ctype, {"ETag": etag})
        with open(full, "rb") as fh:
            data = fh.read()
        self.send_raw(200, data, ctype, {"ETag": etag, "Cache-Control": "no-cache"})

    def serve_upload(self, name):
        if not self.authed():
            raise store.ApiError("Please sign in", 401)
        if not store.FILE_RE.match(name):
            raise store.ApiError("Not found", 404)
        full = os.path.join(store.UPLOADS, name)
        if not os.path.isfile(full):
            raise store.ApiError("Not found", 404)
        with open(full, "rb") as fh:
            data = fh.read()
        self.send_raw(200, data, MIME.get(os.path.splitext(name)[1], "application/octet-stream"),
                      {"Cache-Control": "private, max-age=31536000, immutable"})


# ====================================================================== routes
def _day(h, key, default):
    v = h.query.get(key, default)
    if not DATE_RE.match(v or ""):
        raise store.ApiError("Dates must look like 2026-10-18")
    return v


@route("GET", "/api/ping")
def ping(h):
    return {"app": "APIS", "version": store.VERSION}


# ---- auth
@route("GET", "/api/auth/status")
def auth_status(h):
    return {"setup": store.pin_is_set(), "authed": h.authed(), "version": store.VERSION}


def _cookie(token):
    return {"Set-Cookie": "apis_session=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=7776000" % token}


@route("POST", "/api/auth/setup")
def auth_setup(h):
    if store.pin_is_set():
        raise store.ApiError("A PIN is already set", 409)
    store.set_pin(h.json_body().get("pin"))
    return (200, {"ok": True}, _cookie(store.new_session()))


@route("POST", "/api/auth/login")
def auth_login(h):
    ip = h.client_address[0]
    count, locked = FAILS.get(ip, (0, 0))
    if locked > time.time():
        raise store.ApiError("Too many tries. Wait %d seconds and try again." % int(locked - time.time() + 1), 429)
    if store.check_pin(h.json_body().get("pin")):
        FAILS.pop(ip, None)
        return (200, {"ok": True}, _cookie(store.new_session()))
    count += 1
    FAILS[ip] = (0, time.time() + 30) if count >= 5 else (count, 0)
    time.sleep(0.4)
    raise store.ApiError("That PIN is not right", 401)


@route("POST", "/api/auth/logout")
def auth_logout(h):
    store.end_session(h.cookie())
    return (200, {"ok": True}, {"Set-Cookie": "apis_session=; Path=/; HttpOnly; Max-Age=0"})


@route("POST", "/api/auth/change")
def auth_change(h):
    d = h.json_body()
    if not store.check_pin(d.get("old")):
        raise store.ApiError("Your current PIN is not right", 401)
    store.set_pin(d.get("new"))
    store.end_session(everywhere=True)
    return (200, {"ok": True}, _cookie(store.new_session()))


# ---- app data
@route("GET", "/api/bootstrap")
def bootstrap(h):
    return {"profile": store.get_profile(), "settings": store.get_settings(), "version": store.VERSION, "today": store.today(),
            "enums": {"impact": store.IMPACT, "status": store.STATUS, "cats": store.CATS, "stages": store.STAGES,
                      "kinds": store.KINDS, "project_kinds": store.PROJECT_KINDS, "ach_kinds": store.ACH_KINDS, "link_kinds": store.LINK_KINDS, "default_docs": [d[0] for d in store.DEFAULT_DOCS]}}


@route("GET", "/api/dashboard")
def dashboard(h):
    return store.dashboard()


@route("GET", "/api/profile")
def profile_get(h):
    return store.get_profile()


@route("PUT", "/api/profile")
def profile_put(h):
    return store.update_profile(h.json_body())


@route("GET", "/api/(%s)" % ENTITIES)
def list_entity(h, ent):
    if ent == "leads":
        return store.leads_with_progress()
    return store.list_items(ent, h.query)


@route("POST", "/api/(%s)" % ENTITIES)
def create_entity(h, ent):
    return (201, store.create_item(ent, h.json_body()))


@route("PUT", "/api/(%s)/([a-f0-9]+)" % ENTITIES)
def update_entity(h, ent, item_id):
    return store.update_item(ent, item_id, h.json_body())


@route("DELETE", "/api/(%s)/([a-f0-9]+)" % ENTITIES)
def delete_entity(h, ent, item_id):
    store.delete_item(ent, item_id)
    return {"ok": True}


@route("POST", "/api/leads/([a-f0-9]+)/move")
def lead_move(h, lead_id):
    return store.move_lead(lead_id, h.json_body().get("stage"))


@route("GET", "/api/appraisal")
def appraisal(h):
    return store.appraisal_list()


@route("GET", "/api/appraisal/verify")
def appraisal_verify(h):
    return store.appraisal_verify()


@route("GET", "/api/territory/summary")
def territory_summary(h):
    today = store.today()
    return store.territory_summary(_day(h, "from", today), _day(h, "to", today), h.query.get("territory", ""))


# ---- settings, gmail, reports
@route("GET", "/api/settings")
def settings_get(h):
    s = store.get_settings()
    s["gmail_password_set"] = bool(store.read_secrets().get("gmail_app_password"))
    return s


@route("PUT", "/api/settings")
def settings_put(h):
    s = store.update_settings(h.json_body())
    s["gmail_password_set"] = bool(store.read_secrets().get("gmail_app_password"))
    return s


@route("PUT", "/api/gmail")
def gmail_put(h):
    d = h.json_body()
    pw = str(d.get("app_password") or "").replace(" ", "").strip()
    if pw:
        if not re.match(r"^[A-Za-z0-9]{12,32}$", pw):
            raise store.ApiError("An App Password is 16 letters with no spaces. Copy it again from Google.")
        store.write_secret("gmail_app_password", pw)
    store.update_settings({"gmail_address": d.get("address", ""), "report_to": d.get("report_to", "")})
    return settings_get(h)


@route("DELETE", "/api/gmail")
def gmail_delete(h):
    store.write_secret("gmail_app_password", "")
    store.update_settings({"eod_enabled": False})
    return settings_get(h)


@route("POST", "/api/mail/test")
def mail_test(h):
    import reports
    return reports.send_test()


@route("GET", "/api/report/preview")
def report_preview(h):
    import reports
    day = _day(h, "date", store.today())
    out = reports.build_summary(day)
    out["day"] = day
    return out


@route("GET", "/api/report/status")
def report_status(h):
    import reports
    return {"mail_ready": reports.mail_ready(), "next_run": reports.next_run(), "sent_today": reports._sent_today(),
            "enabled": store.get_setting("eod_enabled")}


@route("POST", "/api/report/send")
def report_send(h):
    import reports
    d = h.json_body()
    day = d.get("date") or store.today()
    if not DATE_RE.match(day):
        raise store.ApiError("Dates must look like 2026-10-18")
    return reports.send_report(day, "manual")


@route("GET", "/api/sends")
def sends(h):
    import reports
    return reports.sends_list()


@route("GET", "/api/export.xlsx")
def export_xlsx(h):
    import reports
    scope = "all" if h.query.get("scope") == "all" else "today"
    day = _day(h, "date", store.today())
    name = "apis_data.xlsx" if scope == "all" else "APIS_%s.xlsx" % day
    return Raw(reports.workbook_bytes(scope, day), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 200,
               {"Content-Disposition": 'attachment; filename="%s"' % name, "Cache-Control": "no-store"})


@route("GET", "/api/ask")
def ask(h):
    import ask as ask_mod
    return ask_mod.answer(h.query.get("q", ""))


# ---- portfolio builder
@route("GET", "/api/portfolio/options")
def pf_options(h):
    import builder
    return builder.options()


@route("POST", "/api/portfolio/preview")
def pf_preview(h):
    import builder
    doc = builder.assemble(h.json_body())
    return {"html": builder.render_html(doc, False, False), "pages": doc["pages"], "pages_text": doc["pages_text"], "dropped": doc["dropped"],
            "notes": doc["notes"], "empty_sections": doc["empty_sections"], "contact": doc["contact"]}


@route("POST", "/api/portfolio/export/(html|docx)")
def pf_export(h, kind):
    import builder
    doc = builder.assemble(h.json_body())
    stem = re.sub(r"[^A-Za-z0-9]+", "_", doc["name"]).strip("_") or "Portfolio"
    if kind == "docx":
        return Raw(builder.render_docx(doc), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 200,
                   {"Content-Disposition": 'attachment; filename="%s_Portfolio.docx"' % stem, "Cache-Control": "no-store"})
    return Raw(builder.render_html(doc, True, False).encode("utf-8"), "text/html; charset=utf-8", 200,
               {"Content-Disposition": 'attachment; filename="%s_Portfolio.html"' % stem, "Cache-Control": "no-store"})


# ---- business analysis studio
MAX_BI_UPLOAD = 60 * 1024 * 1024


@route("GET", "/api/bi/files")
def bi_files(h):
    import bi
    return bi.list_files()


@route("POST", "/api/bi/upload")
def bi_upload(h):
    import bi
    name = up.unquote(h.headers.get("X-Filename") or "file.xlsx")
    return (201, bi.add_file(name, h.read_body(MAX_BI_UPLOAD)))


@route("DELETE", "/api/bi/files/([a-f0-9]+)")
def bi_remove(h, fid):
    import bi
    bi.remove_file(fid)
    return {"ok": True}


@route("GET", "/api/bi/files/([a-f0-9]+)/preview")
def bi_preview(h, fid):
    import bi
    hr = h.query.get("header")
    return bi.preview(fid, h.query.get("sheet", ""), int(hr) if hr and hr.isdigit() else None)


@route("POST", "/api/bi/analyze")
def bi_analyze(h):
    import bi
    return bi.analyze(h.json_body())


@route("POST", "/api/bi/export")
def bi_export(h):
    import bi
    res = bi.analyze(h.json_body())
    return Raw(bi.export_bytes(res), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 200,
               {"Content-Disposition": 'attachment; filename="APIS_analysis_%s.xlsx"' % store.today(), "Cache-Control": "no-store"})


@route("GET", "/api/bi/presets")
def bi_presets(h):
    import bi
    return bi.presets()


@route("POST", "/api/bi/presets")
def bi_preset_save(h):
    import bi
    d = h.json_body()
    return bi.save_preset(d.get("name"), d.get("body") or {})


@route("DELETE", "/api/bi/presets/([a-f0-9]+)")
def bi_preset_delete(h, pid):
    import bi
    bi.delete_preset(pid)
    return {"ok": True}


# ---- files, backup, network, publish
SIGS = [(b"%PDF-", ".pdf"), (b"\xff\xd8\xff", ".jpg"), (b"\x89PNG\r\n\x1a\n", ".png"), (b"GIF87a", ".gif"), (b"GIF89a", ".gif")]


@route("POST", "/api/upload")
def upload(h):
    data = h.read_body(MAX_UPLOAD)
    if not data:
        raise store.ApiError("No picture was received")
    ext = ""
    for sig, e in SIGS:
        if data.startswith(sig):
            ext = e
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = ".webp"
    if not ext:
        raise store.ApiError("Please choose a JPG, PNG, WebP, GIF or PDF file")
    name = secrets.token_hex(10) + ext
    with open(os.path.join(store.UPLOADS, name), "wb") as fh:
        fh.write(data)
    return (201, {"file": name, "url": "/files/" + name})


@route("POST", "/api/backup/run")
def backup_run(h):
    import backup
    out = backup.run_backup()
    out["status"] = backup.status()
    return out


@route("GET", "/api/backup/status")
def backup_status(h):
    import backup
    return backup.status()


def lan_urls():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass
    return ["http://%s:%d" % (ip, STATE["port"]) for ip in ips if ip and not ip.startswith("169.254.") and ip != "0.0.0.0"]


@route("GET", "/api/network")
def network(h):
    return {"port": STATE["port"], "urls": lan_urls(), "local": "http://localhost:%d" % STATE["port"], "data": store.DATA}


@route("GET", "/api/publish.zip")
def publish_zip(h):
    import publish
    return Raw(publish.site_zip(), "application/zip", 200, {"Content-Disposition": 'attachment; filename="my-portfolio-site.zip"'})


@route("POST", "/api/shutdown")
def shutdown(h):
    def later():
        time.sleep(0.4)
        STATE["stop"].set()
        if STATE["server"]:
            STATE["server"].shutdown()
    threading.Thread(target=later, daemon=True).start()
    return {"ok": True}


# ====================================================================== startup
def say(*a):
    try:
        print(*a, flush=True)
    except Exception:
        pass


def already_running(start=8501, end=8510):
    for port in range(start, end + 1):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % port, timeout=0.8) as r:
                if json.loads(r.read().decode()).get("app") == "APIS":
                    return port
        except Exception:
            continue
    return 0


def setup_logging():
    os.makedirs(store.DATA, exist_ok=True)
    root = logging.getLogger("apis")
    root.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(os.path.join(store.DATA, "apis.log"), maxBytes=500_000, backupCount=2, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root.addHandler(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--data", default="")
    ap.add_argument("--reset-pin", action="store_true")
    args = ap.parse_args()
    if args.data:
        store.DATA = os.path.abspath(args.data)
        store.DB_PATH = os.path.join(store.DATA, "apis.db")
        store.UPLOADS = os.path.join(store.DATA, "uploads")
        store.BACKUPS = os.path.join(store.DATA, "backups")
        store.SECRETS_PATH = os.path.join(store.DATA, "secrets.json")

    if args.reset_pin:
        import getpass
        store.connect()
        new = getpass.getpass("Type a new PIN (4 or more characters), then press Enter: ").strip()
        try:
            store.set_pin(new)
        except store.ApiError as e:
            print(e.message)
            return 1
        store.end_session(everywhere=True)
        print("Your PIN was changed. Your records were not touched. Now start APIS as usual.")
        return 0

    running = already_running()
    if running and not args.data:
        say("APIS is already running. Opening it now.")
        if not args.no_browser:
            webbrowser.open("http://localhost:%d" % running)
        return 0

    setup_logging()
    store.connect()
    import seed
    seed.run_if_needed()
    start = args.port or int(store.get_setting("port") or 8501)
    server = None
    for port in range(start, start + 10):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
            STATE["port"] = port
            break
        except OSError:
            continue
    if server is None:
        say("APIS could not start: ports %d to %d are all in use." % (start, start + 9))
        log.error("No free port")
        return 1
    server.daemon_threads = True
    STATE["server"] = server
    STATE["shutdown_token"] = secrets.token_hex(16)
    with open(os.path.join(store.DATA, "shutdown.token"), "w") as fh:
        fh.write(STATE["shutdown_token"])
    with open(os.path.join(store.DATA, "port.txt"), "w") as fh:
        fh.write(str(STATE["port"]))

    import backup
    import reports
    reports.start_scheduler(STATE["stop"])
    backup.start_backups(STATE["stop"])

    urls = lan_urls()
    say("")
    say("  APIS is running.")
    say("  On this laptop:   http://localhost:%d" % STATE["port"])
    for u in urls[:2]:
        say("  On phone/tablet:  %s   (same Wi-Fi)" % u)
    say("")
    say("  Keep this window open. You can minimize it.")
    log.info("APIS %s started on port %d", store.VERSION, STATE["port"])
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open("http://localhost:%d" % STATE["port"])).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STATE["stop"].set()
        server.server_close()
        store.close()
        for f in ("shutdown.token", "port.txt"):
            try:
                os.remove(os.path.join(store.DATA, f))
            except OSError:
                pass
        log.info("APIS stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
