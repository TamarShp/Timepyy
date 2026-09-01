import sys
import tkinter as tk
from database import ScheduleDatabase
from analytics import ScheduleAnalytics
from gui import ScheduleApp

print(">>> STEP 1: Starting main.py directly...", flush=True)

try:
    print(">>> STEP 2: Loading database...", flush=True)
    db = ScheduleDatabase()

    print(">>> STEP 3: Loading analytics...", flush=True)
    analytics = ScheduleAnalytics(db)

    print(">>> STEP 4: Creating Tkinter window...", flush=True)
    root = tk.Tk()

    print(">>> STEP 5: Initializing ScheduleApp...", flush=True)
    app = ScheduleApp(root, db, analytics)

    # Force window visibility on macOS
    root.lift()
    root.attributes('-topmost', True)
    root.after(300, lambda: root.attributes('-topmost', False))
    root.focus_force()

    print(">>> STEP 6: Entering mainloop (Window should be open now)...", flush=True)
    root.mainloop()

    print(">>> STEP 7: Application closed cleanly.", flush=True)

except Exception as e:
    print(f"\nCRITICAL ERROR OCCURRED:\n{e}", flush=True)
    import traceback
    traceback.print_exc()
