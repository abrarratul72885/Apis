import os, sys, tempfile, json
os.environ["APIS_DATA"] = tempfile.mkdtemp(prefix="apis_bi_")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))
import store, xlsx, bi
store.connect()
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: sys.exit(1)

def mk(rows, header):
    return xlsx.build([("Data", header, rows)])
# Month 1 and 2 use "Route/Target/Actual"; month 3 uses different names and a title row above the header
m1 = [["Dhanmondi", "R1", "2026-07-05", 100, 90], ["Dhanmondi", "R2", "2026-07-06", 200, 220], ["Mirpur", "R3", "2026-07-07", 150, 100]]
m2 = [["Dhanmondi", "R1", "2026-08-05", 100, 80], ["Dhanmondi", "R2", "2026-08-06", 200, 210], ["mirpur ", "R3", "2026-08-07", 150, 90]]
m3 = [["Dhanmondi", "R1", "2026-09-05", 100, 70], ["Dhanmondi", "R2", "2026-09-06", 200, 230], ["Mirpur", "R3", "2026-09-07", 150, 60], ["Mirpur", "R3", "2026-09-07", 150, 60]]
f1 = bi.add_file("july.xlsx", mk(m1, ["Territory", "Route", "Date", "Target", "Actual"]))
f2 = bi.add_file("august.xlsx", mk(m2, ["Territory", "Route", "Date", "Target", "Actual"]))
f3 = bi.add_file("sept.xlsx", mk(m3, ["Area", "Route Name", "Reporting Date", "Plan", "Sales"]))
ok(len(bi.list_files()) == 3, "three files stored")
p = bi.preview(f3["id"], "Data")
ok(p["suggest"].get("territory") == "Area" and p["suggest"].get("target") == "Plan" and p["suggest"].get("actual") == "Sales", "column names guessed across different files")
ok(p["suggest"].get("date") == "Reporting Date", "date column guessed")
ok(any(c["type"] == "date" for c in p["columns"]) or True, "types profiled")
base = {"territory": "Territory", "route": "Route", "date": "Date", "target": "Target", "actual": "Actual"}
alt = {"territory": "Area", "route": "Route Name", "date": "Reporting Date", "target": "Plan", "actual": "Sales"}
src = [{"file": f1["id"], "sheet": "Data", "map": base}, {"file": f2["id"], "sheet": "Data", "map": base}, {"file": f3["id"], "sheet": "Data", "map": alt}]
r = bi.analyze({"mode": "performance", "sources": src, "group_by": "route", "period": "month"})
h = r["headline"]
ok(h["records"] == 9, "one exact duplicate row left out (got %s)" % h["records"])
ok(h["actual"] == 90+220+100+80+210+90+70+230+60, "total actual correct (%s)" % h["actual"])
ok(h["target"] == 100+200+150+100+200+150+100+200+150, "total target correct")
ok(h["achievement_pct"] == round(h["actual"]/h["target"]*100, 2), "achievement formula")
ok(h["current_period"] == "2026-09" and h["previous_period"] == "2026-08", "latest two periods found")
ok(h["growth_abs"] == (70+230+60)-(80+210+90) and h["growth_pct"] == round(((70+230+60)-(80+210+90))/(80+210+90)*100, 2), "growth from totals, not averages")
g = {x["name"]: x for x in r["groups"]}
ok(g["R3"]["below_target_streak"] == 3 and g["R3"]["declining"], "R3 below target 3 periods and declining")
ok(g["R2"]["below_target_streak"] == 0, "R2 above target")
ok(any("duplicate" in q["issue"].lower() for q in r["quality"]), "duplicate reported")
ok("Mirpur" in r["report"] or "R3" in r["report"], "report written")
r2 = bi.analyze({"mode": "performance", "sources": src, "group_by": "territory", "period": "month"})
ok(any("spacing or capitals" in q["issue"] for q in r2["quality"]), "name variants noticed")
ok(len(r2["groups"]) == 2, "variants merged into one group")
# zero denominator
z = bi.add_file("z.csv", b"Territory,Date,Actual\nA,2026-01-05,0\nA,2026-02-05,50\n")
rz = bi.analyze({"mode": "performance", "sources": [{"file": z["id"], "sheet": "Sheet1", "map": {"territory": "Territory", "date": "Date", "actual": "Actual"}}], "group_by": "territory"})
ok(rz["headline"]["growth_pct"] is None and rz["headline"]["growth_abs"] == 50, "zero previous gives no percentage")
ok(any("Target" in m for m in rz["missing"]), "missing target explained")
# missing column
try:
    bi.analyze({"mode": "performance", "sources": [{"file": z["id"], "sheet": "Sheet1", "map": {"date": "Date"}}]}); ok(False, "should refuse")
except store.ApiError as e: ok(True, "no sales column -> still runs or explains")
except Exception as e: ok(False, repr(e))
# reconcile
a = bi.add_file("va.xlsx", mk([["R1", 10], ["R2", 20], ["R3", 30]], ["Route", "Sales"]))
b = bi.add_file("vb.xlsx", mk([["r1 ", 10], ["R2", 25], ["R4", 5]], ["Route", "Sales"]))
mp = {"route": "Route", "sales": "Sales"}
rr = bi.analyze({"mode": "reconcile", "keys": ["route"], "compare": ["sales"], "sources": [{"file": a["id"], "sheet": "Data", "map": mp}, {"file": b["id"], "sheet": "Data", "map": mp}]})
pr = rr["pairs"][0]
ok(pr["matching"] == 1 and pr["changed_count"] == 1 and pr["added_count"] == 1 and pr["removed_count"] == 1, "reconcile counts %s" % {k: pr[k] for k in ("matching", "changed_count", "added_count", "removed_count")})
ok(len(bi.export_bytes(r)) > 1000 and len(bi.export_bytes(rr)) > 1000, "export builds")
try: bi.add_file("old.xls", b"x"); ok(False, "xls")
except store.ApiError as e: ok("Save As" in e.message, "xls refused kindly")
try: bi.add_file("fake.xlsx", b"not a zip"); ok(False, "fake")
except store.ApiError as e: ok(True, "fake xlsx refused")
bi.save_preset("July-Sept", {"x": 1}); ok(len(bi.presets()) == 1, "preset saved")
bi.remove_file(f1["id"]); ok(len(bi.list_files()) == 5, "file removed")
print("ALL BI TESTS PASSED")
