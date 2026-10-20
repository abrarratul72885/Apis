"""Public portfolio page (a folder you can host for free) and the printable CV."""
import datetime as dt
import io
import os
import zipfile
from html import escape

import store

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_month(m):
    if not m:
        return ""
    y, mo = m.split("-")
    return "%s %s" % (MONTHS[int(mo) - 1], y)


def span(start, end):
    a = fmt_month(start)
    b = fmt_month(end) if end else "Present"
    return "%s - %s" % (a, b) if a else b


def duration(start, end):
    if not start:
        return ""
    sy, sm = [int(x) for x in start.split("-")]
    if end:
        ey, em = [int(x) for x in end.split("-")]
    else:
        n = dt.date.today()
        ey, em = n.year, n.month
    months = (ey - sy) * 12 + (em - sm) + 1
    if months < 1:
        return ""
    y, m = divmod(months, 12)
    parts = []
    if y:
        parts.append("%d yr%s" % (y, "" if y == 1 else "s"))
    if m:
        parts.append("%d mo%s" % (m, "" if m == 1 else "s"))
    return " ".join(parts)


def paras(text):
    text = (text or "").strip()
    if not text:
        return ""
    return "".join("<p>%s</p>" % escape(p).replace("\n", "<br>") for p in text.split("\n\n"))


def _group_experience(items):
    groups, order = {}, []
    for it in items:
        key = it["org"].strip().lower()
        if key not in groups:
            groups[key] = {"org": it["org"], "items": []}
            order.append(key)
        groups[key]["items"].append(it)
    return [groups[k] for k in order]


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--mute:#6e6e73;--line:rgba(0,0,0,.08);--blue:#0b57d0}
@media (prefers-color-scheme:dark){:root{--bg:#000;--card:#1c1c1e;--ink:#f5f5f7;--mute:#98989d;--line:rgba(255,255,255,.12);--blue:#4c8dff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI Variable","Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto;padding:0 16px 64px}
.cover{height:220px;border-radius:0 0 28px 28px;background:radial-gradient(900px 300px at 80% -20%,#4c8dff 0,transparent 60%),linear-gradient(135deg,#0b3d91,#0b57d0 55%,#3b82f6);background-size:cover;background-position:center}
.head{background:var(--card);border-radius:24px;margin-top:-64px;padding:0 28px 28px;position:relative;box-shadow:0 1px 0 var(--line),0 18px 40px -24px rgba(0,0,0,.25)}
.avatar{width:132px;height:132px;border-radius:50%;border:5px solid var(--card);object-fit:cover;margin-top:-66px;background:#ddd;display:block}
h1{font-size:30px;letter-spacing:-.02em;margin:14px 0 2px}.headline{color:var(--ink);margin:0 0 6px;font-size:17px}.meta{color:var(--mute);font-size:14px}
.meta a{color:var(--blue);text-decoration:none}
section{background:var(--card);border-radius:24px;padding:24px 28px;margin-top:16px;box-shadow:0 1px 0 var(--line)}
h2{font-size:21px;letter-spacing:-.01em;margin:0 0 14px}
p{margin:0 0 10px}.item{padding:14px 0;border-top:1px solid var(--line)}.item:first-of-type{border-top:0;padding-top:0}
.t{font-weight:600}.s{color:var(--mute);font-size:14px}
.org{font-weight:700;font-size:17px;margin-bottom:4px}.role{padding-left:14px;border-left:2px solid var(--line);margin:10px 0}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chip{background:var(--bg);border-radius:999px;padding:6px 12px;font-size:14px}
.post{padding:18px 0;border-top:1px solid var(--line)}.post:first-of-type{border-top:0;padding-top:0}
.photos{display:grid;gap:6px;margin-top:10px;border-radius:16px;overflow:hidden}.photos.n1{grid-template-columns:1fr}.photos.n2,.photos.n4{grid-template-columns:1fr 1fr}.photos.n3{grid-template-columns:2fr 1fr}
.photos img{width:100%;height:100%;object-fit:cover;display:block;max-height:420px}.photos.n3 img:first-child{grid-row:span 2}
.cert{display:flex;gap:14px;align-items:flex-start}.cert img{width:112px;height:80px;object-fit:cover;border-radius:10px;border:1px solid var(--line)}
a{color:var(--blue)}.foot{text-align:center;color:var(--mute);font-size:13px;margin-top:28px}
"""

CV_CSS = """
@page{size:A4;margin:14mm}
body{font:11pt/1.45 "Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#111;margin:0;background:#fff}
.page{max-width:780px;margin:0 auto;padding:24px}
h1{font-size:26pt;margin:0;letter-spacing:-.01em}.sub{color:#0b57d0;font-weight:600;margin:2px 0 4px}
.contact{color:#444;font-size:10pt;margin-bottom:10px}
h2{font-size:11pt;border-bottom:2px solid #0b57d0;padding-bottom:3px;margin:16px 0 8px;color:#0b57d0}
.row{display:flex;justify-content:space-between;gap:12px;font-weight:600}.row span:last-child{font-weight:400;color:#555;white-space:nowrap}
.sm{color:#444;font-size:10pt;margin:1px 0 6px}p{margin:2px 0 6px}
.toolbar{position:sticky;top:0;background:#0b57d0;color:#fff;padding:10px 16px;font:14px sans-serif;display:flex;justify-content:space-between;align-items:center}
.toolbar button{background:#fff;color:#0b57d0;border:0;border-radius:999px;padding:8px 16px;font-weight:600;cursor:pointer}
@media print{.toolbar{display:none}.page{padding:0}}
"""


def _data():
    return {
        "p": store.get_profile(),
        "exp": store.list_items("experience"),
        "edu": store.list_items("education"),
        "certs": store.list_items("certs"),
        "skills": store.list_items("skills"),
        "posts": store.list_items("posts"),
        "projects": store.list_items("projects"),
        "achievements": store.list_items("achievements"),
        "links": store.list_items("links"),
    }


def _img(prefix, name):
    return "%s%s" % (prefix, name) if name else ""


def site_html(img_prefix="img/", include_phone=False, data=None):
    d = data or _data()
    p = d["p"]
    posts = [x for x in d["posts"] if x["visibility"] == "public" and not x.get("archived")]
    cover = "style=\"background-image:url('%s')\"" % _img(img_prefix, p["cover"]) if p["cover"] else ""
    out = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>%s</title><meta name='description' content='%s'><style>%s</style></head><body>" % (
               escape(p["name"]), escape(p["headline"]), CSS)]
    out.append("<div class='cover' %s></div><div class='wrap'><div class='head'>" % cover)
    out.append("<img class='avatar' src='%s' alt=''>" % _img(img_prefix, p["avatar"]) if p["avatar"] else "<div class='avatar'></div>")
    out.append("<h1>%s</h1><p class='headline'>%s</p><div class='meta'>%s" % (escape(p["name"]), escape(p["headline"]), escape(p["location"])))
    links = []
    if p["email"]:
        links.append("<a href='mailto:%s'>%s</a>" % (escape(p["email"]), escape(p["email"])))
    if include_phone and p["phone"]:
        links.append(escape(p["phone"]))
    if p["linkedin"]:
        url = p["linkedin"] if p["linkedin"].startswith("http") else "https://" + p["linkedin"]
        links.append("<a href='%s' rel='noopener'>LinkedIn</a>" % escape(url))
    for lk in d.get("links", []):
        if lk["url"].startswith("http"):
            links.append("<a href='%s' rel='noopener'>%s</a>" % (escape(lk["url"]), escape(lk["label"] or lk["kind"])))
    if links:
        out.append(" &middot; " + " &middot; ".join(links))
    out.append("</div></div>")
    if p["about"]:
        out.append("<section><h2>About</h2>%s</section>" % paras(p["about"]))
    if posts:
        out.append("<section><h2>Activity</h2>")
        for x in posts:
            ph = x["photos"][:4]
            out.append("<div class='post'><div class='s'>%s</div>%s" % (escape(x["posted_at"][:10]), paras(x["caption"])))
            if ph:
                out.append("<div class='photos n%d'>%s</div>" % (len(ph), "".join("<img loading='lazy' src='%s' alt=''>" % _img(img_prefix, f) for f in ph)))
            out.append("</div>")
        out.append("</section>")
    if d["exp"]:
        out.append("<section><h2>Experience</h2>")
        for g in _group_experience(d["exp"]):
            out.append("<div class='item'><div class='org'>%s</div>" % escape(g["org"]))
            for it in g["items"]:
                dur = duration(it["start"], it["end"])
                out.append("<div class='role'><div class='t'>%s</div><div class='s'>%s &middot; %s%s%s</div>%s</div>" % (
                    escape(it["role"]), escape(it["kind"]), span(it["start"], it["end"]), (" &middot; " + dur) if dur else "",
                    (" &middot; " + escape(it["location"])) if it["location"] else "", paras(it["description"])))
            out.append("</div>")
        out.append("</section>")
    projs = [x for x in d.get("projects", []) if x["public"]]
    if projs:
        out.append("<section><h2>Projects</h2>")
        for x in projs:
            img = "<img src='%s' alt=''>" % _img(img_prefix, x["image"]) if x["image"] else ""
            link = " &middot; <a href='%s' rel='noopener'>Open</a>" % escape(x["link"]) if x["link"].startswith("http") else ""
            body = "".join(paras(t) for t in (x["summary"], ("Results: " + x["results"]) if x["results"] else ""))
            out.append("<div class='item cert'>%s<div><div class='t'>%s</div><div class='s'>%s%s</div>%s</div></div>" % (
                img, escape(x["title"]), escape(" \u00b7 ".join(v for v in (x["kind"], x["org"], x["role"]) if v)), link, body))
        out.append("</section>")
    achs = [x for x in d.get("achievements", []) if x["public"]]
    if achs:
        out.append("<section><h2>Achievements</h2>")
        for x in achs:
            out.append("<div class='item'><div class='t'>%s</div><div class='s'>%s %s</div>%s</div>" % (
                escape(x["title"]), escape(" \u00b7 ".join(v for v in (x["kind"], x["org"]) if v)), fmt_month(x["date"]), paras(x["description"])))
        out.append("</section>")
    if d["edu"]:
        out.append("<section><h2>Education</h2>")
        for e in d["edu"]:
            line = ", ".join(x for x in (e["degree"], e["field"]) if x)
            out.append("<div class='item'><div class='t'>%s</div><div class='s'>%s</div><div class='s'>%s%s</div>%s</div>" % (
                escape(e["school"]), escape(line), span(e["start"], e["end"]), (" &middot; " + escape(e["grade"])) if e["grade"] else "", paras(e["description"])))
        out.append("</section>")
    if d["certs"]:
        out.append("<section><h2>Licenses and certifications</h2>")
        for c in d["certs"]:
            img = "<img src='%s' alt=''>" % _img(img_prefix, c["image"]) if c["image"] else ""
            link = " &middot; <a href='%s' rel='noopener'>Show credential</a>" % escape(c["url"]) if c["url"].startswith("http") else ""
            out.append("<div class='item cert'>%s<div><div class='t'>%s</div><div class='s'>%s &middot; %s%s</div>%s</div></div>" % (
                img, escape(c["title"]), escape(c["issuer"]), fmt_month(c["issued"]), link, paras(c["description"])))
        out.append("</section>")
    if d["skills"]:
        out.append("<section><h2>Skills</h2><div class='chips'>%s</div></section>" % "".join("<span class='chip'>%s</span>" % escape(s["name"]) for s in d["skills"]))
    out.append("<div class='foot'>Made with APIS</div></div></body></html>")
    return "".join(out)


def cv_html():
    d = _data()
    p = d["p"]
    o = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>%s - CV</title><style>%s</style></head><body>" % (escape(p["name"]), CV_CSS),
         "<div class='toolbar'><span>Choose 'Save as PDF' in the print window</span><button data-print='1'>Print or save as PDF</button></div><script src='/js/print.js'></script>",
         "<div class='page'><h1>%s</h1><div class='sub'>%s</div>" % (escape(p["name"]), escape(p["headline"]))]
    contact = [x for x in (p["location"], p["email"], p["phone"], p["linkedin"]) if x]
    o.append("<div class='contact'>%s</div>" % " &middot; ".join(escape(x) for x in contact))
    if p["about"]:
        o.append("<h2>Summary</h2>%s" % paras(p["about"]))
    if d["edu"]:
        o.append("<h2>Education</h2>")
        for e in d["edu"]:
            line = ", ".join(x for x in (e["degree"], e["field"]) if x)
            o.append("<div class='row'><span>%s</span><span>%s</span></div><div class='sm'>%s%s</div>" % (
                escape(e["school"]), span(e["start"], e["end"]), escape(line), (" &middot; " + escape(e["grade"])) if e["grade"] else ""))
    if d["exp"]:
        o.append("<h2>Experience and leadership</h2>")
        for it in d["exp"]:
            o.append("<div class='row'><span>%s, %s</span><span>%s</span></div><div class='sm'>%s</div>%s" % (
                escape(it["role"]), escape(it["org"]), span(it["start"], it["end"]), escape(it["kind"]), paras(it["description"])))
    if d.get("projects"):
        o.append("<h2>Projects</h2>")
        for x in d["projects"]:
            o.append("<div class='row'><span>%s</span><span>%s</span></div><div class='sm'>%s</div>%s" % (
                escape(x["title"]), span(x["start"], x["end"]) if x["start"] else "", escape(" \u00b7 ".join(v for v in (x["kind"], x["org"], x["role"]) if v)), paras(x["summary"])))
    if d["certs"]:
        o.append("<h2>Certifications</h2>")
        for c in d["certs"]:
            o.append("<div class='row'><span>%s</span><span>%s</span></div><div class='sm'>%s</div>" % (escape(c["title"]), fmt_month(c["issued"]), escape(c["issuer"])))
    if d.get("achievements"):
        o.append("<h2>Achievements</h2>")
        for x in d["achievements"]:
            o.append("<div class='row'><span>%s</span><span>%s</span></div><div class='sm'>%s</div>%s" % (escape(x["title"]), fmt_month(x["date"]), escape(x["org"]), paras(x["description"])))
    if d["skills"]:
        o.append("<h2>Skills</h2><p>%s</p>" % escape(", ".join(s["name"] for s in d["skills"])))
    o.append("</div></body></html>")
    return "".join(o)


def site_zip():
    d = _data()
    html = site_html("img/", False, d)
    used = set()
    p = d["p"]
    for k in ("avatar", "cover"):
        if p[k]:
            used.add(p[k])
    for ent in ("certs", "edu", "exp"):
        for c in d[ent]:
            if c.get("image"):
                used.add(c["image"])
    for ent in ("projects", "achievements"):
        for c in d[ent]:
            if c["public"] and c["image"]:
                used.add(c["image"])
    for x in d["projects"]:
        if x["public"]:
            used.update(x["photos"][:4])
    for x in d["posts"]:
        if x["visibility"] == "public":
            used.update(x["photos"][:4])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", html)
        for name in sorted(used):
            path = os.path.join(store.UPLOADS, name)
            if os.path.isfile(path):
                z.write(path, "img/" + name)
        z.writestr("HOW TO PUT THIS ONLINE.txt",
                   "This folder is your public portfolio page. It only has the posts you marked Public.\r\n"
                   "Your phone number is not included.\r\n\r\n"
                   "Free way to put it online:\r\n"
                   "1. Unzip this file.\r\n"
                   "2. Open https://app.netlify.com/drop in your browser.\r\n"
                   "3. Drag the unzipped folder onto the page. You get a link you can share.\r\n"
                   "To update it later, download a new zip from APIS and drop it again.\r\n")
    return buf.getvalue()
