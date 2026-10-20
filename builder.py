"""Portfolio Builder: picks and arranges your saved records into a clean 2-3 page document.
Nothing is invented and your saved records are never changed: this only reads them."""
import base64
import io
import math
import os
import re
import zipfile
from html import escape

import publish
import store

SECTION_TITLES = {"summary": "Profile", "experience": "Experience and leadership", "education": "Education", "projects": "Projects",
                  "certifications": "Certifications", "achievements": "Achievements", "skills": "Skills", "links": "Links"}
DEFAULT_ORDER = ["summary", "experience", "education", "projects", "certifications", "achievements", "skills", "links"]
TEMPLATES = {
    "modern": {"label": "Modern corporate", "accent": "#0a57cc"},
    "minimal": {"label": "Minimal professional", "accent": "#222222"},
    "marketing": {"label": "Marketing focus", "accent": "#e8590c"},
}
PURPOSES = {
    "general": {"label": "General portfolio", "words": []},
    "sales": {"label": "Sales role", "words": ["sales", "territory", "sell", "customer", "field", "distribution", "target", "revenue", "negotiat", "retail", "route"]},
    "marketing": {"label": "Marketing role", "words": ["marketing", "brand", "campaign", "consumer", "digital", "social", "content", "research", "promotion", "event"]},
    "analytics": {"label": "Business analysis role", "words": ["data", "excel", "sql", "python", "power bi", "analysis", "analytics", "report", "dashboard", "research"]},
    "banking": {"label": "Banking or finance role", "words": ["bank", "finance", "credit", "loan", "deposit", "audit", "account", "risk", "compliance", "customer"]},
}
LINES_PER_PAGE = 40


def default_config():
    return {"template": "modern", "accent": "", "font": "sans", "purpose": "general", "pages": 3, "detail": "standard", "fit": True,
            "photo": True, "logos": True, "cover": False, "numbers": True, "summary": "", "headline": "",
            "contact": {"email": True, "phone": False, "location": True, "links": True},
            "sections": [{"key": k, "on": k != "links"} for k in DEFAULT_ORDER],
            "exclude": {}, "link_ids": None}


def _cfg(c):
    d = default_config()
    c = c or {}
    for k in ("template", "accent", "font", "purpose", "detail", "summary", "headline"):
        if isinstance(c.get(k), str):
            d[k] = c[k][:2000]
    if d["template"] not in TEMPLATES:
        d["template"] = "modern"
    if d["purpose"] not in PURPOSES:
        d["purpose"] = "general"
    if d["detail"] not in ("brief", "standard", "full"):
        d["detail"] = "standard"
    if d["font"] not in ("sans", "serif"):
        d["font"] = "sans"
    if not re.match(r"^#[0-9a-fA-F]{6}$", d["accent"] or ""):
        d["accent"] = TEMPLATES[d["template"]]["accent"]
    d["pages"] = 2 if str(c.get("pages")) == "2" else 3
    for k in ("fit", "photo", "logos", "cover", "numbers"):
        if k in c:
            d[k] = bool(c[k])
    if isinstance(c.get("contact"), dict):
        for k in d["contact"]:
            if k in c["contact"]:
                d["contact"][k] = bool(c["contact"][k])
    if isinstance(c.get("sections"), list):
        seen, out = set(), []
        for s in c["sections"]:
            if isinstance(s, dict) and s.get("key") in SECTION_TITLES and s["key"] not in seen:
                seen.add(s["key"])
                out.append({"key": s["key"], "on": bool(s.get("on"))})
        for k in DEFAULT_ORDER:
            if k not in seen:
                out.append({"key": k, "on": k != "links"})
        d["sections"] = out
    if isinstance(c.get("exclude"), dict):
        d["exclude"] = {k: [str(x) for x in v][:500] for k, v in c["exclude"].items() if isinstance(v, list)}
    if isinstance(c.get("link_ids"), list):
        d["link_ids"] = [str(x) for x in c["link_ids"]]
    return d


# ---------------------------------------------------------------- text helpers
def sentences(text):
    out = []
    for block in re.split(r"\n+", (text or "").strip()):
        block = re.sub(r"^[\-•*\s]+", "", block.strip())
        if not block:
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", block):
            s = s.strip()
            if s:
                out.append(s)
    return out


def _score(text, words, recent_rank):
    t = (text or "").lower()
    hits = sum(1 for w in words if w in t)
    return hits * 3 + max(0, 6 - recent_rank) * 0.5


def _bullets(text, detail):
    n = {"brief": 1, "standard": 3, "full": 99}[detail]
    return sentences(text)[:n]


def _short_summary(about, limit=460):
    out, total = [], 0
    for s in sentences(about):
        if total + len(s) > limit and out:
            break
        out.append(s)
        total += len(s) + 1
    return " ".join(out)


# ---------------------------------------------------------------- assemble
def _items(cfg, data):
    """Every candidate record, shaped the same way, with a relevance score."""
    words = PURPOSES[cfg["purpose"]]["words"]
    ex = cfg["exclude"]

    def keep(ent, it):
        return it["id"] not in ex.get(ent, [])

    def pack(ent, it, title, sub, date, desc, logo, tags="", link=""):
        return {"ent": ent, "id": it["id"], "title": title, "sub": sub, "date": date, "desc": desc or "", "logo": logo or "", "tags": tags, "link": link}

    out = {k: [] for k in DEFAULT_ORDER}
    for i, e in enumerate([x for x in data["exp"] if keep("experience", x)]):
        it = pack("experience", e, e["role"], e["org"] + ((" · " + e["location"]) if e["location"] else ""), publish.span(e["start"], e["end"]), e["description"], e["image"], e["skills"])
        it["score"] = _score(e["role"] + " " + e["org"] + " " + e["description"] + " " + e["skills"], words, i) + 2
        out["experience"].append(it)
    for i, e in enumerate([x for x in data["edu"] if keep("education", x)]):
        line = ", ".join(x for x in (e["degree"], e["field"]) if x)
        d = publish.span(e["start"], e["end"])
        it = pack("education", e, e["school"], line + ((" · " + e["grade"]) if e["grade"] else ""), d, e["description"], e["image"])
        it["score"] = 100
        out["education"].append(it)
    for i, e in enumerate([x for x in data["projects"] if keep("projects", x)]):
        parts = [e["summary"], ("Problem: " + e["problem"]) if e["problem"] else "", ("Methods: " + e["methods"]) if e["methods"] else "", ("Results: " + e["results"]) if e["results"] else ""]
        it = pack("projects", e, e["title"], " · ".join(x for x in (e["kind"], e["org"], e["role"]) if x), publish.span(e["start"], e["end"]) if e["start"] else "", "\n".join(p for p in parts if p), e["image"], e["tags"], e["link"])
        it["score"] = _score(" ".join(parts) + e["title"] + e["tags"], words, i) + 1.5
        out["projects"].append(it)
    for i, e in enumerate([x for x in data["certs"] if keep("certifications", x)]):
        it = pack("certifications", e, e["title"], e["issuer"], publish.fmt_month(e["issued"]), e["description"], e["image"], e["skills"], e["url"])
        it["score"] = _score(e["title"] + " " + e["skills"] + " " + e["issuer"], words, i)
        out["certifications"].append(it)
    for i, e in enumerate([x for x in data["achievements"] if keep("achievements", x)]):
        it = pack("achievements", e, e["title"], " · ".join(x for x in (e["kind"], e["org"]) if x), publish.fmt_month(e["date"]), e["description"], e["image"], "", e["link"])
        it["score"] = _score(e["title"] + " " + e["description"], words, i) + 1
        out["achievements"].append(it)
    out["skills"] = [{"ent": "skills", "id": s["id"], "title": s["name"], "category": s["category"], "score": _score(s["name"], words, 9)} for s in data["skills"] if keep("skills", s)]
    return out


def _lines(it, detail, cpl):
    if it.get("ent") == "skills":
        return 0
    n = 1.0 + (0.4 if it["sub"] and len(it["sub"]) + len(it["date"]) > cpl - 10 else 0)
    for b in _bullets(it["desc"], detail):
        n += math.ceil((len(b) + 3) / (cpl - 6))
    return n + 0.55


def assemble(config):
    cfg = _cfg(config)
    data = publish._data()
    data["projects"] = store.list_items("projects")
    data["achievements"] = store.list_items("achievements")
    data["links"] = store.list_items("links")
    p = data["p"]
    items = _items(cfg, data)
    order = [s["key"] for s in cfg["sections"] if s["on"]]
    notes, dropped = [], []
    summary = (cfg["summary"].strip() or _short_summary(p["about"]))
    detail = cfg["detail"]
    compact = False
    budget_pages = cfg["pages"]

    def total(detail_, compact_):
        cpl = 118 if compact_ else 104
        lpp = LINES_PER_PAGE * (1.14 if compact_ else 1.0)
        used = 7.0 if cfg["template"] != "minimal" else 6.0
        if "summary" in order and summary:
            used += 2 + math.ceil(len(summary) / cpl)
        for k in order:
            if k in ("summary", "skills", "links"):
                continue
            if items[k]:
                used += 2.2
            for it in items[k]:
                if not it.get("drop"):
                    used += _lines(it, detail_, cpl)
        if "skills" in order and any(not s.get("drop") for s in items["skills"]):
            used += 2.2 + math.ceil(sum(len(s["title"]) + 3 for s in items["skills"] if not s.get("drop")) / cpl)
        if "links" in order:
            used += 3
        return used / lpp

    if cfg["fit"]:
        if total(detail, compact) > budget_pages:
            compact = True
            notes.append("Text size was tightened slightly to fit.")
        for lvl in ("full", "standard", "brief"):
            if total(detail, compact) <= budget_pages:
                break
            if detail != "brief" and (lvl == detail or (lvl == "standard" and detail == "full")):
                nd = "standard" if detail == "full" else "brief"
                if nd != detail:
                    detail = nd
                    notes.append("Long descriptions were shortened to their first sentences (nothing was reworded).")
        guard = 0
        while total(detail, compact) > budget_pages and guard < 200:
            guard += 1
            cands = []
            for k in order:
                if k in ("summary", "education", "links"):
                    continue
                live = [it for it in items[k] if not it.get("drop")]
                min_keep = 1 if k != "skills" else 8
                if len(live) > min_keep:
                    worst = min(live, key=lambda it: it["score"])
                    cands.append((worst["score"], k, worst))
            if not cands:
                break
            _s, k, worst = min(cands, key=lambda x: x[0])
            worst["drop"] = True
            dropped.append({"section": k, "title": worst["title"]})
    pages = total(detail, compact)
    sections = []
    for k in order:
        if k == "summary":
            if summary:
                sections.append({"key": k, "title": cfg_title(k), "text": summary})
        elif k == "skills":
            live = [s for s in items["skills"] if not s.get("drop")]
            if live:
                cats = {}
                for s in live:
                    cats.setdefault(s["category"] or "", []).append(s["title"])
                sections.append({"key": k, "title": cfg_title(k), "groups": [{"name": n, "items": v} for n, v in cats.items()]})
        elif k == "links":
            ls = [x for x in data["links"] if cfg["link_ids"] is None or x["id"] in cfg["link_ids"]]
            if ls:
                sections.append({"key": k, "title": cfg_title(k), "links": [{"label": x["label"] or x["kind"], "url": x["url"]} for x in ls]})
        else:
            live = [it for it in items[k] if not it.get("drop")]
            for it in live:
                it["bullets"] = _bullets(it["desc"], detail)
            if live:
                sections.append({"key": k, "title": cfg_title(k), "items": live})
    contact = []
    c = cfg["contact"]
    if c["email"] and p["email"]:
        contact.append(p["email"])
    if c["phone"] and p["phone"]:
        contact.append(p["phone"])
    if c["location"] and p["location"]:
        contact.append(p["location"])
    if c["links"]:
        if p["linkedin"]:
            contact.append(p["linkedin"])
        if "links" not in order:
            for x in data["links"][:3]:
                contact.append(x["url"])
    left = [s["key"] for s in cfg["sections"] if s["on"] and not any(x["key"] == s["key"] for x in sections)]
    return {"cfg": cfg, "name": p["name"], "headline": cfg["headline"].strip() or p["headline"], "contact": contact, "avatar": p["avatar"] if cfg["photo"] else "",
            "cover": p["cover"] if cfg["cover"] else "", "sections": sections, "dropped": dropped, "notes": notes, "pages": round(pages, 1),
            "pages_text": "about %d page%s" % (max(1, math.ceil(pages - 0.05)), "" if math.ceil(pages - 0.05) <= 1 else "s"),
            "compact": compact, "empty_sections": left}


def cfg_title(k):
    return SECTION_TITLES[k]


# ---------------------------------------------------------------- HTML
def _img_src(name, inline):
    if not name:
        return ""
    if not inline:
        return "/files/" + name
    path = os.path.join(store.UPLOADS, name)
    try:
        if os.path.getsize(path) > 1500000:
            return ""
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return ""
    mime = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(name.rsplit(".", 1)[-1], "image/jpeg")
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode())


def _css(cfg, compact):
    a = cfg["accent"]
    fam = '"Georgia","Cambria","Times New Roman",serif' if cfg["font"] == "serif" else '"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif'
    base = 9.4 if compact else 10.2
    t = cfg["template"]
    return """
@page{size:A4;margin:13mm 14mm}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:#e9e9ee;color:#1b1b1f;font:%(base)spt/1.42 %(fam)s}
.sheet{width:210mm;margin:18px auto;background:#fff;padding:13mm 14mm;box-shadow:0 8px 30px rgba(0,0,0,.18)}
.hd{display:flex;gap:16px;align-items:center;margin-bottom:8px;%(hdstyle)s}
.hd img.ph{width:25mm;height:25mm;border-radius:50%%;object-fit:cover;flex:none}
.hd h1{font-size:%(h1)spt;margin:0;line-height:1.1;letter-spacing:-.01em;%(h1c)s}
.hd .hl{font-size:%(hl)spt;color:%(hlc)s;font-weight:600;margin:3px 0 4px}
.hd .ct{font-size:%(sm)spt;color:#555}
.cover{height:18mm;border-radius:3mm;margin-bottom:6mm;background:linear-gradient(135deg,%(a)s,%(a)s99)}
h2{font-size:%(h2)spt;margin:%(h2m)s;%(h2s)s;break-after:avoid}
.it{break-inside:avoid;margin:0 0 %(gap)smm}
.row{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.row .t{font-weight:700}
.row .d{color:#666;font-size:%(sm)spt;white-space:nowrap}
.sub{color:#555;font-size:%(sm)spt;display:flex;gap:6px;align-items:center}
.sub img{width:5mm;height:5mm;object-fit:contain;border-radius:1mm}
ul{margin:1mm 0 0;padding-left:4.5mm}li{margin:0 0 .7mm}
p{margin:0 0 2mm}
.tags{color:#666;font-size:%(sm)spt;margin-top:.5mm}
.sk{margin:0 0 1.2mm}.sk b{font-weight:700}
.lk a{color:%(a)s;text-decoration:none;margin-right:5mm}
.bar{position:sticky;top:0;z-index:5;background:#1b1b1f;color:#fff;padding:10px 16px;display:flex;justify-content:space-between;align-items:center;font:14px %(sans)s}
.bar button{background:#fff;color:#111;border:0;border-radius:999px;padding:8px 18px;font-weight:700;cursor:pointer}
@media print{body{background:#fff}.sheet{margin:0;padding:0;box-shadow:none;width:auto}.bar{display:none}}
@media (max-width:820px){.sheet{width:auto;margin:0;padding:16px}}
""" % {"base": base, "fam": fam, "sans": '"Segoe UI",Roboto,Arial,sans-serif', "a": a, "sm": base - 1.1,
       "h1": 22 if t != "minimal" else 20, "hl": base + 1.6, "hlc": a if t != "minimal" else "#333",
       "h1c": "" if t != "marketing" else "color:%s" % a,
       "hdstyle": "padding-bottom:4mm;border-bottom:2px solid %s" % a if t == "modern" else ("padding-bottom:3mm;border-bottom:1px solid #999" if t == "minimal" else "padding:4mm;background:%s14;border-radius:3mm" % a),
       "h2": base + 1.8 if t != "minimal" else base + 0.8,
       "h2m": "5mm 0 2.4mm",
       "h2s": ("color:%s;border-bottom:1.5px solid %s;padding-bottom:1mm" % (a, a)) if t == "modern" else
              ("text-transform:uppercase;letter-spacing:.12em;font-size:%spt;border-bottom:1px solid #bbb;padding-bottom:1mm" % (base - 0.4) if t == "minimal" else
               "color:#fff;background:%s;padding:1mm 3mm;border-radius:1.5mm" % a),
       "gap": 2.4 if compact else 3.2}


def render_html(doc, inline_images=False, toolbar=True, print_now=False):
    cfg = doc["cfg"]
    o = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>%s - Portfolio</title><style>%s</style></head><body>" % (
        escape(doc["name"]), _css(cfg, doc["compact"]))]
    if toolbar:
        o.append("<div class='bar'><span>Choose \"Save as PDF\" as the printer, margins Default, and turn off Headers and footers.</span><button data-print='1'>Print or save as PDF</button></div>")
    o.append("<div class='sheet'>")
    if doc["cover"]:
        o.append("<div class='cover'></div>")
    o.append("<div class='hd'>")
    src = _img_src(doc["avatar"], inline_images)
    if src:
        o.append("<img class='ph' src='%s' alt=''>" % src)
    o.append("<div><h1>%s</h1><div class='hl'>%s</div><div class='ct'>%s</div></div></div>" % (
        escape(doc["name"]), escape(doc["headline"]), " &middot; ".join(escape(x) for x in doc["contact"])))
    for s in doc["sections"]:
        o.append("<h2>%s</h2>" % escape(s["title"]))
        if s["key"] == "summary":
            o.append("<p>%s</p>" % escape(s["text"]))
        elif s["key"] == "skills":
            for g in s["groups"]:
                o.append("<div class='sk'>%s%s</div>" % (("<b>%s:</b> " % escape(g["name"])) if g["name"] else "", escape(", ".join(g["items"]))))
        elif s["key"] == "links":
            o.append("<div class='lk'>%s</div>" % "".join("<a href='%s'>%s</a>" % (escape(x["url"]), escape(x["label"])) for x in s["links"]))
        else:
            for it in s["items"]:
                o.append("<div class='it'><div class='row'><span class='t'>%s</span><span class='d'>%s</span></div>" % (escape(it["title"]), escape(it["date"])))
                logo = _img_src(it["logo"], inline_images) if cfg["logos"] else ""
                if it["sub"] or logo:
                    o.append("<div class='sub'>%s%s</div>" % ("<img src='%s' alt=''>" % logo if logo else "", escape(it["sub"])))
                if it["bullets"]:
                    o.append("<ul>%s</ul>" % "".join("<li>%s</li>" % escape(b) for b in it["bullets"]))
                if it.get("tags") and cfg["detail"] != "brief" and s["key"] in ("projects", "experience"):
                    o.append("<div class='tags'>%s</div>" % escape(it["tags"]))
                o.append("</div>")
    o.append("</div>")
    o.append("<script src='/js/print.js'></script>" if toolbar else "")
    o.append("</body></html>")
    return "".join(o)


# ---------------------------------------------------------------- DOCX
def _x(t):
    return escape(t or "", quote=False)


def _run(text, bold=False, size=None, color=None, italic=False):
    pr = ""
    if bold:
        pr += "<w:b/>"
    if italic:
        pr += "<w:i/>"
    if color:
        pr += '<w:color w:val="%s"/>' % color.lstrip("#")
    if size:
        pr += '<w:sz w:val="%d"/>' % int(size * 2)
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % ("<w:rPr>%s</w:rPr>" % pr if pr else "", _x(text))


def _para(runs, after=60, before=0, indent=0, hanging=0, border=None, keep=False, tabs=None):
    pr = '<w:spacing w:before="%d" w:after="%d"/>' % (before, after)
    if keep:
        pr = "<w:keepNext/>" + pr
    if border:
        pr = '<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="1" w:color="%s"/></w:pBdr>' % border.lstrip("#") + pr
    if tabs:
        pr = '<w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>' % tabs + pr
    if indent:
        pr += '<w:ind w:left="%d" w:hanging="%d"/>' % (indent, hanging)
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (pr, "".join(runs))


def render_docx(doc):
    a = doc["cfg"]["accent"]
    font = "Georgia" if doc["cfg"]["font"] == "serif" else "Calibri"
    body = [_para([_run(doc["name"], True, 22, a)], after=20),
            _para([_run(doc["headline"], True, 11.5, "444444")], after=20),
            _para([_run("  |  ".join(doc["contact"]), size=9.5, color="555555")], after=100)]
    for s in doc["sections"]:
        body.append(_para([_run(s["title"].upper(), True, 11, a)], before=160, after=70, border=a, keep=True))
        if s["key"] == "summary":
            body.append(_para([_run(s["text"], size=10.5)], after=60))
        elif s["key"] == "skills":
            for g in s["groups"]:
                r = ([_run(g["name"] + ": ", True, 10.5)] if g["name"] else []) + [_run(", ".join(g["items"]), size=10.5)]
                body.append(_para(r, after=40))
        elif s["key"] == "links":
            for x in s["links"]:
                body.append(_para([_run(x["label"] + ": ", True, 10.5), _run(x["url"], size=10.5)], after=30))
        else:
            for it in s["items"]:
                body.append(_para([_run(it["title"], True, 11), _run("\t" + it["date"], size=9.5, color="666666")], after=0, keep=True, tabs=10200))
                if it["sub"]:
                    body.append(_para([_run(it["sub"], size=9.5, color="555555")], after=20, keep=True))
                for b in it["bullets"]:
                    body.append(_para([_run("•  " + b, size=10.5)], after=20, indent=300, hanging=220))
                body.append(_para([], after=60))
    sect = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="720" w:right="800" w:bottom="720" w:left="800" w:header="400" w:footer="400" w:gutter="0"/></w:sectPr>'
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>%s%s</w:body></w:document>'
                % ("".join(body), sect))
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/><w:sz w:val="21"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>' % (font, font, font))
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)
    return buf.getvalue()


def options():
    return {"templates": [{"key": k, "label": v["label"], "accent": v["accent"]} for k, v in TEMPLATES.items()],
            "purposes": [{"key": k, "label": v["label"]} for k, v in PURPOSES.items()],
            "sections": [{"key": k, "label": v} for k, v in SECTION_TITLES.items()], "default": default_config()}
