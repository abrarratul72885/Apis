# APIS

**Work Smarter. Make an Impact.**

APIS is a personal operations hub that runs on your own laptop and costs nothing. It has no accounts, no cloud and no installs beyond Python. Open it in any browser, or install it on an Android phone or tablet as an app.

## What it does

| Section | What you get |
|---|---|
| **Home** | Today at a glance, alerts for missed targets, stock-outs and overdue follow-ups, quick add, and Ask APIS |
| **My Portfolio** | A LinkedIn-style profile you fully control: posts with photos and PDFs, experience, education, projects, certifications, achievements, skills and social links. Upload your own logos |
| **Portfolio Builder** | A 2 to 3 page portfolio made from your records. Three templates, purpose-based selection, preview, then PDF, Word or HTML. Never invents anything |
| **Work and Tasks** | Daily log with impact and status, history, and a tamper-evident career log of your best work |
| **Business Analysis** | Upload up to 20 Excel or CSV files, map columns, compare performance or reconcile versions, and get a plain-English report. Fixed formulas, safe with zeros and missing data |
| **Sales and Territory** | Target against actual by route, stock-outs, alerts |
| **Projects and Pipeline** | Four-stage board with a document checklist that blocks risky moves |
| **Reports and Automation** | End-of-day report by Gmail, with an Excel attachment, on a schedule |
| **Settings and Data** | Sales, Banking or General wording, Gmail, Google Drive backup folder, phone access, PIN |

Currency is Bangladeshi taka (৳). The work week is Sunday to Thursday.

## Run it (Windows)

1. Install [Python 3.10 or newer](https://www.python.org/downloads/) and tick **Add python.exe to PATH**.
2. Download this repository (green **Code** button, then **Download ZIP**) and unzip it.
3. Double-click **Start APIS.bat**. Your browser opens. Choose a PIN.

Other systems: `python3 server/apis_server.py`

The server uses only the Python standard library. There is nothing to `pip install`.

## Use it on Android

With APIS running and the phone on the same Wi-Fi, open **Settings and Data** to see the address (for example `http://192.168.0.12:8501`). Type it into Chrome, sign in, then choose **Install app**.

## Where your data lives

Everything is stored in the `data/` folder next to the app: a SQLite database, your uploads, automatic backups, and (if you connect Gmail) an App Password. **`data/` is listed in `.gitignore`. Never remove that line and never commit that folder.** Backups can also be copied to a Google Drive folder from Settings.

## Making it yours

Your name, photo and records are entered in the app. If you want a ready-made first-run profile, create `server/seed_personal.py` (it is ignored by git). The public repository starts with a blank profile.

## A note on hosting

GitHub hosts the code, but APIS is a small server that has to run on your own computer. GitHub Pages cannot run it, and it is deliberately not designed to be put on the public internet. For a public portfolio page, use **My Portfolio, Share public page**: it makes a static folder with only the posts, projects and achievements you marked Public (no phone number) that you can host for free.

## Tests

```
python tests/backend_test.py
python tests/bi_test.py
```

## Limits

- Old `.xls` files are not read. Save them as `.xlsx` first.
- No offline language model is included. Ask APIS answers common questions from your records with fixed rules.
- Banking mode only changes wording and checklists. APIS never connects to a bank system. Do not store customer ID numbers, account numbers or passwords.

MIT licence.
