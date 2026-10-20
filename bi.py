"""Business Analysis Studio: reads .xlsx / .csv files (standard library only) and runs fixed, labelled formulas.
Original files are never changed. Every number comes from the functions below, never from a guess."""
import csv
import datetime as dt
import io
import json
import os
import re
import secrets
import threading
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict

import store
import xlsx as xlsxw

MAX_ROWS = 300000
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
RELNS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
LOCK = threading.RLock()
CACHE = OrderedDict()  # file id -> {sheet name -> rows}; small, keeps files from being re-read for every click
EXTS = (".xlsx", ".xlsm", ".csv")

FIELDS = [  # (key, label, synonyms)
    ("date", "Date", ["date", "reporting date", "day", "month", "period", "invoice date", "order date", "sales date"]),
    ("territory", "Territory", ["territory", "area", "region", "zone", "branch", "district"]),
    ("route", "Route", ["route", "beat", "route name", "route code"]),
    ("distributor", "Distributor", ["distributor", "dealer", "dist", "distributor name", "partner"]),
    ("salesperson", "Salesperson", ["salesperson", "sales officer", "so", "tso", "officer", "rep", "sales rep", "employee"]),
    ("outlet", "Outlet", ["outlet", "retailer", "shop", "store", "outlet id", "outlet name", "customer", "client"]),
    ("product", "Product", ["product", "sku", "item", "product name", "brand", "item name"]),
    ("category", "Category", ["category", "product category", "segment", "group", "class"]),
    ("target", "Target", ["target", "target sales", "plan", "budget", "goal", "target value"]),
    ("actual", "Actual", ["actual", "actual sales", "sales", "achievement", "revenue", "amount", "value", "sale value", "net sales", "deposit", "loan"]),
    ("stock_out", "Stock-out", ["stock out", "stockout", "stock-out", "out of stock", "oos"]),
]
FIELD_KEYS = [f[0] for f in FIELDS]
GROUPS = ["territory", "route", "distributor", "salesperson", "outlet", "product", "category"]
MONTH_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?")


class BIError(store.ApiError):
    pass


# --------------------------------------------------------------------------- storage
def _dir():
    d = os.path.join(store.DATA, "analysis_files")
    os.makedirs(d, exist_ok=True)
    return d


def _init():
    store.run("CREATE TABLE IF NOT EXISTS bi_files (id TEXT PRIMARY KEY, name TEXT, ext TEXT, size INTEGER, added TEXT, sheets TEXT)")
    store.run("CREATE TABLE IF NOT EXISTS bi_presets (id TEXT PRIMARY KEY, name TEXT, body TEXT, saved TEXT)")


def _path(fid):
    row = store.q1("SELECT * FROM bi_files WHERE id=?", (fid,))
    if not row:
        raise BIError("That file was not found", 404)
    return row, os.path.join(_dir(), fid + row["ext"])


# --------------------------------------------------------------------------- reading
def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _excel_date(serial):
    try:
        base = dt.datetime(1899, 12, 30) + dt.timedelta(days=float(serial))
    except (OverflowError, ValueError):
        return str(serial)
    if base.hour or base.minute or base.second:
        return base.strftime("%Y-%m-%d %H:%M")
    return base.strftime("%Y-%m-%d")


def _read_xlsx(data):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise BIError("This file is not a real .xlsx workbook. If it is an older .xls file, open it in Excel and use Save As .xlsx.")
    names = set(z.namelist())
    if "xl/workbook.xml" not in names:
        raise BIError("This does not look like an Excel workbook.")
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    date_styles = set()
    if "xl/styles.xml" in names:
        st = ET.fromstring(z.read("xl/styles.xml"))
        custom = {}
        for nf in st.findall("m:numFmts/m:numFmt", NS):
            custom[int(nf.get("numFmtId"))] = (nf.get("formatCode") or "").lower()
        builtin = set(range(14, 23)) | {45, 46, 47}
        for i, xf in enumerate(st.findall("m:cellXfs/m:xf", NS)):
            fid = int(xf.get("numFmtId", 0))
            code = custom.get(fid)
            if fid in builtin or (code and re.search(r"[dmyh]", re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", code)) and "0.0" not in code and "#" not in code):
                date_styles.add(i)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels.findall(RELNS + "Relationship")}
    out = OrderedDict()
    for sh in wb.findall("m:sheets/m:sheet", NS):
        rid = sh.get("{%s}id" % NS["r"])
        t = target.get(rid, "")
        t = t.lstrip("/")
        path = t if t.startswith("xl/") else "xl/" + t
        if path not in names:
            continue
        rows = []
        for _ev, el in ET.iterparse(io.BytesIO(z.read(path)), events=("end",)):
            if el.tag != "{%s}row" % NS["m"]:
                continue
            row = []
            for c in el.findall("m:c", NS):
                idx = _col_index(c.get("r"))
                while len(row) < idx:
                    row.append("")
                typ = c.get("t")
                v = c.find("m:v", NS)
                val = ""
                if typ == "s" and v is not None and v.text is not None:
                    val = shared[int(v.text)] if int(v.text) < len(shared) else ""
                elif typ == "inlineStr":
                    val = "".join(t_.text or "" for t_ in c.iter("{%s}t" % NS["m"]))
                elif typ == "b":
                    val = "TRUE" if (v is not None and v.text == "1") else "FALSE"
                elif v is not None and v.text is not None:
                    if typ in ("str", "e"):
                        val = v.text
                    else:
                        try:
                            num = float(v.text)
                        except ValueError:
                            num = None
                        if num is None:
                            val = v.text
                        elif int(c.get("s", 0)) in date_styles and 0 < num < 80000:
                            val = _excel_date(num)
                        else:
                            val = int(num) if num == int(num) and abs(num) < 1e15 else num
                row.append(val)
            rows.append(row)
            el.clear()
            if len(rows) >= MAX_ROWS:
                break
        while rows and not any(str(x).strip() for x in rows[-1]):
            rows.pop()
        out[sh.get("name")] = rows
    return out


def _read_csv(data):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = []
    for r in csv.reader(io.StringIO(text), dialect):
        rows.append([x.strip() for x in r])
        if len(rows) >= MAX_ROWS:
            break
    while rows and not any(rows[-1]):
        rows.pop()
    return OrderedDict([("Sheet1", rows)])


def sheets_of(fid):
    with LOCK:
        if fid in CACHE:
            CACHE.move_to_end(fid)
            return CACHE[fid]
    row, path = _path(fid)
    with open(path, "rb") as fh:
        data = fh.read()
    sheets = _read_csv(data) if row["ext"] == ".csv" else _read_xlsx(data)
    with LOCK:
        CACHE[fid] = sheets
        while len(CACHE) > 6:
            CACHE.popitem(last=False)
    return sheets


# --------------------------------------------------------------------------- files
def add_file(name, data):
    _init()
    ext = os.path.splitext(name)[1].lower()
    if ext == ".xls":
        raise BIError("Old .xls files are not supported. Open it in Excel and choose Save As .xlsx, then upload again.")
    if ext not in EXTS:
        raise BIError("Please upload an Excel (.xlsx) or CSV file.")
    if not data:
        raise BIError("The file was empty.")
    if store.q1("SELECT COUNT(*) AS n FROM bi_files")["n"] >= 40:
        raise BIError("You have 40 files stored. Remove some before adding more.")
    sheets = _read_csv(data) if ext == ".csv" else _read_xlsx(data)
    info = [{"name": n, "rows": max(0, len(r) - 1)} for n, r in sheets.items()]
    fid = secrets.token_hex(8)
    with open(os.path.join(_dir(), fid + ext), "wb") as fh:
        fh.write(data)
    clean = re.sub(r"[^\w .()\-]", "_", os.path.basename(name))[:120] or "file" + ext
    store.run("INSERT INTO bi_files VALUES (?,?,?,?,?,?)", (fid, clean, ext, len(data), store.now().strftime("%Y-%m-%d %H:%M"), json.dumps(info)))
    with LOCK:
        CACHE[fid] = sheets
    return file_row(fid)


def file_row(fid):
    r = store.q1("SELECT * FROM bi_files WHERE id=?", (fid,))
    r["sheets"] = json.loads(r["sheets"])
    return r


def list_files():
    _init()
    out = store.q("SELECT * FROM bi_files ORDER BY added DESC, rowid DESC")
    for r in out:
        r["sheets"] = json.loads(r["sheets"])
    return out


def remove_file(fid):
    row, path = _path(fid)
    store.run("DELETE FROM bi_files WHERE id=?", (fid,))
    with LOCK:
        CACHE.pop(fid, None)
    try:
        os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- tables
def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("৳", "").replace("BDT", "").replace("Tk", "").replace("%", "").strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if neg else n


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%b-%y", "%b %Y", "%B %Y", "%Y-%m", "%d-%b-%Y", "%d-%b-%y"]


def _date(v):
    s = str(v).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return dt.datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None
    for f in DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def _find_header(rows, forced=None):
    if forced is not None:
        return max(0, min(int(forced), max(0, len(rows) - 1)))
    for i, r in enumerate(rows[:20]):
        cells = [c for c in r if str(c).strip()]
        if len(cells) >= 2 and sum(1 for c in cells if isinstance(c, str) and _num(c) is None) >= max(2, int(len(cells) * 0.6)):
            return i
    return 0


def _clean_header(h, i):
    s = re.sub(r"\s+", " ", str(h)).strip()
    return s or "Column %d" % (i + 1)


def table(fid, sheet, header_row=None):
    sheets = sheets_of(fid)
    if sheet not in sheets:
        raise BIError("That worksheet was not found in the file", 404)
    rows = sheets[sheet]
    if not rows:
        return {"header_row": 0, "columns": [], "rows": []}
    hr = _find_header(rows, header_row)
    width = max(len(r) for r in rows[hr:hr + 200] or [[]])
    cols, seen = [], {}
    for i in range(width):
        name = _clean_header(rows[hr][i] if i < len(rows[hr]) else "", i)
        if name in seen:
            seen[name] += 1
            name = "%s (%d)" % (name, seen[name])
        else:
            seen[name] = 1
        cols.append(name)
    body = [r + [""] * (width - len(r)) for r in rows[hr + 1:] if any(str(x).strip() for x in r)]
    return {"header_row": hr, "columns": cols, "rows": body}


def _suggest(cols):
    out, used = {}, set()
    norm = {c: re.sub(r"[^a-z0-9]+", " ", c.lower()).strip() for c in cols}
    for key, _label, syns in FIELDS:
        for c in cols:
            if c in used:
                continue
            if norm[c] in syns:
                out[key] = c
                used.add(c)
                break
        else:
            for c in cols:
                if c in used:
                    continue
                if any(len(s) > 3 and s in norm[c] for s in syns):
                    out[key] = c
                    used.add(c)
                    break
    return out


def preview(fid, sheet, header_row=None):
    t = table(fid, sheet, header_row)
    cols = t["columns"]
    prof = []
    for i, c in enumerate(cols):
        vals = [r[i] for r in t["rows"]]
        filled = [v for v in vals if str(v).strip()]
        nums = sum(1 for v in filled if _num(v) is not None)
        dates = sum(1 for v in filled[:200] if _date(v) is not None)
        kind = "empty"
        if filled:
            kind = "number" if nums >= 0.9 * len(filled) else ("date" if dates >= 0.8 * min(len(filled), 200) else "text")
        prof.append({"name": c, "type": kind, "missing": len(vals) - len(filled)})
    return {"header_row": t["header_row"], "columns": prof, "row_count": len(t["rows"]), "sample": t["rows"][:8],
            "suggest": _suggest(cols), "fields": [{"key": k, "label": l} for k, l, _ in FIELDS]}


# --------------------------------------------------------------------------- analysis
def _norm_name(v):
    return re.sub(r"\s+", " ", str(v).strip())


def _truthy(v):
    return str(v).strip().lower() in ("1", "1.0", "yes", "y", "true", "out", "stock out", "stockout", "oos", "x")


def _period_key(d, unit):
    if unit == "day":
        return d.strftime("%Y-%m-%d")
    if unit == "week":
        y, w, _ = d.isocalendar()
        return "%d-W%02d" % (y, w)
    if unit == "quarter":
        return "%d-Q%d" % (d.year, (d.month - 1) // 3 + 1)
    return d.strftime("%Y-%m")


def pct(a, b):
    return round(a / b * 100, 2) if b else None


def load_sources(sources, date_from=None, date_to=None):
    """Turn every chosen worksheet into one list of tidy records, remembering where each came from."""
    recs, issues, notes = [], defaultdict(int), []
    structure = {}
    fnames = {r["id"]: r["name"] for r in list_files()}
    for si, src in enumerate(sources):
        fid, sheet = src.get("file"), src.get("sheet")
        label = "%s / %s" % (fnames.get(fid, fid), sheet)
        t = table(fid, sheet, src.get("header_row"))
        mp = {k: v for k, v in (src.get("map") or {}).items() if v in t["columns"]}
        structure[label] = sorted(t["columns"])
        idx = {k: t["columns"].index(v) for k, v in mp.items()}
        for ri, row in enumerate(t["rows"]):
            rec = {"_src": label, "_row": ri + t["header_row"] + 2, "_si": si}
            bad = False
            for k, i in idx.items():
                raw = row[i]
                if k == "date":
                    d = _date(raw) if str(raw).strip() else None
                    if str(raw).strip() and d is None:
                        issues["Dates that could not be read"] += 1
                    if not str(raw).strip():
                        issues["Missing date"] += 1
                    rec[k] = d
                elif k in ("target", "actual"):
                    n = _num(raw) if str(raw).strip() else None
                    if str(raw).strip() and n is None:
                        issues["%s values that are not numbers" % dict((a, b) for a, b, _ in FIELDS)[k]] += 1
                    if n is None and not str(raw).strip():
                        issues["Missing %s" % k] += 1
                    if n is not None and n < 0:
                        issues["Negative %s values" % k] += 1
                    rec[k] = n
                elif k == "stock_out":
                    rec[k] = _truthy(raw)
                else:
                    v = _norm_name(raw)
                    if not v:
                        issues["Missing %s name" % k] += 1
                    rec[k] = v
            d = rec.get("date")
            if d and date_from and d < date_from or d and date_to and d > date_to:
                continue
            recs.append(rec)
    return recs, dict(issues), structure


def _dedupe(recs):
    seen, keep, dup = {}, [], []
    for r in recs:
        key = tuple((k, str(r.get(k))) for k in sorted(r) if not k.startswith("_"))
        if key in seen:
            dup.append(r)
        else:
            seen[key] = r["_src"]
            keep.append(r)
    return keep, dup


def _name_variants(recs, dim):
    groups = defaultdict(set)
    for r in recs:
        v = r.get(dim)
        if v:
            groups[re.sub(r"[^a-z0-9]", "", v.lower())].add(v)
    return [sorted(v) for v in groups.values() if len(v) > 1]


def _display_map(recs, dim):
    first = {}
    for r in recs:
        v = r.get(dim)
        if v:
            first.setdefault(re.sub(r"[^a-z0-9]", "", v.lower()), v)
    return first


def _outliers(values):
    vals = sorted(v for v in values if v is not None)
    if len(vals) < 8:
        return None
    q1, q3 = vals[len(vals) // 4], vals[(len(vals) * 3) // 4]
    iqr = q3 - q1
    return (q1 - 3 * iqr, q3 + 3 * iqr) if iqr > 0 else None


def analyze(req):
    mode = req.get("mode", "performance")
    sources = req.get("sources") or []
    if not sources:
        raise BIError("Choose at least one worksheet to analyse.")
    if len(sources) > 60:
        raise BIError("Please choose 60 worksheets or fewer.")
    if mode == "reconcile":
        return reconcile(req)
    df = _date(req.get("from") or "") if req.get("from") else None
    dtt = _date(req.get("to") or "") if req.get("to") else None
    if not any("actual" in (s_.get("map") or {}) for s_ in sources):
        raise BIError("Choose which column holds the sales value (Actual) for each worksheet. Without it, totals, growth and contribution cannot be calculated.")
    recs, issues, structure = load_sources(sources, df, dtt)
    if not recs:
        raise BIError("No rows were found. Check the header row and the column mapping, and the date range.")
    mapped = {k for s in sources for k in (s.get("map") or {})}
    for k in ("target", "actual"):
        if k not in mapped:
            pass
    dim = req.get("group_by") or ""
    unit = req.get("period") or "month"
    dedupe_on = req.get("dedupe", True)
    dups = []
    if dedupe_on:
        recs, dups = _dedupe(recs)
    avail, missing = [], []
    has = lambda k: k in mapped
    if not has("actual"):
        missing.append("Sales value (Actual): choose which column holds sales to calculate totals, growth and contribution.")
    if has("actual") and has("target"):
        avail.append("Target achievement and sales gap")
    elif has("actual"):
        missing.append("Target: choose a target column to calculate achievement percentage and sales gap.")
    if has("actual") and has("date"):
        avail.append("Period comparison and growth")
    elif has("actual"):
        missing.append("Date: choose a date column to calculate growth and compare periods.")
    if has("actual") and dim and not has(dim):
        raise BIError("You chose to group by %s, but no %s column is mapped." % (dim, dim))
    if has("outlet"):
        avail.append("Outlet counts and sales per outlet")
    if has("stock_out"):
        avail.append("Stock-out frequency")
    disp = _display_map(recs, dim) if dim else {}

    def gname(r):
        if not dim:
            return "All records"
        v = r.get(dim)
        return disp.get(re.sub(r"[^a-z0-9]", "", v.lower()), v) if v else "(blank)"

    actual_vals = [r.get("actual") for r in recs]
    total_actual = sum(v for v in actual_vals if v is not None)
    total_target = sum(r.get("target") or 0 for r in recs) if has("target") else None
    # groups
    G = OrderedDict()
    for r in recs:
        g = G.setdefault(gname(r), {"name": gname(r), "rows": 0, "actual": 0.0, "target": 0.0, "stock_outs": 0, "outlets": set(), "periods": defaultdict(lambda: [0.0, 0.0])})
        g["rows"] += 1
        a, t = r.get("actual"), r.get("target")
        g["actual"] += a or 0
        g["target"] += t or 0
        if r.get("stock_out"):
            g["stock_outs"] += 1
        if r.get("outlet"):
            g["outlets"].add(r["outlet"].lower())
        if r.get("date"):
            pk = _period_key(r["date"], unit)
            g["periods"][pk][0] += a or 0
            g["periods"][pk][1] += t or 0
    all_periods = sorted({p for g in G.values() for p in g["periods"]})
    cur_p = all_periods[-1] if len(all_periods) >= 1 else None
    prev_p = all_periods[-2] if len(all_periods) >= 2 else None
    rows = []
    for g in G.values():
        row = {"name": g["name"], "records": g["rows"], "actual": round(g["actual"], 2)}
        row["share_pct"] = pct(g["actual"], total_actual)
        if has("target"):
            row["target"] = round(g["target"], 2)
            row["achievement_pct"] = pct(g["actual"], g["target"])
            row["gap"] = round(g["actual"] - g["target"], 2)
        if cur_p and prev_p:
            c, p = g["periods"].get(cur_p, [0.0, 0.0])[0], g["periods"].get(prev_p, [0.0, 0.0])[0]
            row["current"], row["previous"] = round(c, 2), round(p, 2)
            row["growth_abs"] = round(c - p, 2)
            row["growth_pct"] = pct(c - p, p)
        if has("outlet"):
            row["outlets"] = len(g["outlets"])
            row["per_outlet"] = round(g["actual"] / len(g["outlets"]), 2) if g["outlets"] else None
        if has("stock_out"):
            row["stock_outs"] = g["stock_outs"]
            row["stock_out_rate_pct"] = pct(g["stock_outs"], g["rows"])
        # consecutive periods below target (latest streak)
        streak = 0
        if has("target"):
            for p in sorted(g["periods"], reverse=True):
                a, t = g["periods"][p]
                if t > 0 and a < t:
                    streak += 1
                else:
                    break
            row["below_target_streak"] = streak
        # consistently declining
        pv = [g["periods"][p][0] for p in sorted(g["periods"])]
        row["declining"] = len(pv) >= 3 and all(pv[i] > pv[i + 1] for i in range(len(pv) - 3, len(pv) - 1)) and pv[-2] > pv[-1]
        rows.append(row)
    rows.sort(key=lambda r: -r["actual"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    # period totals
    per = []
    ptot = defaultdict(lambda: [0.0, 0.0])
    for g in G.values():
        for p, (a, t) in g["periods"].items():
            ptot[p][0] += a
            ptot[p][1] += t
    prev = None
    for p in sorted(ptot):
        a, t = ptot[p]
        item = {"period": p, "actual": round(a, 2)}
        if has("target"):
            item["target"] = round(t, 2)
            item["achievement_pct"] = pct(a, t)
        if prev is not None:
            item["growth_abs"] = round(a - prev, 2)
            item["growth_pct"] = pct(a - prev, prev)
        prev = a
        per.append(item)
    # quality
    quality = []
    for k, n in sorted(issues.items()):
        quality.append({"issue": k, "count": n})
    if dedupe_on and dups:
        quality.append({"issue": "Duplicate records left out (identical in every mapped column)", "count": len(dups)})
    elif not dedupe_on:
        _k, d2 = _dedupe(recs)
        if d2:
            quality.append({"issue": "Possible duplicate records still included (identical in every mapped column)", "count": len(d2)})
    for dd in ("territory", "route", "distributor", "product", "category", "salesperson", "outlet"):
        if has(dd):
            var = _name_variants(recs, dd)
            if var:
                quality.append({"issue": "Names that differ only by spacing or capitals (%s), treated as the same" % dd, "count": len(var),
                                "examples": [" / ".join(v) for v in var[:4]]})
    if has("actual"):
        lim = _outliers(actual_vals)
        if lim:
            outl = [r for r in recs if r.get("actual") is not None and (r["actual"] < lim[0] or r["actual"] > lim[1])]
            if outl:
                quality.append({"issue": "Unusually large or small sales values worth checking", "count": len(outl),
                                "examples": ["%s row %d: %s" % (o["_src"], o["_row"], round(o["actual"], 2)) for o in outl[:4]]})
    cols_sets = list(structure.values())
    if len(cols_sets) > 1 and any(c != cols_sets[0] for c in cols_sets[1:]):
        quality.append({"issue": "The chosen worksheets do not all have the same columns (mapping was used to line them up)", "count": len(cols_sets)})
    periods_by_src = defaultdict(set)
    for r in recs:
        if r.get("date"):
            periods_by_src[r["_src"]].add(_period_key(r["date"], unit))
    srcs = list(periods_by_src)
    for i in range(len(srcs)):
        for j in range(i + 1, len(srcs)):
            ov = periods_by_src[srcs[i]] & periods_by_src[srcs[j]]
            if ov:
                quality.append({"issue": "Two worksheets cover the same period, so totals may count it twice: %s and %s" % (srcs[i], srcs[j]),
                                "count": len(ov), "examples": sorted(ov)[:4]})
    # headline numbers
    head = {"records": len(recs), "actual": round(total_actual, 2)}
    if total_target is not None:
        head["target"] = round(total_target, 2)
        head["achievement_pct"] = pct(total_actual, total_target)
        head["gap"] = round(total_actual - total_target, 2)
    if cur_p and prev_p and per:
        c, p = per[-1]["actual"], per[-2]["actual"]
        head.update({"current_period": cur_p, "previous_period": prev_p, "current": c, "previous": p,
                     "growth_abs": round(c - p, 2), "growth_pct": pct(c - p, p)})
    if per:
        best = max(per, key=lambda x: x["actual"])
        worst = min(per, key=lambda x: x["actual"])
        head["best_period"], head["worst_period"] = best["period"], worst["period"]
    result = {"mode": "performance", "group_by": dim, "period_unit": unit, "headline": head, "groups": rows, "periods": per,
              "quality": quality, "available": avail, "missing": missing, "currency": store.get_setting("currency"),
              "sources": [{"file": s.get("file"), "sheet": s.get("sheet")} for s in sources], "dedupe": bool(dedupe_on)}
    result["report"] = report_text(result, sources)
    return result


# --------------------------------------------------------------------------- reconcile
def reconcile(req):
    sources = req["sources"]
    if len(sources) < 2:
        raise BIError("Choose at least two worksheets to compare.")
    keys = req.get("keys") or []
    cmp_cols = req.get("compare") or []
    if not keys:
        raise BIError("Choose at least one matching column (for example Route or Outlet ID).")
    fnames = {r["id"]: r["name"] for r in list_files()}
    tables = []
    for s in sources:
        t = table(s["file"], s["sheet"], s.get("header_row"))
        mp = s.get("map") or {}
        for k in keys + cmp_cols:
            if k not in mp or mp[k] not in t["columns"]:
                raise BIError("Map the column for '%s' in every chosen worksheet." % k)
        idx = {k: t["columns"].index(mp[k]) for k in keys + cmp_cols}
        data, dupkeys = OrderedDict(), []
        for ri, row in enumerate(t["rows"]):
            kv = tuple(re.sub(r"\s+", " ", str(row[idx[k]]).strip()).lower() for k in keys)
            if not any(kv):
                continue
            if kv in data:
                dupkeys.append(kv)
                continue
            data[kv] = {c: row[idx[c]] for c in cmp_cols}
        tables.append({"label": "%s / %s" % (fnames.get(s["file"], s["file"]), s["sheet"]), "data": data, "dups": dupkeys})
    base = tables[0]
    out = []
    for other in tables[1:]:
        added = [k for k in other["data"] if k not in base["data"]]
        removed = [k for k in base["data"] if k not in other["data"]]
        changed = []
        same = 0
        for k, v in base["data"].items():
            if k in other["data"]:
                diffs = []
                for c in cmp_cols:
                    a, b = v[c], other["data"][k][c]
                    na, nb = _num(a), _num(b)
                    eq = (abs(na - nb) < 1e-9) if (na is not None and nb is not None) else (str(a).strip().lower() == str(b).strip().lower())
                    if not eq:
                        diffs.append({"column": c, "old": a, "new": b})
                if diffs:
                    changed.append({"key": " | ".join(k), "diffs": diffs})
                else:
                    same += 1
        out.append({"base": base["label"], "other": other["label"], "matching": same, "added": [" | ".join(k) for k in added][:300],
                    "added_count": len(added), "removed": [" | ".join(k) for k in removed][:300], "removed_count": len(removed),
                    "changed": changed[:300], "changed_count": len(changed), "dup_base": len(base["dups"]), "dup_other": len(other["dups"])})
    lines = ["RECONCILIATION REPORT", "Matching columns: " + ", ".join(keys), "Compared columns: " + (", ".join(cmp_cols) or "none (presence only)"), ""]
    for o in out:
        lines += ["%s  ->  %s" % (o["base"], o["other"]),
                  "- %d records match exactly." % o["matching"],
                  "- %d records are only in the second file (new or added)." % o["added_count"],
                  "- %d records are only in the first file (removed, or missing from the second)." % o["removed_count"],
                  "- %d records have different values." % o["changed_count"]]
        if o["dup_base"] or o["dup_other"]:
            lines.append("- Repeated matching keys were found (%d in the first file, %d in the second); only the first of each was compared." % (o["dup_base"], o["dup_other"]))
        lines += ["", "Note: a record missing from one file is not proof of a business loss. Please check each one before drawing conclusions.", ""]
    return {"mode": "reconcile", "keys": keys, "compare": cmp_cols, "pairs": out, "report": "\n".join(lines)}


# --------------------------------------------------------------------------- plain-English report
def _m(n, cur):
    if n is None:
        return "not available"
    neg = n < 0
    s = "{:,.0f}".format(abs(n))
    if abs(n) >= 100000:
        s = _lakh(abs(n))
    return ("-" if neg else "") + cur + s


def _lakh(n):
    s = "{:.0f}".format(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _p(v):
    return "not calculable" if v is None else ("%.1f%%" % v)


def report_text(res, sources):
    cur = res["currency"]
    h, g, per = res["headline"], res["groups"], res["periods"]
    dim = res["group_by"]
    fn = {r["id"]: r["name"] for r in list_files()}
    L = ["BUSINESS ANALYSIS REPORT", "Prepared by APIS on " + store.now().strftime("%d %b %Y"), ""]
    L += ["1. What was analysed",
          "%d records after cleaning, from %d worksheet%s." % (h["records"], len(sources), "" if len(sources) == 1 else "s"),
          "Duplicate handling: " + ("identical rows were left out." if res["dedupe"] else "duplicates were kept in (switched off by you)."), ""]
    L += ["2. Files and worksheets used"] + ["- %s, sheet \"%s\"" % (fn.get(s["file"], s["file"]), s["sheet"]) for s in sources] + [""]
    used = sorted({k for s in sources for k in (s.get("map") or {})})
    L += ["3. Columns used", ", ".join(used) if used else "None mapped.", ""]
    L += ["4. Main figures", "Total actual sales: %s." % _m(h["actual"], cur)]
    if "target" in h:
        L += ["Total target: %s. Achievement = Actual / Target x 100 = %s." % (_m(h["target"], cur), _p(h["achievement_pct"])),
              "Sales gap = Actual - Target = %s." % _m(h["gap"], cur)]
    if "growth_pct" in h:
        L += ["Latest period (%s) compared with the one before (%s): %s versus %s. Absolute growth = %s. Growth rate = (Current - Previous) / Previous x 100 = %s." % (
            h["current_period"], h["previous_period"], _m(h["current"], cur), _m(h["previous"], cur), _m(h["growth_abs"], cur), _p(h["growth_pct"]))]
        if h["previous"] == 0:
            L.append("The previous period was zero, so a growth rate is not meaningful.")
    L.append("")
    L.append("5. Increases and decreases")
    up = [r for r in g if r.get("growth_abs") is not None and r["growth_abs"] > 0]
    down = [r for r in g if r.get("growth_abs") is not None and r["growth_abs"] < 0]
    if up or down:
        for r in sorted(up, key=lambda x: -x["growth_abs"])[:3]:
            L.append("- %s rose by %s (%s)." % (r["name"], _m(r["growth_abs"], cur), _p(r["growth_pct"])))
        for r in sorted(down, key=lambda x: x["growth_abs"])[:3]:
            L.append("- %s fell by %s (%s)." % (r["name"], _m(-r["growth_abs"], cur), _p(r["growth_pct"])))
    else:
        L.append("A period comparison needs a date column and at least two periods.")
    L.append("")
    L.append("6. Highest and lowest")
    if dim and len(g) > 1:
        L.append("- Largest %s: %s with %s (%s of total)." % (dim, g[0]["name"], _m(g[0]["actual"], cur), _p(g[0]["share_pct"])))
        L.append("- Smallest %s: %s with %s (%s of total)." % (dim, g[-1]["name"], _m(g[-1]["actual"], cur), _p(g[-1]["share_pct"])))
    if "best_period" in h and len(per) > 1:
        L.append("- Best period: %s. Weakest period: %s." % (h["best_period"], h["worst_period"]))
    L.append("")
    L.append("7. Patterns and exceptions")
    below = [r for r in g if r.get("below_target_streak", 0) >= 2]
    for r in below[:5]:
        L.append("- %s was below target for %d periods in a row." % (r["name"], r["below_target_streak"]))
    for r in [x for x in g if x.get("declining")][:5]:
        L.append("- %s fell in each of the last two periods." % r["name"])
    for r in [x for x in g if x.get("achievement_pct") is not None and x["achievement_pct"] >= 100][:3]:
        L.append("- %s reached %s of its target." % (r["name"], _p(r["achievement_pct"])))
    if "stock_outs" in (g[0] if g else {}):
        so = sorted([r for r in g if r["stock_outs"]], key=lambda x: -x["stock_outs"])[:3]
        for r in so:
            L.append("- %s had %d stock-out record%s (%s of its records)." % (r["name"], r["stock_outs"], "" if r["stock_outs"] == 1 else "s", _p(r["stock_out_rate_pct"])))
    if L[-1] == "7. Patterns and exceptions":
        L.append("No repeated shortfalls or declines were found in the data provided.")
    L.append("")
    L.append("8. Data quality")
    if res["quality"]:
        for qd in res["quality"]:
            L.append("- %s: %d%s" % (qd["issue"], qd["count"], (" (e.g. " + "; ".join(qd.get("examples", [])) + ")") if qd.get("examples") else ""))
    else:
        L.append("No problems were found in the columns that were mapped.")
    L.append("")
    L.append("9. Suggested next steps (these are ideas to check, not proven causes)")
    if below:
        L.append("- Ask what is different on %s; the data shows the shortfall but not the reason." % below[0]["name"])
    if res["quality"]:
        L.append("- Fix or confirm the data quality items above before sharing these figures.")
    if res["missing"]:
        L.append("- Add the missing information listed below to unlock more analysis.")
    L.append("- Confirm the figures with the source reports before official use.")
    L.append("")
    L.append("10. Limits and assumptions")
    L.append("- Blank numbers were left out of totals, not counted as zero. Rows with no date are excluded from period comparisons.")
    L.append("- Growth is computed from combined totals, not by averaging individual percentages.")
    L += ["- " + x for x in res["missing"]]
    return "\n".join(L)


def export_bytes(res):
    if res.get("mode") == "reconcile":
        rows = []
        for o in res["pairs"]:
            rows.append([o["base"], o["other"], o["matching"], o["added_count"], o["removed_count"], o["changed_count"]])
        sheets = [("Summary", ["First file", "Second file", "Matching", "Only in second", "Only in first", "Changed"], rows),
                  ("Changes", ["Key", "Column", "Old", "New"], [[c["key"], d["column"], d["old"], d["new"]] for o in res["pairs"] for c in o["changed"] for d in c["diffs"]]),
                  ("Only in second", ["Key"], [[k] for o in res["pairs"] for k in o["added"]]),
                  ("Only in first", ["Key"], [[k] for o in res["pairs"] for k in o["removed"]]),
                  ("Report", ["Report"], [[x] for x in res["report"].split("\n")])]
        return xlsxw.build(sheets)
    cols = [("name", res["group_by"].title() or "Group"), ("records", "Records"), ("actual", "Actual"), ("target", "Target"), ("achievement_pct", "Achievement %"),
            ("gap", "Gap"), ("share_pct", "Share %"), ("current", "Current period"), ("previous", "Previous period"), ("growth_abs", "Growth"),
            ("growth_pct", "Growth %"), ("outlets", "Outlets"), ("per_outlet", "Sales per outlet"), ("stock_outs", "Stock-outs"), ("below_target_streak", "Periods below target")]
    cols = [c for c in cols if any(c[0] in g for g in res["groups"])]
    sheets = [("By group", [c[1] for c in cols], [[g.get(c[0], "") if g.get(c[0]) is not None else "" for c in cols] for g in res["groups"]]),
              ("By period", ["Period", "Actual", "Target", "Achievement %", "Growth", "Growth %"],
               [[p["period"], p["actual"], p.get("target", ""), p.get("achievement_pct") if p.get("achievement_pct") is not None else "", p.get("growth_abs", ""),
                 p.get("growth_pct") if p.get("growth_pct") is not None else ""] for p in res["periods"]]),
              ("Data quality", ["Issue", "Count"], [[q["issue"], q["count"]] for q in res["quality"]]),
              ("Report", ["Report"], [[x] for x in res["report"].split("\n")])]
    return xlsxw.build(sheets)


# --------------------------------------------------------------------------- saved settings
def presets():
    _init()
    return [{"id": r["id"], "name": r["name"], "saved": r["saved"], "body": json.loads(r["body"])} for r in store.q("SELECT * FROM bi_presets ORDER BY saved DESC")]


def save_preset(name, body):
    _init()
    name = str(name or "").strip()[:80]
    if not name:
        raise BIError("Give these settings a name.")
    old = store.q1("SELECT id FROM bi_presets WHERE name=?", (name,))
    pid = old["id"] if old else secrets.token_hex(6)
    store.run("INSERT INTO bi_presets VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body, saved=excluded.saved",
              (pid, name, json.dumps(body), store.now().strftime("%Y-%m-%d %H:%M")))
    return presets()


def delete_preset(pid):
    _init()
    store.run("DELETE FROM bi_presets WHERE id=?", (pid,))
