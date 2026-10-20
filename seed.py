"""First-run setup. If a private file named seed_personal.py exists next to this one (it is NOT part of the public
repository), it fills in your own profile. Otherwise APIS starts with a blank, ready-to-edit profile."""
import store


def run_if_needed():
    if store.get_setting("seeded") or store.q1("SELECT 1 FROM profile LIMIT 1"):
        store.set_setting("seeded", True)
        return
    try:
        import seed_personal
    except ImportError:
        seed_personal = None
    if seed_personal:
        seed_personal.run()
        return
    store.update_profile({"name": "Your Name", "headline": "Add your headline here", "about": "Tap Edit to tell your story."})
    store.set_setting("seeded", True)
