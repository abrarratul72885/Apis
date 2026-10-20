"""EOD report text, Excel exports, Gmail sending and the built-in scheduler."""
import datetime as dt
import logging
import re
import smtplib
import socket
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

import store
import xlsx

log = logging.getLogger("apis")


def money(n, symbol=None):
    symbol = store.get_setting("currency") if symbol is None else symbol
    n = int(round(n or 0))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    return ("-" if n < 0 else "") + symbol + s


def nice_date(day):
    d = dt.datetime.strptime(day, "%Y-%m-%d")
    return d.strftime("%A %d %B %Y")


# ------------------------------------------------------------------ summary
def build_summary(day):
    prof = store.get_profile()
    name = prof.get("name") or "APIS"
    logs = store.q("SELECT * FROM logs WHERE date=? ORDER BY created_at", (day,))
    done = [x for x in logs if x["status"] == "Completed"]
    still = [x for x in logs if x["status"] != "Completed"]
    carry = store.q("SELECT * FROM logs WHERE status<>'Completed' AND date<? ORDER BY date DESC LIMIT 8", (day,))
    terr = store.territory_summary(day, day)
    terr_rows = store.q("SELECT * FROM territory WHERE date=?", (day,))
    thr = store.get_setting("alert_threshold")
    stages = {s: 0 for s in store.STAGES}
    for l in store.q("SELECT stage FROM leads"):
        stages[l["stage"]] += 1
    moved = store.q(
        "SELECT e.to_stage, e.from_stage, l.company FROM lead_events e JOIN leads l ON l.id=e.lead_id "
        "WHERE substr(e.at,1,10)=? ORDER BY e.at", (day,))
    due = store.q("SELECT company, next_action, next_action_date FROM leads WHERE next_action_date<>'' AND next_action_date<=? AND stage<>'Sanctioned' ORDER BY next_action_date", (day,))
    hours = round(sum(x["hours"] or 0 for x in logs), 1)

    t = ["EOD report - " + nice_date(day), name, ""]
    t.append("Completed (%d)" % len(done))
    t += ["- [%s] %s%s" % (x["impact"], x["title"], (" - " + x["result"]) if x["result"] else "") for x in done] or ["- Nothing marked complete"]
    t += ["", "Still open (%d)" % len(still)]
    t += ["- (%s) %s" % (x["status"], x["title"]) for x in still] or ["- Nothing open from today"]
    if carry:
        t += ["", "Carried over from earlier days"]
        t += ["- (%s, %s) %s" % (x["status"], x["date"], x["title"]) for x in carry]
    if terr_rows:
        t += ["", "Territory performance",
              "Actual %s against target %s (%s%%)" % (money(terr["actual"]), money(terr["target"]), round(terr["pct"] or 0))]
        for s in terr["routes"]:
            flag = "  <- below %d%% target" % thr if s["pct"] is not None and s["pct"] < thr else ""
            t.append("- %s (%s): %s of %s, %s%%%s" % (s["route"], s["territory"], money(s["actual"]), money(s["target"]), round(s["pct"] or 0), flag))
        for r in terr_rows:
            if r["stock_out"]:
                t.append("- STOCK-OUT on %s: %s" % (r["route"], r["stock_out_items"] or "items not listed"))
    lead_total = sum(stages.values())
    if lead_total:
        t += ["", "Client pipeline",
              "%d client%s: %s" % (lead_total, "" if lead_total == 1 else "s", ", ".join("%s %d" % (k, v) for k, v in stages.items()))]
        for m in moved:
            t.append(("- New client today: %s" % m["company"]) if not m["from_stage"] else "- Moved today: %s (%s to %s)" % (m["company"], m["from_stage"], m["to_stage"]))
        for d in due[:6]:
            t.append("- Follow-up due: %s - %s (%s)" % (d["company"], d["next_action"] or "next step", d["next_action_date"]))
    t += ["", "Hours logged: %s" % hours]
    text = "\n".join(t)

    def li(items):
        return "".join("<li style='margin:4px 0'>%s</li>" % i for i in items) or "<li style='color:#6e6e73'>None</li>"

    h = ["<div style='font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:640px;margin:0 auto;color:#1d1d1f'>",
         "<div style='background:#0b57d0;color:#fff;padding:20px 24px;border-radius:14px 14px 0 0'>",
         "<div style='font-size:13px;opacity:.85'>End-of-day report</div>",
         "<div style='font-size:22px;font-weight:700;margin-top:2px'>%s</div>" % escape(nice_date(day)),
         "<div style='font-size:14px;opacity:.9;margin-top:2px'>%s</div></div>" % escape(name),
         "<div style='background:#f5f5f7;padding:20px 24px;border-radius:0 0 14px 14px;font-size:14px;line-height:1.5'>"]
    h.append("<h3 style='margin:0 0 6px;font-size:15px'>Completed (%d)</h3><ul style='margin:0 0 16px;padding-left:20px'>%s</ul>" % (
        len(done), li(["<b>[%s]</b> %s%s" % (escape(x["impact"]), escape(x["title"]), (" &mdash; " + escape(x["result"])) if x["result"] else "") for x in done])))
    h.append("<h3 style='margin:0 0 6px;font-size:15px'>Still open (%d)</h3><ul style='margin:0 0 16px;padding-left:20px'>%s</ul>" % (
        len(still), li(["(%s) %s" % (escape(x["status"]), escape(x["title"])) for x in still])))
    if terr_rows:
        rows = []
        for s in terr["routes"]:
            low = s["pct"] is not None and s["pct"] < thr
            rows.append("<li>%s (%s): %s of %s &mdash; <b style='color:%s'>%s%%</b></li>" % (
                escape(s["route"]), escape(s["territory"]), money(s["actual"]), money(s["target"]), "#c5221f" if low else "#137333", round(s["pct"] or 0)))
        for r in terr_rows:
            if r["stock_out"]:
                rows.append("<li style='color:#c5221f'>Stock-out on %s: %s</li>" % (escape(r["route"]), escape(r["stock_out_items"] or "items not listed")))
        h.append("<h3 style='margin:0 0 6px;font-size:15px'>Territory: %s of %s (%s%%)</h3><ul style='margin:0 0 16px;padding-left:20px'>%s</ul>" % (
            money(terr["actual"]), money(terr["target"]), round(terr["pct"] or 0), "".join(rows)))
    if lead_total:
        rows = ["<li>%d client%s: %s</li>" % (lead_total, "" if lead_total == 1 else "s", escape(", ".join("%s %d" % (k, v) for k, v in stages.items())))]
        rows += [("<li>New client today: %s</li>" % escape(m["company"])) if not m["from_stage"] else
                 "<li>Moved today: %s (%s to %s)</li>" % (escape(m["company"]), escape(m["from_stage"]), escape(m["to_stage"])) for m in moved]
        rows += ["<li>Follow-up due: %s &mdash; %s (%s)</li>" % (escape(d["company"]), escape(d["next_action"] or "next step"), escape(d["next_action_date"])) for d in due[:6]]
        h.append("<h3 style='margin:0 0 6px;font-size:15px'>Client pipeline</h3><ul style='margin:0 0 16px;padding-left:20px'>%s</ul>" % "".join(rows))
    h.append("<div style='color:#6e6e73;font-size:13px'>Hours logged: %s</div></div></div>" % hours)

    subject = (store.get_setting("subject_template") or "EOD report - {date}").format(date=day, name=name)
    return {"subject": subject, "text": text, "html": "".join(h),
            "stats": {"done": len(done), "open": len(still), "hours": hours, "routes": len(terr["routes"]),
                      "has_data": bool(logs or terr_rows or moved)}}


# ------------------------------------------------------------------ Excel
LOG_COLS = [("date", "Date"), ("category", "Category"), ("title", "Title"), ("description", "Description"), ("location", "Client or location"),
            ("impact", "Impact"), ("status", "Status"), ("hours", "Hours"), ("result", "Result"), ("created_at", "Logged at")]
TERR_COLS = [("date", "Date"), ("territory", "Territory"), ("route", "Route"), ("distributor", "Distributor"), ("target", "Target"),
             ("actual", "Actual"), ("stock_out", "Stock-out"), ("stock_out_items", "Stock-out items"), ("remarks", "Remarks")]


def _sheet(name, table, cols, where="", args=(), order="rowid"):
    rows = store.q("SELECT * FROM %s %s ORDER BY %s" % (table, where, order), args)
    out = []
    for r in rows:
        line = []
        for key, _label in cols:
            v = r.get(key)
            if key == "stock_out":
                v = "Yes" if v else "No"
            line.append(v)
        out.append(line)
    return (name, [c[1] for c in cols], out)


def workbook_bytes(scope="today", day=None):
    day = day or store.today()
    sheets = []
    if scope == "all":
        sheets.append(_sheet("Daily_Logs", "logs", LOG_COLS, order="date, created_at"))
        sheets.append(_sheet("Territory_Metrics", "territory", TERR_COLS, order="date, created_at"))
        sheets.append(_sheet("Pipeline", "leads", [("company", "Company"), ("contact", "Contact"), ("product", "Product"), ("amount", "Amount"),
                                                   ("stage", "Stage"), ("stage_since", "In stage since"), ("next_action", "Next action"),
                                                   ("next_action_date", "Next action date"), ("notes", "Notes")], order="created_at"))
        docs = store.q("SELECT d.*, l.company FROM lead_docs d JOIN leads l ON l.id=d.lead_id ORDER BY l.company, d.rowid")
        sheets.append(("Doc_Checklist", ["Company", "Document", "Required", "Received", "Verified", "Received date", "Expiry date", "Note"],
                       [[d["company"], d["doc"], "Yes" if d["required"] else "No", "Yes" if d["received"] else "No",
                         "Yes" if d["verified"] else "No", d["received_date"], d["expiry_date"], d["note"]] for d in docs]))
        sheets.append(_sheet("Appraisal_Log", "appraisal", [("seq", "No."), ("date", "Date"), ("title", "Title"), ("impact", "Impact"),
                                                            ("result", "Result"), ("logged_at", "Logged at"), ("hash", "Fingerprint")], order="seq"))
        p = store.get_profile()
        sheets.append(("Profile", ["Field", "Value"], [[k, v] for k, v in p.items() if k not in ("avatar", "cover")]))
        sheets.append(_sheet("Experience", "experience", [("org", "Organisation"), ("role", "Role"), ("kind", "Type"), ("start", "Start"), ("end", "End"),
                                                          ("location", "Location"), ("description", "Description")], order='"start" DESC'))
        sheets.append(_sheet("Education", "education", [("school", "School"), ("degree", "Degree"), ("field", "Field"), ("start", "Start"),
                                                        ("end", "End"), ("grade", "Grade")], order='"start" DESC'))
        sheets.append(_sheet("Certifications", "certs", [("title", "Title"), ("issuer", "Issuer"), ("issued", "Issued"), ("credential_id", "Credential ID"),
                                                         ("url", "Link"), ("skills", "Skills")], order="issued DESC"))
        sheets.append(_sheet("Skills", "skills", [("name", "Skill"), ("category", "Category")], order="category, name"))
        sheets.append(_sheet("Posts", "posts", [("posted_at", "Posted"), ("visibility", "Visibility"), ("caption", "Caption"), ("tags", "Tags")], order="posted_at DESC"))
    else:
        sheets.append(_sheet("Daily_Logs", "logs", LOG_COLS, "WHERE date=?", (day,), "created_at"))
        sheets.append(_sheet("Territory_Metrics", "territory", TERR_COLS, "WHERE date=?", (day,), "created_at"))
    return xlsx.build(sheets)


# ------------------------------------------------------------------ sending
def mail_config():
    s = store.get_settings()
    pw = (store.read_secrets().get("gmail_app_password") or "").replace(" ", "")
    return s, pw


def mail_ready():
    s, pw = mail_config()
    return bool(s["gmail_address"] and pw)


def _send(msg, s, pw):
    try:
        if s["smtp_ssl"]:
            server = smtplib.SMTP_SSL(s["smtp_host"], s["smtp_port"], timeout=30, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(s["smtp_host"], s["smtp_port"], timeout=30)
            if s["smtp_port"] == 587:
                server.starttls(context=ssl.create_default_context())
        try:
            if pw:
                server.login(s["gmail_address"], pw)
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except smtplib.SMTPAuthenticationError:
        raise store.ApiError("Gmail did not accept the App Password. Create a new one in your Google account and paste it again, without spaces.")
    except smtplib.SMTPRecipientsRefused:
        raise store.ApiError("Gmail refused one of the recipient addresses. Check the 'Send reports to' list.")
    except (socket.gaierror, socket.timeout, ConnectionError, TimeoutError):
        raise store.ApiError("Could not reach Gmail. Check that this laptop is online and try again.")
    except (smtplib.SMTPException, ssl.SSLError, OSError) as e:
        raise store.ApiError("Gmail could not send the email: %s" % e)


def _record(day, trigger, to, subject, ok, error=""):
    store.run("INSERT INTO sends(id,at,day,trigger,to_list,subject,ok,error) VALUES (?,?,?,?,?,?,?,?)",
              (store.new_id(), store.now().strftime("%Y-%m-%d %H:%M:%S"), day, trigger, to, subject, 1 if ok else 0, error))


def send_test():
    s, pw = mail_config()
    if not s["gmail_address"] or not pw:
        raise store.ApiError("Add your Gmail address and App Password first.")
    msg = EmailMessage()
    msg["From"] = s["gmail_address"]
    msg["To"] = s["gmail_address"]
    msg["Subject"] = "APIS test email"
    msg.set_content("Gmail is connected to APIS. Your end-of-day reports will be sent from this address.")
    _send(msg, s, pw)
    return {"ok": True, "to": s["gmail_address"]}


def send_report(day=None, trigger="manual"):
    day = day or store.today()
    s, pw = mail_config()
    if not s["gmail_address"] or not pw:
        raise store.ApiError("Connect Gmail first: add your address and App Password in Settings.")
    recipients = [a.strip() for a in s["report_to"].split(",") if a.strip()]
    if not recipients:
        raise store.ApiError("Add at least one address under 'Send reports to' in Settings.")
    summary = build_summary(day)
    prof = store.get_profile()
    msg = EmailMessage()
    msg["From"] = formataddr((prof.get("name") or "APIS", s["gmail_address"]))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = summary["subject"]
    msg.set_content(summary["text"])
    msg.add_alternative(summary["html"], subtype="html")
    if s["attach_excel"]:
        scope = "all" if s["attach_full"] else "today"
        msg.add_attachment(workbook_bytes(scope, day), maintype="application",
                           subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           filename="APIS_EOD_%s.xlsx" % day if scope == "today" else "apis_data_%s.xlsx" % day)
    try:
        _send(msg, s, pw)
    except store.ApiError as e:
        _record(day, trigger, ", ".join(recipients), summary["subject"], False, e.message)
        raise
    _record(day, trigger, ", ".join(recipients), summary["subject"], True)
    return {"ok": True, "to": recipients, "subject": summary["subject"]}


def sends_list():
    return store.q("SELECT * FROM sends ORDER BY at DESC LIMIT 40")


# ------------------------------------------------------------------ scheduler
def _sent_today():
    return bool(store.q1("SELECT 1 FROM sends WHERE day=? AND ok=1", (store.today(),)))


def next_run():
    s = store.get_settings()
    if not s["eod_enabled"] or not s["eod_days"]:
        return ""
    hh, mm = [int(x) for x in s["eod_time"].split(":")]
    n = store.now()
    for add in range(0, 8):
        d = (n + dt.timedelta(days=add)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if d.weekday() in s["eod_days"] and (d > n or (add == 0 and not _sent_today() and s["eod_catch_up"])):
            return d.strftime("%Y-%m-%d %H:%M")
    return ""


def due_now():
    s = store.get_settings()
    if not s["eod_enabled"] or not mail_ready():
        return False
    n = store.now()
    if n.weekday() not in s["eod_days"]:
        return False
    hh, mm = [int(x) for x in s["eod_time"].split(":")]
    sched = n.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if n < sched:
        return False
    if not s["eod_catch_up"] and (n - sched) > dt.timedelta(minutes=20):
        return False
    if _sent_today():
        return False
    last = store.q1("SELECT at FROM sends WHERE day=? AND trigger='auto' ORDER BY at DESC LIMIT 1", (store.today(),))
    if last and (n - dt.datetime.strptime(last["at"], "%Y-%m-%d %H:%M:%S")) < dt.timedelta(minutes=10):
        return False
    tries = store.q1("SELECT COUNT(*) AS c FROM sends WHERE day=? AND trigger='auto' AND ok=0", (store.today(),))["c"]
    if tries >= 4:
        return False
    return build_summary(store.today())["stats"]["has_data"]


def scheduler_tick():
    if due_now():
        try:
            send_report(store.today(), "auto")
            log.info("Automatic EOD report sent")
        except store.ApiError as e:
            log.warning("Automatic EOD report failed: %s", e.message)
        except Exception:
            log.exception("Automatic EOD report crashed")


def start_scheduler(stop_event):
    def loop():
        while not stop_event.is_set():
            try:
                scheduler_tick()
            except Exception:
                log.exception("Scheduler error")
            stop_event.wait(30)
    t = threading.Thread(target=loop, name="apis-scheduler", daemon=True)
    t.start()
    return t
