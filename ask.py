"""Ask APIS: answers plain questions from your own records. Every number is counted by code, nothing is guessed,
and every answer says where it came from."""
import re

import store


def _money(n):
    return store.get_setting("currency") + "{:,.0f}".format(n or 0)


def answer(question):
    ql = (question or "").lower().strip()
    if not ql:
        raise store.ApiError("Type a question first.")
    today = store.today()
    out = []

    def add(title, lines, source):
        out.append({"title": title, "lines": lines, "source": source})

    asked = False
    if re.search(r"priorit|today|to do|todo|task", ql) and not re.search(r"overdue|week", ql):
        asked = True
        rows = store.q("SELECT * FROM logs WHERE date=? AND status<>'Completed' ORDER BY CASE impact WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, created_at LIMIT 3", (today,))
        if not rows:
            rows = store.q("SELECT * FROM logs WHERE status<>'Completed' ORDER BY CASE impact WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, date DESC LIMIT 3")
        add("Your top open tasks", ["%s (%s impact, %s)" % (r["title"], r["impact"], r["date"]) for r in rows] or ["No open tasks found."], "Work and Tasks")
    if re.search(r"week|accomplish|achiev|done|complete", ql):
        asked = True
        start = store.q1("SELECT date('now','localtime','-6 day') AS d")["d"]
        rows = store.q("SELECT * FROM logs WHERE status='Completed' AND date>=? ORDER BY date DESC", (start,))
        hrs = sum(r["hours"] or 0 for r in rows)
        add("Completed in the last 7 days", ["%d tasks completed, %.1f hours logged." % (len(rows), hrs)] + ["%s: %s" % (r["date"], r["title"]) for r in rows[:8]], "Work and Tasks")
    if re.search(r"overdue|follow|late", ql):
        asked = True
        rows = store.q("SELECT * FROM leads WHERE next_action_date<>'' AND next_action_date<? AND stage<>'Sanctioned' ORDER BY next_action_date", (today,))
        add("Overdue follow-ups", ["%s: %s (due %s)" % (r["company"], r["next_action"] or "next step", r["next_action_date"]) for r in rows] or ["Nothing is overdue."], "Projects and Pipeline")
    if re.search(r"target|miss|below|route|territor|branch", ql):
        asked = True
        s = store.territory_summary(store.q1("SELECT date('now','localtime','-29 day') AS d")["d"], today)
        thr = store.get_setting("alert_threshold")
        miss = [r for r in s["routes"] if r["pct"] is not None and r["pct"] < 100]
        lines = ["Last 30 days: actual %s against target %s (%s)." % (_money(s["actual"]), _money(s["target"]), ("%.1f%%" % s["pct"]) if s["pct"] is not None else "no target")]
        lines += ["%s: %.1f%% (%s of %s)" % (r["route"], r["pct"], _money(r["actual"]), _money(r["target"])) for r in sorted(miss, key=lambda r: r["pct"])[:8]] or ["Every route reached its target."]
        add("Routes below target (alert level %d%%)" % thr, lines, "Sales and Territory")
    if re.search(r"pipeline|client|stage|lead|application", ql):
        asked = True
        rows = store.q("SELECT stage, COUNT(*) AS n, SUM(amount) AS a FROM leads GROUP BY stage")
        add("Pipeline", ["%s: %d (%s)" % (r["stage"], r["n"], _money(r["a"])) for r in rows] or ["No clients yet."], "Projects and Pipeline")
    if re.search(r"missing|portfolio|profile|complete", ql):
        asked = True
        p = store.get_profile()
        miss = []
        for k, label in (("headline", "headline"), ("about", "About text"), ("email", "email"), ("phone", "phone"), ("linkedin", "LinkedIn link"), ("cover", "cover photo")):
            if not p[k]:
                miss.append("Add your " + label)
        for ent, label in (("projects", "a project"), ("achievements", "an achievement"), ("links", "a social link"), ("posts", "a post")):
            if not store.q1("SELECT COUNT(*) AS n FROM %s" % ent)["n"]:
                miss.append("Add " + label)
        add("What is missing from your portfolio", miss or ["Nothing obvious. Your portfolio has every main section."], "My Portfolio")
    if not asked:
        add("I can answer questions about your own records", [
            "Try: What are my top tasks today?", "What did I complete this week?", "Which routes are below target?", "Any overdue follow-ups?",
            "How is my pipeline?", "What is missing from my portfolio?",
            "For growth and comparisons across many Excel files, open Business Analysis."], "")
    return {"question": question, "answers": out}
