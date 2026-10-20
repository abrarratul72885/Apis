"""Daily backups on the laptop, plus an optional copy into a Google Drive folder."""
import glob
import logging
import os
import shutil
import sqlite3
import threading

import reports
import store

log = logging.getLogger("apis")
DRIVE_SUBFOLDER = "APIS Backup"


def detect_drive():
    found = []
    home = os.path.expanduser("~")
    cands = []
    if os.name == "nt":
        for letter in "GHDEFIJKLMNOPQRSTUVWXYZ":
            cands.append("%s:\\My Drive" % letter)
    cands += [os.path.join(home, "Google Drive"), os.path.join(home, "My Drive"), os.path.join(home, "Google Drive", "My Drive")]
    cands += glob.glob(os.path.join(home, "Library", "CloudStorage", "GoogleDrive-*", "My Drive"))
    for c in cands:
        if os.path.isdir(c) and c not in found:
            found.append(c)
    return found


def _snapshot(dest):
    src = store.connect()
    out = sqlite3.connect(dest)
    try:
        with store.LOCK:
            src.backup(out)
    finally:
        out.close()


def _prune(folder, pattern, keep):
    files = sorted(glob.glob(os.path.join(folder, pattern)))
    for old in files[:-keep] if keep > 0 else []:
        try:
            os.remove(old)
        except OSError:
            pass


def run_backup():
    """Returns a small status dict. Never raises: problems are reported in the result."""
    result = {"local": False, "drive": False, "drive_error": ""}
    keep = max(3, int(store.get_setting("backups_keep") or 30))
    day = store.today().replace("-", "")
    try:
        os.makedirs(store.BACKUPS, exist_ok=True)
        target = os.path.join(store.BACKUPS, "apis_%s.db" % day)
        _snapshot(target)
        _prune(store.BACKUPS, "apis_*.db", keep)
        store.set_setting("last_backup", store.now().strftime("%Y-%m-%d %H:%M"))
        result["local"] = True
    except Exception as e:
        log.exception("Local backup failed")
        result["drive_error"] = "Backup on this laptop failed: %s" % e
        return result

    drive = (store.get_setting("drive_dir") or "").strip()
    if drive:
        try:
            if not os.path.isdir(drive):
                raise OSError("The folder '%s' was not found. Is Google Drive running?" % drive)
            dest = os.path.join(drive, DRIVE_SUBFOLDER)
            os.makedirs(os.path.join(dest, "uploads"), exist_ok=True)
            os.makedirs(os.path.join(dest, "database"), exist_ok=True)
            shutil.copy2(target, os.path.join(dest, "database", "apis_%s.db" % day))
            _prune(os.path.join(dest, "database"), "apis_*.db", 14)
            for name in os.listdir(store.UPLOADS):
                src = os.path.join(store.UPLOADS, name)
                dst = os.path.join(dest, "uploads", name)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
            with open(os.path.join(dest, "apis_data.xlsx"), "wb") as fh:
                fh.write(reports.workbook_bytes("all"))
            with open(os.path.join(dest, "READ ME.txt"), "w", encoding="utf-8") as fh:
                fh.write("This folder is the automatic backup of your APIS app.\n"
                         "database\\  = copies of your data, one per day\n"
                         "uploads\\   = your photos and certificate pictures\n"
                         "apis_data.xlsx = all your data in a spreadsheet you can open in Excel\n"
                         "To restore: see 'READ ME FIRST.txt' in the APIS folder.\n")
            store.set_setting("last_drive_backup", store.now().strftime("%Y-%m-%d %H:%M"))
            store.set_setting("last_drive_error", "")
            result["drive"] = True
        except Exception as e:
            msg = str(e)
            log.warning("Drive backup failed: %s", msg)
            store.set_setting("last_drive_error", msg)
            result["drive_error"] = msg
    return result


def status():
    s = store.get_settings()
    files = sorted(glob.glob(os.path.join(store.BACKUPS, "apis_*.db")), reverse=True)
    return {"last_backup": s["last_backup"], "last_drive_backup": s["last_drive_backup"], "last_drive_error": s["last_drive_error"],
            "drive_dir": s["drive_dir"], "count": len(files), "folder": store.BACKUPS,
            "detected": detect_drive()}


def start_backups(stop_event):
    def loop():
        stop_event.wait(8)
        while not stop_event.is_set():
            try:
                run_backup()
            except Exception:
                log.exception("Backup loop error")
            stop_event.wait(3 * 3600)
    t = threading.Thread(target=loop, name="apis-backup", daemon=True)
    t.start()
    return t
