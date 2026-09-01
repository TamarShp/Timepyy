import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import calendar
from datetime import date, time, datetime, timedelta
from typing import List, Tuple, Optional
from models import UserProfile, RoutineSlot
from database import ScheduleDatabase
from analytics import ScheduleAnalytics


class ToolTip:
    """Displays informative floating tooltip on hover for compact event blocks."""
    def __init__(self, widget, text_func):
        self.widget = widget
        self.text_func = text_func
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text_func():
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text_func(), justify="left",
                         background="#1e293b", foreground="#ffffff", relief="solid",
                         borderwidth=1, font=("Helvetica", 9), padx=8, pady=5)
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class HabitRowItem:
    def __init__(self, parent_frame: tk.Frame, on_delete_callback, default_name="", default_time="18:00", default_dur="60", default_color="#bbf7d0", initial_days=None, default_reminder="None", default_buf="10"):
        self.on_delete_callback = on_delete_callback
        self.color_var = tk.StringVar(value=default_color)
        self.reminder_var = tk.StringVar(value=default_reminder)

        self.row_card = tk.Frame(parent_frame, bg="#ffffff", padx=10, pady=8, relief="solid", bd=1, highlightbackground="#cbd5e1", highlightthickness=1)
        self.row_card.pack(fill="x", pady=6)

        form_line = tk.Frame(self.row_card, bg="#ffffff")
        form_line.pack(fill="x", pady=(0, 6))

        # Activity Name
        tk.Label(form_line, text="Activity:", bg="#ffffff", fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 2))
        self.entry_name = ttk.Entry(form_line, width=10)
        if default_name:
            self.entry_name.insert(0, default_name)
        self.entry_name.grid(row=0, column=1, sticky="w", padx=(0, 4))

        # Time
        tk.Label(form_line, text="Time:", bg="#ffffff", fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 2))
        self.entry_time = ttk.Entry(form_line, width=5)
        self.entry_time.insert(0, default_time)
        self.entry_time.grid(row=0, column=3, sticky="w", padx=(0, 4))

        # Duration (Min)
        tk.Label(form_line, text="Min:", bg="#ffffff", fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=0, column=4, sticky="w", padx=(0, 2))
        self.entry_dur = ttk.Entry(form_line, width=3)
        self.entry_dur.insert(0, str(default_dur))
        self.entry_dur.grid(row=0, column=5, sticky="w", padx=(0, 4))

        # Buffer (Buf)
        tk.Label(form_line, text="Buf:", bg="#ffffff", fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=0, column=6, sticky="w", padx=(0, 2))
        self.entry_buf = ttk.Entry(form_line, width=3)
        self.entry_buf.insert(0, str(default_buf))
        self.entry_buf.grid(row=0, column=7, sticky="w", padx=(0, 4))

        # Alert
        tk.Label(form_line, text="Alert:", bg="#ffffff", fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=0, column=8, sticky="w", padx=(0, 2))
        self.combo_rem = ttk.Combobox(
            form_line, textvariable=self.reminder_var,
            values=["None", "15m", "30m", "1h"],
            width=6, state="readonly"
        )
        # המרה קטנה לטקסט קצר יותר כדי לחסוך רוחב
        rem_short = {"None": "None", "15 min before": "15m", "30 min before": "30m", "1 hour before": "1h", 0: "None", 15: "15m", 30: "30m", 60: "1h"}
        self.combo_rem.set(rem_short.get(default_reminder, "None"))
        self.combo_rem.grid(row=0, column=9, sticky="w", padx=(0, 4))

        # Color Button
        self.btn_color = tk.Button(
            form_line, text="Color", bg=self.color_var.get(), width=4, relief="groove",
            font=("Helvetica", 8, "bold"), cursor="pointinghand", command=self._pick_color
        )
        self.btn_color.grid(row=0, column=10, sticky="w", padx=(0, 4))

        # Delete Button
        btn_del = tk.Button(
            form_line, text="✕", bg="#fee2e2", fg="#991b1b", font=("Helvetica", 9, "bold"),
            relief="flat", width=2, cursor="pointinghand", command=lambda: self.on_delete_callback(self)
        )
        btn_del.grid(row=0, column=11, sticky="e")
        form_line.columnconfigure(11, weight=1)
        
        # Days Line
        days_line = tk.Frame(self.row_card, bg="#ffffff")
        days_line.pack(fill="x")

        tk.Label(days_line, text="Days:", bg="#ffffff", fg="#475569", font=("Helvetica", 9, "bold")).pack(side="left", padx=(0, 6))

        self.habit_days_vars = {}
        day_mapping = [("Sun", 0), ("Mon", 1), ("Tue", 2), ("Wed", 3), ("Thu", 4), ("Fri", 5), ("Sat", 6)]
        for lbl, d_idx in day_mapping:
            v = tk.BooleanVar(value=(initial_days is not None and d_idx in initial_days))
            chk = tk.Checkbutton(
                days_line, text=lbl, variable=v, bg="#ffffff", activebackground="#ffffff",
                fg="#1e293b", selectcolor="#ffffff", font=("Helvetica", 9)
            )
            chk.pack(side="left", padx=2)
            self.habit_days_vars[d_idx] = v

    def _pick_color(self):
        top_window = self.row_card.winfo_toplevel()
        
        was_topmost = top_window.attributes('-topmost')
        if was_topmost:
            top_window.attributes('-topmost', False)
            
        #open the color chooser dialog and get the selected color
        color = colorchooser.askcolor(parent=top_window, title="Choose Activity Color")[1]
        
        if was_topmost:
            top_window.attributes('-topmost', True)
            top_window.lift()

        if color:
            self.color_var.set(color)
            self.btn_color.configure(bg=color)

    def destroy(self):
        self.row_card.destroy()

class OnboardingDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: ScheduleDatabase, on_complete_callback=None):
        super().__init__(parent)
        self.db = db
        self.on_complete_callback = on_complete_callback
        self.title("Personal Rhythm & Core Habits Setup")
        self.geometry("640x760")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.bg_main = "#f0f4f8"
        self.bg_card = "#ffffff"
        self.accent_color = "#2b6cb0"
        self.configure(bg=self.bg_main)
        self.lift()
        self.attributes('-topmost', True)

        self.color_lunch = tk.StringVar(value="#fed7aa")
        self.habit_rows: List[HabitRowItem] = []

        self._build_ui()
        self._load_existing_habits()

    def _build_ui(self):
        header_frame = tk.Frame(self, bg=self.bg_main, padx=20, pady=12)
        header_frame.pack(fill="x")

        tk.Label(header_frame, text="Smart Scheduler - Habits & Wellness", font=("Helvetica", 16, "bold"),
                 bg=self.bg_main, fg="#1a365d").pack(pady=(0, 2))
        tk.Label(header_frame, text="Lock in your nutrition, workouts, and personal habits before adding daily tasks.",
                 wraplength=580, font=("Helvetica", 10), bg=self.bg_main, fg="#4a5568").pack()

        canvas = tk.Canvas(self, bg=self.bg_main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=self.bg_main, padx=16)

        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _configure_canvas_width(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _configure_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="top", fill="both", expand=True, padx=4)
        scrollbar.pack(side="right", fill="y")

        # Profile
        user_box = tk.LabelFrame(scroll_content, text=" Profile & Sleep Boundaries ", font=("Helvetica", 11, "bold"),
                                 bg=self.bg_card, fg="#2d3748", padx=14, pady=10, relief="solid", bd=1)
        user_box.pack(fill="x", pady=6)

        tk.Label(user_box, text="Full Name:", bg=self.bg_card, fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=0, column=0, sticky="w", padx=4, pady=5)
        self.entry_name = ttk.Entry(user_box, width=28)
        self.entry_name.grid(row=0, column=1, columnspan=3, sticky="w", padx=4, pady=5)

        tk.Label(user_box, text="Wake Time (HH:MM):", bg=self.bg_card, fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=1, column=0, sticky="w", padx=4, pady=5)
        self.entry_wake = ttk.Entry(user_box, width=10)
        self.entry_wake.grid(row=1, column=1, sticky="w", padx=4, pady=5)

        tk.Label(user_box, text="Bed Time (HH:MM):", bg=self.bg_card, fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=1, column=2, sticky="w", padx=(14, 4), pady=5)
        self.entry_sleep = ttk.Entry(user_box, width=10)
        self.entry_sleep.grid(row=1, column=3, sticky="w", padx=4, pady=5)

        # Lunch Window
        meal_box = tk.LabelFrame(scroll_content, text=" Daily Nutrition Protection ", font=("Helvetica", 11, "bold"),
                                 bg=self.bg_card, fg="#2d3748", padx=14, pady=10, relief="solid", bd=1)
        meal_box.pack(fill="x", pady=6)

        self.var_lunch = tk.BooleanVar(value=True)
        chk_lunch = tk.Checkbutton(meal_box, text="Reserve fixed daily lunch window",
                                   variable=self.var_lunch, command=self._toggle_lunch,
                                   bg=self.bg_card, activebackground=self.bg_card, fg="#1e293b",
                                   selectcolor="#ffffff", font=("Helvetica", 9))
        chk_lunch.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.btn_lunch_color = tk.Button(meal_box, text="Color", bg=self.color_lunch.get(), width=6, relief="groove",
                                         command=lambda: self._pick_color(self.color_lunch, self.btn_lunch_color))
        self.btn_lunch_color.grid(row=0, column=3, sticky="e", padx=4)

        tk.Label(meal_box, text="Start (HH:MM):", bg=self.bg_card, fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.entry_lunch_time = ttk.Entry(meal_box, width=10)
        self.entry_lunch_time.grid(row=1, column=1, sticky="w", padx=4, pady=4)

        tk.Label(meal_box, text="Duration (min):", bg=self.bg_card, fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=1, column=2, sticky="w", padx=(14, 4), pady=4)
        self.entry_lunch_dur = ttk.Entry(meal_box, width=8)
        self.entry_lunch_dur.grid(row=1, column=3, sticky="w", padx=4, pady=4)
        # Lunch reminder combo
        tk.Label(meal_box, text="Alert:", bg=self.bg_card, fg="#1e293b", font=("Helvetica", 9, "bold")).grid(row=1, column=4, sticky="w", padx=(10, 4), pady=4)
        self.lunch_rem_var = tk.StringVar(value="None")
        self.combo_lunch_rem = ttk.Combobox(
            meal_box, textvariable=self.lunch_rem_var,
            values=["None", "15 min before", "30 min before", "1 hour before"],
            width=11, state="readonly"
        )
        self.combo_lunch_rem.grid(row=1, column=5, sticky="w", padx=4, pady=4)

        # Habits
        self.habits_frame_box = tk.LabelFrame(scroll_content, text=" Recurring Activities & Routines ", font=("Helvetica", 11, "bold"),
                                              bg=self.bg_card, fg="#2d3748", padx=12, pady=10, relief="solid", bd=1)
        self.habits_frame_box.pack(fill="x", pady=6)

        self.habits_container = tk.Frame(self.habits_frame_box, bg=self.bg_card)
        self.habits_container.pack(fill="x")

        btn_add_habit = tk.Button(
            self.habits_frame_box, text="➕ Add Another Habit / Routine",
            font=("Helvetica", 10, "bold"), bg="#f1f5f9", fg="#2b6cb0",
            relief="groove", padx=10, pady=5, cursor="pointinghand", command=lambda: self._add_habit_row()
        )
        btn_add_habit.pack(anchor="w", pady=(8, 2))

        # Bottom Bar
        bottom_bar = tk.Frame(self, bg=self.bg_main, pady=12)
        bottom_bar.pack(side="bottom", fill="x")

        btn_finish = tk.Button(
            bottom_bar, text="Lock in Habits & Open Planner", command=self._save_profile,
            font=("Helvetica", 11, "bold"), bg=self.accent_color, fg="black",
            padx=20, pady=8, relief="raised", bd=1, cursor="pointinghand"
        )
        btn_finish.pack()

    def _load_existing_habits(self):
            user, routine_details = self.db.load_user_profile_with_colors()
            if user:
                self.entry_name.delete(0, tk.END)
                self.entry_name.insert(0, user.full_name)
                self.entry_wake.delete(0, tk.END)
                self.entry_wake.insert(0, user.wake_time.strftime("%H:%M"))
                self.entry_sleep.delete(0, tk.END)
                self.entry_sleep.insert(0, user.sleep_time.strftime("%H:%M"))
    
                lunch_slots = [r for r in routine_details if r["slot"].title == "Lunch Break"]
                other_slots = [r for r in routine_details if r["slot"].title != "Lunch Break"]
    
                if lunch_slots:
                    first_lunch = lunch_slots[0]
                    self.var_lunch.set(True)
                    self.entry_lunch_time.delete(0, tk.END)
                    self.entry_lunch_time.insert(0, first_lunch["slot"].start_clock.strftime("%H:%M"))
                    self.entry_lunch_dur.delete(0, tk.END)
                    self.entry_lunch_dur.insert(0, str(first_lunch["slot"].duration_minutes))
                    self.color_lunch.set(first_lunch["color_hex"])
                    self.btn_lunch_color.configure(bg=first_lunch["color_hex"])
                else:
                    self.var_lunch.set(False)
                    self._toggle_lunch()
    
                grouped = {}
                for r_item in other_slots:
                    slot = r_item["slot"]
                    key = (slot.title, slot.start_clock.strftime("%H:%M"), slot.duration_minutes,slot.bufferbefore_minutes, r_item["color_hex"])
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(slot.day_of_week)
    
                for (h_name, h_time, h_dur, h_buf, h_col), days_list in grouped.items():
                    self._add_habit_row(name=h_name, def_time=h_time, def_dur=str(h_dur), def_buf=str(h_buf), def_color=h_col, initial_days=days_list)
    
            if not self.habit_rows:
                self._add_habit_row(name="", def_time="18:00", def_dur="60", def_color="#bbf7d0")
    
            if not user:
                self.entry_name.insert(0, "User")
                self.entry_wake.insert(0, "07:00")
                self.entry_sleep.insert(0, "23:00")
                self.entry_lunch_time.insert(0, "13:00")
                self.entry_lunch_dur.insert(0, "45")
            

    def _pick_color(self, target_var: tk.StringVar, target_btn: tk.Button):
        self.attributes('-topmost', False)
        # open the color chooser dialog and get the selected color
        color = colorchooser.askcolor(parent=self, title="Choose Color")[1]
        
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()

        if color:
            target_var.set(color)
            target_btn.configure(bg=color)

    def _toggle_lunch(self):
        state = "normal" if self.var_lunch.get() else "disabled"
        self.entry_lunch_time.configure(state=state)
        self.entry_lunch_dur.configure(state=state)
        self.btn_lunch_color.configure(state=state)

    def _add_habit_row(self, name="", def_time="18:00", def_dur="60", def_buf="10", def_color="#bbf7d0", initial_days=None):
        palette = ["#bbf7d0", "#fed7aa", "#cff4fc", "#e9d5ff", "#fecdd3", "#fef08a"]
        color = def_color if def_color else palette[len(self.habit_rows) % len(palette)]
        item = HabitRowItem(self.habits_container, self._remove_habit_row, default_name=name,
                            default_time=def_time, default_dur=def_dur, default_buf=def_buf, default_color=color, initial_days=initial_days)
        self.habit_rows.append(item)

    def _remove_habit_row(self, item: HabitRowItem):
        if len(self.habit_rows) <= 1:
            messagebox.showinfo("Notice", "At least one habit entry should remain.")
            return
        item.destroy()
        self.habit_rows.remove(item)

    def _save_profile(self):
        try:
            name = self.entry_name.get().strip() or "Calendar Owner"
            wake_t = datetime.strptime(self.entry_wake.get().strip(), "%H:%M").time()
            sleep_t = datetime.strptime(self.entry_sleep.get().strip(), "%H:%M").time()

            routines: List[RoutineSlot] = []
            routine_colors: List[str] = []
            routine_reminders: List[int] = []

            rem_map = {"None": 0, "15 min before": 15, "30 min before": 30, "1 hour before": 60}

            if self.var_lunch.get():
                lunch_t = datetime.strptime(self.entry_lunch_time.get().strip(), "%H:%M").time()
                lunch_dur = int(self.entry_lunch_dur.get().strip())
                lunch_rem = rem_map.get(self.lunch_rem_var.get(), 0)
                for day in range(7):
                    routines.append(RoutineSlot(
                        title="Lunch Break", category="Personal",
                        day_of_week=day, start_clock=lunch_t, duration_minutes=lunch_dur,
                        buffer_before_minutes=5, buffer_after_minutes=5
                    ))
                    routine_colors.append(self.color_lunch.get())
                    routine_reminders.append(lunch_rem)

            for item in self.habit_rows:
                h_name = item.entry_name.get().strip()
                selected_days = [d_idx for d_idx, v in item.habit_days_vars.items() if v.get()]
                if h_name and selected_days:
                    h_t = datetime.strptime(item.entry_time.get().strip(), "%H:%M").time()
                    h_dur = int(item.entry_dur.get().strip())
                    h_buf = int(item.entry_buf.get().strip()) # קליטת ה-Buffer מהמשתמש
                    h_color = item.color_var.get()
                    h_rem = rem_map.get(item.reminder_var.get(), 0)

                    for d in selected_days:
                        routines.append(RoutineSlot(
                            title=h_name, category="Health",
                            day_of_week=d, start_clock=h_t, duration_minutes=h_dur,
                            buffer_before_minutes=h_buf, buffer_after_minutes=h_buf # שימוש ב-Buffer המוגדר
                        ))
                        routine_colors.append(h_color)
                        routine_reminders.append(h_rem)

            user = UserProfile(id=0, full_name=name, wake_time=wake_t, sleep_time=sleep_t, routines=routines)
            self.db.save_user_profile_with_colors(user, routine_colors, routine_reminders)

            messagebox.showinfo("Habits Locked", f"Saved {len(routines)} recurring slots for {user.full_name}.")
            if self.on_complete_callback:
                self.on_complete_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Validation Error", f"Time must be formatted HH:MM:\n{e}")

class EventActionDialog(tk.Toplevel):
    def __init__(self, app: "ScheduleApp", db: ScheduleDatabase, event_data: dict, on_update_callback):
        super().__init__(app.root)
        self.app = app
        self.db = db
        self.event_data = event_data
        self.on_update_callback = on_update_callback

        self.title(f"Manage Event: {event_data['title']}")
        self.geometry("450x560")
        self.resizable(False, False)
        self.transient(app.root)
        self.grab_set()

        self.configure(bg="#f8fafc")
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg="#f8fafc", padx=20, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(
            container, text="Edit or Remove Event", font=("Helvetica", 15, "bold"),
            bg="#f8fafc", fg="#1e3a8a"
        ).pack(pady=(0, 14))

        form_frame = tk.Frame(
            container, bg="#ffffff", padx=16, pady=14,
            relief="solid", bd=1, highlightbackground="#cbd5e1", highlightthickness=1
        )
        form_frame.pack(fill="x", pady=4)

        def create_form_row(row_idx, label_text):
            lbl = tk.Label(
                form_frame, text=label_text, bg="#ffffff", fg="#0f172a",
                font=("Helvetica", 10, "bold"), anchor="w"
            )
            lbl.grid(row=row_idx, column=0, sticky="w", pady=6, padx=(0, 12))
            entry = ttk.Entry(form_frame, width=24)
            entry.grid(row=row_idx, column=1, sticky="ew", pady=6)
            return entry

        #form fields
        self.entry_title = create_form_row(0, "Event Title:")
        self.entry_title.insert(0, self.event_data["title"])

        self.entry_start_date = create_form_row(1, "Start Date (YYYY-MM-DD):")
        self.entry_start_date.insert(0, self.event_data["event_date"])

        self.entry_end_date = create_form_row(2, "End Date (YYYY-MM-DD):")
        self.entry_end_date.insert(0, self.event_data.get("end_date", self.event_data["event_date"]))

        self.entry_time = create_form_row(3, "Start Time (HH:MM):")
        clock_str = self.event_data["start_clock"][:5]
        self.entry_time.insert(0, clock_str)

        self.entry_dur = create_form_row(4, "Duration (minutes):")
        self.entry_dur.insert(0, str(self.event_data["duration_minutes"]))

        self.entry_buf = create_form_row(5, "Buffer (minutes):")
        self.entry_buf.insert(0, str(self.event_data.get("buffer_before_minutes", 15)))

        # שדה התזכורת עם StringVar מפורש
        lbl_rem = tk.Label(
            form_frame, text="Reminder Alert:", bg="#ffffff", fg="#0f172a",
            font=("Helvetica", 10, "bold"), anchor="w"
        )
        lbl_rem.grid(row=6, column=0, sticky="w", pady=6, padx=(0, 12))

        self.reminder_var = tk.StringVar()
        self.combo_reminder = ttk.Combobox(
            form_frame,
            textvariable=self.reminder_var,
            values=["None", "15 min before", "30 min before", "1 hour before"],
            width=22,
            state="readonly"
        )

        # המרה בטוחה מערך קיים
        try:
            curr_val = int(self.event_data.get("reminder_min", 0))
        except (ValueError, TypeError):
            curr_val = 0

        reverse_map = {0: "None", 15: "15 min before", 30: "30 min before", 60: "1 hour before"}
        self.reminder_var.set(reverse_map.get(curr_val, "None"))
        self.combo_reminder.grid(row=6, column=1, sticky="ew", pady=6)

        form_frame.columnconfigure(1, weight=1)

        # כפתורים
        btn_frame = tk.Frame(container, bg="#f8fafc")
        btn_frame.pack(fill="x", pady=(18, 0))

        btn_save = tk.Button(
            btn_frame, text="Save Changes", bg="#2563eb", fg="black",
            highlightbackground="#2563eb", font=("Helvetica", 10, "bold"),
            padx=14, pady=7, cursor="pointinghand", command=self._save_changes
        )
        btn_save.pack(side="left", expand=True, padx=6)

        btn_delete = tk.Button(
            btn_frame, text="Delete Event", bg="#dc2626", fg="red",
            highlightbackground="#dc2626", font=("Helvetica", 10, "bold"),
            padx=14, pady=7, cursor="pointinghand", command=self._delete_event
        )
        btn_delete.pack(side="right", expand=True, padx=6)

    def _save_changes(self):
        try:
            new_title = self.entry_title.get().strip()
            new_start_d = date.fromisoformat(self.entry_start_date.get().strip())
            new_end_d = date.fromisoformat(self.entry_end_date.get().strip())

            if new_end_d < new_start_d:
                messagebox.showerror("Validation Error", "End date cannot be earlier than start date.")
                return

            t_parts = [int(p) for p in self.entry_time.get().strip().split(":")]
            new_time = time(t_parts[0], t_parts[1])
            new_dur = int(self.entry_dur.get().strip())
            new_buf = int(self.entry_buf.get().strip())

            # מיפוי הבחירה מתוך ה-StringVar
            selected_str = self.reminder_var.get().strip()
            rem_map = {
                "None": 0,
                "15 min before": 15,
                "30 min before": 30,
                "1 hour before": 60
            }
            new_rem = rem_map.get(selected_str, 0)

            start_dt = datetime.combine(new_start_d, new_time)
            total_start = start_dt - timedelta(minutes=new_buf)
            total_end = start_dt + timedelta(minutes=new_dur + new_buf)

            # update the database record with the new values
            self.db.update_event_record(
                event_id=self.event_data["id"],
                title=new_title,
                category=self.event_data["category"],
                event_date_str=new_start_d.isoformat(),
                end_date_str=new_end_d.isoformat(),
                start_clock_str=new_time.isoformat(),
                duration=new_dur,
                buf_before=new_buf,
                buf_after=new_buf,
                total_start_str=total_start.isoformat(),
                total_end_str=total_end.isoformat(),
                color_hex=self.event_data["color_hex"],
                reminder_min=new_rem
            )
            # update the local event_data dictionary to reflect the changes
            self.event_data["reminder_min"] = new_rem

            # Reset the notified cache on the app instance
            # Reset the notified cache on the app instance using matching key format
            if hasattr(self.app, "_notified_events"):
                self.app._notified_events.discard(f"ev_{self.event_data['id']}")
                self.app._notified_events.discard(self.event_data["id"])

            messagebox.showinfo("Updated", f"Event '{new_title}' updated successfully!")
            self.on_update_callback()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to save changes:\n{e}")

    def _delete_event(self):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{self.event_data['title']}'?")
        if confirm:
            self.db.delete_event(self.event_data["id"])
            messagebox.showinfo("Deleted", "Event removed from calendar.")
            self.on_update_callback()
            self.destroy()


class ScheduleApp:
    def __init__(self, root: tk.Tk, db: ScheduleDatabase, analytics: ScheduleAnalytics):
        self.root = root
        self.db = db
        self.analytics = analytics
        self.root.title("TimePy - Smart Weekly & Daily Planner")
        self.root.geometry("1300x900")
        
        self.bg_dashboard = "#edf2f7"
        self.root.configure(bg=self.bg_dashboard)

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("TEntry", fieldbackground="#ffffff", foreground="#0f172a", bordercolor="#cbd5e1")
        style.configure("TCombobox", fieldbackground="#ffffff", foreground="#0f172a", background="#f8fafc", bordercolor="#cbd5e1")
        style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])

        self.current_date = date.today()
        sunday_offset = (self.current_date.weekday() + 1) % 7
        self.current_week_start = self.current_date - timedelta(days=sunday_offset)
        self.active_view = tk.StringVar(value="Week")
        self.mindful_enabled = tk.BooleanVar(value=True)

        self.category_colors = {}
        self.load_categories_from_db()

        # Top Bar
        top_bar = tk.Frame(root, bg=self.bg_dashboard, padx=15, pady=6)
        top_bar.pack(fill="x")

        self.lbl_welcome = tk.Label(top_bar, text="Welcome to TimePy", font=("Helvetica", 13, "bold"),
                                    bg=self.bg_dashboard, fg="#1a365d")
        self.lbl_welcome.pack(side="left")

        right_actions = tk.Frame(top_bar, bg=self.bg_dashboard)
        right_actions.pack(side="right")

        chk_mindful = ttk.Checkbutton(right_actions, text="🌿 Mindful Check-ins", variable=self.mindful_enabled)
        chk_mindful.pack(side="left", padx=(0, 12))

        btn_edit_profile = ttk.Button(right_actions, text="⚙ Core Habits & Wellness", command=self.open_onboarding)
        btn_edit_profile.pack(side="left")

        # Mindful Banner Notification
        self.banner_frame = tk.Frame(root, bg="#ecfdf5", padx=12, pady=6, relief="solid", bd=1, highlightbackground="#a7f3d0")
        self.lbl_banner = tk.Label(
            self.banner_frame,
            text="🌿 Friendly reminder: Have you carved out 15 minutes of quiet time or hydration for yourself today?",
            bg="#ecfdf5", fg="#065f46", font=("Helvetica", 10, "bold")
        )
        self.lbl_banner.pack(side="left", padx=6)
        btn_dismiss_banner = tk.Button(self.banner_frame, text="✕", bg="#ecfdf5", fg="#065f46", relief="flat",
                                       font=("Helvetica", 9, "bold"), command=self.banner_frame.pack_forget)
        btn_dismiss_banner.pack(side="right")
        self.banner_frame.pack(fill="x", padx=15, pady=(2, 4))

        # Event Form
        form_frame = ttk.LabelFrame(root, text=" Schedule New Event ", padding=10)
        form_frame.pack(fill="x", padx=15, pady=4)

        ttk.Label(form_frame, text="Title:").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.entry_title = ttk.Entry(form_frame, width=16)
        self.entry_title.grid(row=0, column=1, sticky="w", padx=4, pady=3)

        ttk.Label(form_frame, text="Category:").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        self.combo_cat = ttk.Combobox(form_frame, width=12, state="readonly")
        self.combo_cat.grid(row=0, column=3, sticky="w", padx=4, pady=3)

        btn_new_cat = ttk.Button(form_frame, text="+ Cat", width=6, command=self.open_add_category_dialog)
        btn_new_cat.grid(row=0, column=4, padx=4, pady=3)

        ttk.Label(form_frame, text="Start Date:").grid(row=0, column=5, sticky="w", padx=4, pady=3)
        self.entry_date = ttk.Entry(form_frame, width=11)
        self.entry_date.insert(0, str(self.current_date))
        self.entry_date.grid(row=0, column=6, sticky="w", padx=4, pady=3)

        self.is_multiday = tk.BooleanVar(value=False)
        chk_multiday = ttk.Checkbutton(form_frame, text="Multi-day Span", variable=self.is_multiday, command=self.toggle_multiday_ui)
        chk_multiday.grid(row=0, column=7, padx=(8, 2), sticky="w")

        ttk.Label(form_frame, text="End Date:").grid(row=0, column=8, sticky="w", padx=4, pady=3)
        self.entry_end_date = ttk.Entry(form_frame, width=11, state="disabled")
        self.entry_end_date.insert(0, str(self.current_date + timedelta(days=2)))
        self.entry_end_date.grid(row=0, column=9, sticky="w", padx=4, pady=3)

        # Row 1: Time, Duration, Buffer, Reminder, and Schedule Button
        ttk.Label(form_frame, text="Start (HH:MM):").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.entry_time = ttk.Entry(form_frame, width=10)
        self.entry_time.insert(0, "14:00")
        self.entry_time.grid(row=1, column=1, sticky="w", padx=4, pady=3)

        ttk.Label(form_frame, text="Duration (min):").grid(row=1, column=2, sticky="w", padx=4, pady=3)
        self.entry_dur = ttk.Entry(form_frame, width=8)
        self.entry_dur.insert(0, "60")
        self.entry_dur.grid(row=1, column=3, sticky="w", padx=4, pady=3)

        ttk.Label(form_frame, text="Buffer (min):").grid(row=1, column=4, sticky="w", padx=4, pady=3)
        self.entry_buf = ttk.Entry(form_frame, width=6)
        self.entry_buf.insert(0, "15")
        self.entry_buf.grid(row=1, column=5, sticky="w", padx=4, pady=3)

        ttk.Label(form_frame, text="Reminder:").grid(row=1, column=6, sticky="w", padx=(8, 4), pady=3)
        self.combo_reminder = ttk.Combobox(
            form_frame,
            values=["None", "15 min before", "30 min before", "1 hour before"],
            width=13,
            state="readonly"
        )
        self.combo_reminder.current(0)
        self.combo_reminder.grid(row=1, column=7, sticky="w", padx=4, pady=3)

        btn_submit = ttk.Button(form_frame, text="Schedule Event", command=self.add_event)
        btn_submit.grid(row=1, column=8, columnspan=2, sticky="e", padx=(10, 4), pady=3)
        rec_frame = tk.Frame(form_frame, bg="#ffffff", padx=8, pady=4, relief="groove", bd=1)
        rec_frame.grid(row=2, column=0, columnspan=10, sticky="ew", pady=(4, 2))

        self.is_recurring = tk.BooleanVar(value=False)
        chk_rec = ttk.Checkbutton(rec_frame, text="Repeating Event", variable=self.is_recurring, command=self.toggle_recurrence_ui)
        chk_rec.grid(row=0, column=0, sticky="w", padx=4)

        ttk.Label(rec_frame, text="Frequency:").grid(row=0, column=1, padx=(6, 2))
        self.combo_freq = ttk.Combobox(rec_frame, values=["Weekly", "Monthly", "Yearly"], width=9, state="disabled")
        self.combo_freq.current(0)
        self.combo_freq.grid(row=0, column=2, padx=4)
        self.combo_freq.bind("<<ComboboxSelected>>", self.on_freq_change)
        self.days_vars = {}
        day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        days_box = tk.Frame(rec_frame, bg="#ffffff")
        days_box.grid(row=0, column=3, padx=(10, 4))
        for lbl in day_labels:
            var = tk.BooleanVar(value=False)
            chk = ttk.Checkbutton(days_box, text=lbl, variable=var, state="disabled")
            chk.pack(side="left", padx=2)
            self.days_vars[lbl] = (var, chk)

        # Navigation
        nav_bar = tk.Frame(root, bg=self.bg_dashboard, padx=15, pady=4)
        nav_bar.pack(fill="x")

        tk.Label(nav_bar, text="View:", font=("Helvetica", 10, "bold"), bg=self.bg_dashboard).pack(side="left", padx=(0, 4))
        ttk.Radiobutton(nav_bar, text="Weekly View", variable=self.active_view, value="Week", command=self.switch_view).pack(side="left", padx=4)
        ttk.Radiobutton(nav_bar, text="Day View", variable=self.active_view, value="Day", command=self.switch_view).pack(side="left", padx=(0, 15))

        tk.Label(nav_bar, text="Step:", font=("Helvetica", 10, "bold"), bg=self.bg_dashboard).pack(side="left", padx=(0, 4))
        self.nav_step = tk.StringVar(value="Standard")
        ttk.Combobox(nav_bar, values=["Standard", "Month", "Year"], textvariable=self.nav_step, width=9, state="readonly").pack(side="left", padx=(0, 10))

        tk.Button(nav_bar, text="◀ Previous", font=("Helvetica", 10, "bold"), bg="#ffffff", command=lambda: self.navigate_time(-1)).pack(side="left", padx=3)
        tk.Button(nav_bar, text="Today", font=("Helvetica", 10, "bold"), bg="#e2e8f0", command=self.navigate_today).pack(side="left", padx=3)
        tk.Button(nav_bar, text="Next ▶", font=("Helvetica", 10, "bold"), bg="#ffffff", command=lambda: self.navigate_time(1)).pack(side="left", padx=3)

        self.lbl_current_range = tk.Label(nav_bar, text="", font=("Helvetica", 12, "bold"), bg=self.bg_dashboard, fg="#2c5282")
        self.lbl_current_range.pack(side="right")

        # Timetable
        calendar_frame = ttk.LabelFrame(root, text=" Calendar Timetable (Hover for details, click to Edit/Delete) ", padding=6)
        calendar_frame.pack(fill="both", expand=True, padx=15, pady=4)

        canvas = tk.Canvas(calendar_frame, bg="#ffffff")
        scrollbar = ttk.Scrollbar(calendar_frame, orient="vertical", command=canvas.yview)
        self.grid_container = tk.Frame(canvas, bg="#ffffff")
        self.grid_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.grid_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.start_hour = 7
        self.end_hour = 23
        self.hour_height_px = 64  # Precise pixel height per hour

        self.update_category_combobox()
        self.check_initial_profile()
        self.render_grid()

        # Check-in prompt timer (simulating mindful ping)
        self.root.after(3000, self._trigger_mindful_popup)
        self._start_reminder_daemon()
        self._auto_refresh_time_indicator()
    
    def _play_alert_sound(self):
        """Plays a gentle native macOS alert sound."""
        import subprocess
        try:
            # Plays the built-in system chime without needing any permissions
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])
        except Exception:
            pass

    def _show_reminder_popup(self, title: str, minutes_left: int, buf: int):
        if hasattr(self, "_active_reminder_popup") and self._active_reminder_popup is not None:
            try:
                if self._active_reminder_popup.winfo_exists():
                    return
            except Exception:
                pass

        self._play_alert_sound()

        popup = tk.Toplevel(self.root)
        self._active_reminder_popup = popup
        popup.title("Upcoming Reminder")
        popup.geometry("380x190")
        popup.resizable(False, False)
        popup.configure(bg="#1e293b")
        popup.attributes("-topmost", True)

        tk.Label(popup, text="⏰ Upcoming Event Alert", font=("Helvetica", 12, "bold"), bg="#1e293b", fg="#38bdf8").pack(pady=(15, 6))

        # עדכון הטקסט כך שיציג מתי ה-Buffer מתחיל
        if buf > 0:
            msg = f"Time to get ready! '{title}' starts in {minutes_left + buf} minutes."
            msg += f"\n(Your {buf}m prep/travel buffer starts in {minutes_left} minutes)"
        else:
            msg = f"'{title}' starts in {minutes_left} minutes!"

        tk.Label(popup, text=msg, font=("Helvetica", 10), bg="#1e293b", fg="#f8fafc", justify="center").pack(pady=6)

        def _on_close():
            self._active_reminder_popup = None
            popup.destroy()

        btn = tk.Button(popup, text="Got It", font=("Helvetica", 10, "bold"), bg="#38bdf8", fg="#0f172a", relief="flat", padx=16, pady=4, cursor="hand2", command=_on_close)
        btn.pack(pady=(10, 0))
        popup.protocol("WM_DELETE_WINDOW", _on_close)


    def _start_reminder_daemon(self):
        import math
        now = datetime.now()
        today_date = now.date()
        today_weekday = (today_date.weekday() + 1) % 7

        if not hasattr(self, "_notified_events"):
            self._notified_events = set()

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # בדיקת אירועים רגילים
                cursor.execute("SELECT id, title, event_date, start_clock, buffer_before_minutes, reminder_min FROM events WHERE reminder_min > 0;")
                for row in cursor.fetchall():
                    ev_id, title, e_date_str, e_time_str, buf, rem_min = row
                    t_parts = [int(p) for p in e_time_str.split(":")]
                    ev_start = datetime.combine(date.fromisoformat(e_date_str), time(t_parts[0], t_parts[1]))
                    
                    # חיסור ה-Buffer משעת ההתחלה כדי לקבל את זמן ההתראה האמיתי
                    effective_start = ev_start - timedelta(minutes=buf)
                    diff_minutes = (effective_start - now).total_seconds() / 60.0

                    if -0.5 <= diff_minutes <= (float(rem_min) + 0.5) and f"ev_{ev_id}" not in self._notified_events:
                        self._notified_events.add(f"ev_{ev_id}")
                        disp_min = max(1, math.ceil(diff_minutes))
                        self._show_reminder_popup(title, disp_min, buf)

                # בדיקת הרגלים קבועים
                exclusions = self.db.get_routine_exclusions()
                cursor.execute("SELECT id, title, start_clock, buffer_before_minutes, reminder_min FROM user_routines WHERE day_of_week = ? AND reminder_min > 0;", (today_weekday,))
                for row in cursor.fetchall():
                    r_id, r_title, r_clock_str, r_buf, r_rem_min = row
                    
                    if (r_id, today_date.isoformat()) in exclusions:
                        continue

                    t_parts = [int(p) for p in r_clock_str.split(":")]
                    r_start = datetime.combine(today_date, time(t_parts[0], t_parts[1]))
                    
                    # חיסור ה-Buffer משעת ההתחלה להרגלים
                    effective_start = r_start - timedelta(minutes=r_buf)
                    diff_minutes = (effective_start - now).total_seconds() / 60.0

                    r_key = f"routine_{r_id}_{today_date.isoformat()}"
                    if -0.5 <= diff_minutes <= (float(r_rem_min) + 0.5) and r_key not in self._notified_events:
                        self._notified_events.add(r_key)
                        disp_min = max(1, math.ceil(diff_minutes))
                        self._show_reminder_popup(f"Core Habit: {r_title}", disp_min, r_buf)

        except Exception as err:
            print(f">>> Reminder Daemon Error: {err}")

        self.root.after(10000, self._start_reminder_daemon)

    def _trigger_mindful_popup(self):
        # Always convert to integer milliseconds (e.g. 0.5 * 60 * 1000 = 30000)
        interval_ms = int(20 * 60 * 1000)

        if self.mindful_enabled.get():
            messages = [
                "Taking even 5 minutes to breathe and disconnect can recharge your entire afternoon.",
                "Your schedule looks active! Remember to schedule time for yourself just like any meeting.",
                "Have you had a glass of water and stepped away from the screen recently?",
                "Quick posture check: drop your shoulders, unclench your jaw, and take a deep breath."
            ]
            import random
            selected = random.choice(messages)
            self.lbl_banner.configure(text=f"🌿 Friendly Check-in: {selected}")
            
            # Repack banner cleanly below the top control bar
            self.banner_frame.pack_forget()
            self.banner_frame.pack(fill="x", padx=15, pady=(2, 4), after=self.root.winfo_children()[0])

        # Schedule the next check-in
        self.root.after(interval_ms, self._trigger_mindful_popup)

    def toggle_multiday_ui(self):
        state = "normal" if self.is_multiday.get() else "disabled"
        self.entry_end_date.configure(state=state)

    def toggle_recurrence_ui(self):
        state = "readonly" if self.is_recurring.get() else "disabled"
        self.combo_freq.configure(state=state)
        self.on_freq_change()

    def on_freq_change(self, event=None):
        """Enable day checkboxes ONLY when frequency is Weekly."""
        is_weekly = self.is_recurring.get() and (self.combo_freq.get() == "Weekly")
        day_state = "normal" if is_weekly else "disabled"

        for var, chk in self.days_vars.values():
            if not is_weekly:
                var.set(False)  # Clear days when not weekly
            chk.configure(state=day_state)
    def switch_view(self):
        self.render_grid()

    def navigate_today(self):
        self.current_date = date.today()
        sunday_offset = (self.current_date.weekday() + 1) % 7
        self.current_week_start = self.current_date - timedelta(days=sunday_offset)
        self.render_grid()

    def navigate_time(self, direction: int):
        step = self.nav_step.get()
        if self.active_view.get() == "Day":
            if step == "Standard":
                self.current_date += timedelta(days=1 * direction)
            elif step == "Month":
                self.current_date += timedelta(days=30 * direction)
            elif step == "Year":
                self.current_date += timedelta(days=365 * direction)
        else:
            if step == "Standard":
                self.current_week_start += timedelta(days=7 * direction)
            elif step == "Month":
                self.current_week_start += timedelta(days=28 * direction)
            elif step == "Year":
                self.current_week_start += timedelta(days=364 * direction)
        self.render_grid()

    def check_initial_profile(self):
        user = self.db.load_user_profile()
        if not user:
            self.open_onboarding()
        else:
            self.lbl_welcome.configure(text=f"Welcome back, {user.full_name}")

    def open_onboarding(self):
        dialog = OnboardingDialog(self.root, self.db, on_complete_callback=self.render_grid)
        self.root.wait_window(dialog)
        user = self.db.load_user_profile()
        if user:
            self.lbl_welcome.configure(text=f"Welcome back, {user.full_name}")
            self.render_grid()

    def load_categories_from_db(self):
        records = self.db.get_categories()
        self.category_colors = {cat: hex_code for cat, hex_code in records}

    def update_category_combobox(self):
        cats = list(self.category_colors.keys())
        self.combo_cat["values"] = cats
        if cats:
            self.combo_cat.current(0)

    def open_add_category_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Category")
        dialog.geometry("320x200")
        dialog.configure(bg="#eaf2f8")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Category Name:", bg="#eaf2f8", font=("Helvetica", 10, "bold")).pack(pady=(12, 4))
        entry_cat_name = ttk.Entry(dialog, width=22)
        entry_cat_name.pack(pady=4)

        color_var = tk.StringVar(value="#e2e3e5")
        btn_pick = tk.Button(dialog, text="Pick Color", bg=color_var.get(), width=15)

        def pick_color():
            color = colorchooser.askcolor(title="Choose Category Color")[1]
            if color:
                color_var.set(color)
                btn_pick.configure(bg=color)

        btn_pick.configure(command=pick_color)
        btn_pick.pack(pady=8)

        def save():
            name = entry_cat_name.get().strip()
            if not name:
                messagebox.showerror("Error", "Category name cannot be empty.")
                return
            self.db.add_category(name, color_var.get())
            self.load_categories_from_db()
            self.update_category_combobox()
            self.combo_cat.set(name)
            dialog.destroy()

        ttk.Button(dialog, text="Save Category", command=save).pack(pady=6)

    def render_grid(self):
        if self.active_view.get() == "Day":
            self.render_day_view()
        else:
            self.render_week_view()

    def _render_time_slice(self, cell_frame: tk.Frame, start_min_in_hour: int, duration_in_this_hour: int,
                           bg_color: str, text: str, full_details: str, is_buffer: bool = False, on_click=None):
        """Places a proportionally sized sub-rectangle within the 60-minute hour slot."""
        rel_y = start_min_in_hour / 60.0
        rel_h = max(duration_in_this_hour / 60.0, 0.12)  # Maintain minimal visual click target

        sub_frame = tk.Frame(
            cell_frame, bg=bg_color, relief="solid" if not is_buffer else "flat",
            bd=1 if not is_buffer else 0, highlightbackground="#cbd5e1"
        )
        sub_frame.place(relx=0.02, rely=rel_y, relwidth=0.96, relheight=rel_h)

        lbl_text = text if duration_in_this_hour >= 20 else text[:12]
        lbl = tk.Label(
            sub_frame, text=lbl_text, bg=bg_color, fg="#1e293b" if not is_buffer else "#64748b",
            font=("Helvetica", 8, "bold" if not is_buffer else "italic"), anchor="w", padx=3
        )
        lbl.pack(fill="both", expand=True)

        # Attach Floating ToolTip for complete data
        ToolTip(sub_frame, lambda: full_details)
        ToolTip(lbl, lambda: full_details)

        if on_click:
            sub_frame.configure(cursor="pointinghand")
            lbl.configure(cursor="pointinghand")
            sub_frame.bind("<Button-1>", lambda e: on_click())
            lbl.bind("<Button-1>", lambda e: on_click())
    def _draw_current_time_indicator(self, parent_cell: tk.Frame, current_min: int):
        """Draws a crisp red line with a small circle indicating the exact current minute."""
        rel_y = current_min / 60.0
        
        indicator_frame = tk.Frame(parent_cell, bg="#ef4444", height=2)
        indicator_frame.place(relx=0.0, rely=rel_y, relwidth=1.0, height=2)

        # Dot on the edge for Google Calendar feel
        dot = tk.Label(parent_cell, text="●", fg="#ef4444", bg=parent_cell.cget("bg"), font=("Helvetica", 8))
        dot.place(relx=-0.02, rely=rel_y - 0.08)

    def _auto_refresh_time_indicator(self):
        """Periodically refreshes the grid every minute to keep the red line in sync."""
        now = datetime.now()
        # Only re-render if we are within visible business hours to avoid unnecessary redraws
        if self.start_hour <= now.hour <= self.end_hour:
            self.render_grid()
        self.root.after(60000, self._auto_refresh_time_indicator)

    def render_week_view(self):
        for widget in self.grid_container.winfo_children():
            widget.destroy()

        week_end = self.current_week_start + timedelta(days=6)
        self.lbl_current_range.configure(
            text=f"📅 {self.current_week_start.strftime('%b %d, %Y')} – {week_end.strftime('%b %d, %Y')}"
        )

        tk.Label(self.grid_container, text="Hour", width=8, font=("Helvetica", 10, "bold"),
                 bg="#2b6cb0", fg="white", relief="ridge", pady=6).grid(row=0, column=0, sticky="nsew")

        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for col_idx, name in enumerate(day_names, start=1):
            col_date = self.current_week_start + timedelta(days=col_idx - 1)
            tk.Label(self.grid_container, text=f"{name}\n{col_date.strftime('%d/%m')}", width=17,
                     font=("Helvetica", 9, "bold"), bg="#2b6cb0", fg="white", relief="ridge", pady=4).grid(row=0, column=col_idx, sticky="nsew")

        cell_slots = {}
        for r_idx, hour in enumerate(range(self.start_hour, self.end_hour + 1), start=1):
            tk.Label(self.grid_container, text=f"{hour:02d}:00", font=("Helvetica", 9, "bold"),
                     bg="#f7fafc", fg="#4a5568", relief="groove", height=3).grid(row=r_idx, column=0, sticky="nsew")

            for c_idx in range(1, 8):
                cell_frame = tk.Frame(self.grid_container, bg="#ffffff", relief="solid", bd=1,
                                      highlightbackground="#f1f5f9", highlightthickness=1, height=self.hour_height_px)
                cell_frame.grid(row=r_idx, column=c_idx, sticky="nsew")
                cell_frame.grid_propagate(False)
                cell_slots[(c_idx - 1, hour)] = cell_frame

        # 1. Routines
        _, routine_details = self.db.load_user_profile_with_colors()
        for r_info in routine_details:
            r = r_info["slot"]
            d = r.day_of_week
            color = r_info["color_hex"]

            event_start_min = r.start_clock.hour * 60 + r.start_clock.minute
            event_end_min = event_start_min + r.duration_minutes
            details = f"📌 {r.title}\nTime: {r.start_clock.strftime('%H:%M')} ({r.duration_minutes} min)\nCategory: {r.category}"

            for h in range(self.start_hour, self.end_hour + 1):
                slot_start = h * 60
                slot_end = (h + 1) * 60
                # Overlap in this specific hour
                ov_start = max(event_start_min, slot_start)
                ov_end = min(event_end_min, slot_end)
                if ov_start < ov_end:
                    start_in_h = ov_start - slot_start
                    dur_in_h = ov_end - ov_start
                    txt = f"📌 {r.title}" if ov_start == event_start_min else f"↓ {r.title}"
                    if (d, h) in cell_slots:
                        self._render_time_slice(cell_slots[(d, h)], start_in_h, dur_in_h, color, txt, details)

        # 2. Events with Multi-Hour Proportions, Buffers, and End-of-Month Recurring Logic
        day_tag_to_col = {"Sun": 0, "Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6}
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, category, event_date, end_date, start_clock,
                       duration_minutes, buffer_before_minutes, buffer_after_minutes,
                       recurrence_freq, recurrence_days, color_hex, reminder_min
                FROM events;
            """)
            for row in cursor.fetchall():
                ev_data = {
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "event_date": row[3],
                    "end_date": row[4] or row[3],
                    "start_clock": row[5],
                    "duration_minutes": row[6],
                    "buffer_before_minutes": row[7],
                    "buffer_after_minutes": row[8],
                    "recurrence_freq": row[9],
                    "recurrence_days": row[10],
                    "color_hex": row[11],
                    "reminder_min": row[12] if len(row) > 12 and row[12] is not None else 0
                }
                start_d = date.fromisoformat(ev_data["event_date"])
                end_d = date.fromisoformat(ev_data["end_date"])
                t_parts = [int(p) for p in ev_data["start_clock"].split(":")]
                ev_start_min = t_parts[0] * 60 + t_parts[1]
                ev_end_min = ev_start_min + ev_data["duration_minutes"]
                buf_before = ev_data["buffer_before_minutes"]
                buf_after = ev_data["buffer_after_minutes"]
                freq = ev_data["recurrence_freq"]

                details = (
                    f"🏷 {ev_data['title']}\n"
                    f"Time: {ev_data['start_clock'][:5]} ({ev_data['duration_minutes']} min)\n"
                    f"Buffer: {buf_before}m before, {buf_after}m after\n"
                    f"Category: {ev_data['category']}"
                )

                def draw_event_proportional(c_idx):
                    # Draw Buffer Before
                    if buf_before > 0:
                        b_start = ev_start_min - buf_before
                        b_end = ev_start_min
                        for h in range(self.start_hour, self.end_hour + 1):
                            s_h = h * 60
                            e_h = (h + 1) * 60
                            if max(b_start, s_h) < min(b_end, e_h):
                                self._render_time_slice(
                                    cell_slots[(c_idx, h)], max(b_start, s_h) - s_h,
                                    min(b_end, e_h) - max(b_start, s_h), "#f1f5f9",
                                    f"⏳ Buffer", f"Buffer before '{ev_data['title']}' ({buf_before}m)", is_buffer=True
                                )

                    # Draw Main Event Body
                    for h in range(self.start_hour, self.end_hour + 1):
                        s_h = h * 60
                        e_h = (h + 1) * 60
                        ov_s = max(ev_start_min, s_h)
                        ov_e = min(ev_end_min, e_h)
                        if ov_s < ov_e:
                            txt = f"🚩 {ev_data['title']}" if ov_s == ev_start_min else f"↓ {ev_data['title']}"
                            self._render_time_slice(
                                cell_slots[(c_idx, h)], ov_s - s_h, ov_e - ov_s,
                                ev_data["color_hex"], txt, details,
                                on_click=lambda d=ev_data: self.open_event_action_dialog(d)
                            )

                    # Draw Buffer After
                    if buf_after > 0:
                        b_start = ev_end_min
                        b_end = ev_end_min + buf_after
                        for h in range(self.start_hour, self.end_hour + 1):
                            s_h = h * 60
                            e_h = (h + 1) * 60
                            if max(b_start, s_h) < min(b_end, e_h):
                                self._render_time_slice(
                                    cell_slots[(c_idx, h)], max(b_start, s_h) - s_h,
                                    min(b_end, e_h) - max(b_start, s_h), "#f1f5f9",
                                    f"⏳ Buffer", f"Buffer after '{ev_data['title']}' ({buf_after}m)", is_buffer=True
                                )

                # Recurrence Matching
                if freq == "None" or not freq:
                    for c_idx in range(7):
                        day_dt = self.current_week_start + timedelta(days=c_idx)
                        if start_d <= day_dt <= end_d:
                            draw_event_proportional(c_idx)

                elif freq == "Weekly":
                    if ev_data["recurrence_days"]:
                        for d_tag in [d.strip() for d in ev_data["recurrence_days"].split(",") if d.strip()]:
                            if d_tag in day_tag_to_col:
                                draw_event_proportional(day_tag_to_col[d_tag])
                    else:
                        draw_event_proportional((start_d.weekday() + 1) % 7)

                elif freq == "Monthly":
                    for c_idx in range(7):
                        day_dt = self.current_week_start + timedelta(days=c_idx)
                        # Fix for 31st recurrence in 30-day/28-day months
                        last_day_of_month = calendar.monthrange(day_dt.year, day_dt.month)[1]
                        target_day = min(start_d.day, last_day_of_month)
                        if day_dt.day == target_day and day_dt >= start_d:
                            draw_event_proportional(c_idx)

                elif freq == "Yearly":
                    for c_idx in range(7):
                        day_dt = self.current_week_start + timedelta(days=c_idx)
                        if day_dt.month == start_d.month:
                            last_day = calendar.monthrange(day_dt.year, day_dt.month)[1]
                            target_day = min(start_d.day, last_day)
                            if day_dt.day == target_day and day_dt >= start_d:
                                draw_event_proportional(c_idx)
        # Draw Red Line Indicator for Current Time (Weekly View)
        now = datetime.now()
        today_date = now.date()

        # Check if the currently viewed week contains today
        if self.current_week_start <= today_date <= self.current_week_start + timedelta(days=6):
            if self.start_hour <= now.hour <= self.end_hour:
                today_col_idx = (today_date.weekday() + 1) % 7
                if (today_col_idx, now.hour) in cell_slots:
                    self._draw_current_time_indicator(cell_slots[(today_col_idx, now.hour)], now.minute)

    def render_day_view(self):
        for widget in self.grid_container.winfo_children():
            widget.destroy()

        day_name = self.current_date.strftime("%A")
        self.lbl_current_range.configure(text=f"📅 {day_name}, {self.current_date.strftime('%B %d, %Y')}")

        tk.Label(self.grid_container, text="Hour", width=12, font=("Helvetica", 10, "bold"),
                 bg="#2b6cb0", fg="white", relief="ridge", pady=6).grid(row=0, column=0, sticky="nsew")

        tk.Label(self.grid_container, text=f"{day_name} Timeline ({self.current_date.strftime('%d/%m/%Y')})",
                 width=70, font=("Helvetica", 10, "bold"), bg="#2b6cb0", fg="white", relief="ridge", pady=6).grid(row=0, column=1, sticky="nsew")

        cell_slots = {}
        for r_idx, hour in enumerate(range(self.start_hour, self.end_hour + 1), start=1):
            tk.Label(self.grid_container, text=f"{hour:02d}:00", font=("Helvetica", 10, "bold"),
                     bg="#f7fafc", fg="#4a5568", relief="groove", height=3).grid(row=r_idx, column=0, sticky="nsew")

            cell_frame = tk.Frame(self.grid_container, bg="#ffffff", relief="solid", bd=1,
                                  highlightbackground="#f1f5f9", highlightthickness=1, height=self.hour_height_px)
            cell_frame.grid(row=r_idx, column=1, sticky="nsew")
            cell_frame.grid_propagate(False)
            cell_slots[hour] = cell_frame

        target_weekday = (self.current_date.weekday() + 1) % 7
        _, routine_details = self.db.load_user_profile_with_colors()
        for r_info in routine_details:
            r = r_info["slot"]
            if r.day_of_week == target_weekday:
                event_start_min = r.start_clock.hour * 60 + r.start_clock.minute
                event_end_min = event_start_min + r.duration_minutes
                details = f"📌 {r.title}\nTime: {r.start_clock.strftime('%H:%M')} ({r.duration_minutes}m)"

                for h in range(self.start_hour, self.end_hour + 1):
                    s_h, e_h = h * 60, (h + 1) * 60
                    ov_s, ov_e = max(event_start_min, s_h), min(event_end_min, e_h)
                    if ov_s < ov_e:
                        txt = f"📌 {r.title}" if ov_s == event_start_min else f"↓ {r.title}"
                        self._render_time_slice(cell_slots[h], ov_s - s_h, ov_e - ov_s, r_info["color_hex"], txt, details)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, category, event_date, end_date, start_clock, duration_minutes,
                       buffer_before_minutes, buffer_after_minutes, recurrence_freq, recurrence_days,
                       color_hex, reminder_min
                FROM events;
            """)
            day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            today_tag = day_labels[target_weekday]

            for row in cursor.fetchall():
                ev_data = {
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "event_date": row[3],
                    "end_date": row[4] or row[3],
                    "start_clock": row[5],
                    "duration_minutes": row[6],
                    "buffer_before_minutes": row[7],
                    "buffer_after_minutes": row[8],
                    "recurrence_freq": row[9],
                    "recurrence_days": row[10],
                    "color_hex": row[11],
                    "reminder_min": row[12] if len(row) > 12 and row[12] is not None else 0
                }
                start_d = date.fromisoformat(ev_data["event_date"])
                end_d = date.fromisoformat(ev_data["end_date"])
                t_parts = [int(p) for p in ev_data["start_clock"].split(":")]
                ev_start_min = t_parts[0] * 60 + t_parts[1]
                ev_end_min = ev_start_min + ev_data["duration_minutes"]
                buf_before = ev_data["buffer_before_minutes"]
                buf_after = ev_data["buffer_after_minutes"]
                freq = ev_data["recurrence_freq"]

                should_render = False
                if (freq == "None" or not freq) and (start_d <= self.current_date <= end_d):
                    should_render = True
                elif freq == "Weekly" and ev_data["recurrence_days"] and today_tag in [d.strip() for d in ev_data["recurrence_days"].split(",")]:
                    should_render = True
                elif freq == "Monthly":
                    last_day = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
                    target_day = min(start_d.day, last_day)
                    if self.current_date.day == target_day and self.current_date >= start_d:
                        should_render = True
                elif freq == "Yearly":
                    if self.current_date.month == start_d.month:
                        last_day = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
                        target_day = min(start_d.day, last_day)
                        if self.current_date.day == target_day and self.current_date >= start_d:
                            should_render = True

                if should_render:
                    details = f"🏷 {ev_data['title']}\nTime: {ev_data['start_clock'][:5]} ({ev_data['duration_minutes']} min)\nBuffer: {buf_before}m before, {buf_after}m after"
                    
                    # Buffer Before
                    if buf_before > 0:
                        b_s, b_e = ev_start_min - buf_before, ev_start_min
                        for h in range(self.start_hour, self.end_hour + 1):
                            s_h, e_h = h * 60, (h + 1) * 60
                            if max(b_s, s_h) < min(b_e, e_h):
                                self._render_time_slice(cell_slots[h], max(b_s, s_h) - s_h, min(b_e, e_h) - max(b_s, s_h), "#f1f5f9", "⏳ Buffer", f"Buffer before ({buf_before}m)", is_buffer=True)

                    # Event Body
                    for h in range(self.start_hour, self.end_hour + 1):
                        s_h, e_h = h * 60, (h + 1) * 60
                        ov_s, ov_e = max(ev_start_min, s_h), min(ev_end_min, e_h)
                        if ov_s < ov_e:
                            txt = f"🚩 {ev_data['title']}" if ov_s == ev_start_min else f"↓ {ev_data['title']}"
                            self._render_time_slice(cell_slots[h], ov_s - s_h, ov_e - ov_s, ev_data["color_hex"], txt, details, on_click=lambda d=ev_data: self.open_event_action_dialog(d))

                    # Buffer After
                    if buf_after > 0:
                        b_s, b_e = ev_end_min, ev_end_min + buf_after
                        for h in range(self.start_hour, self.end_hour + 1):
                            s_h, e_h = h * 60, (h + 1) * 60
                            if max(b_s, s_h) < min(b_e, e_h):
                                self._render_time_slice(cell_slots[h], max(b_s, s_h) - s_h, min(b_e, e_h) - max(b_s, s_h), "#f1f5f9", "⏳ Buffer", f"Buffer after ({buf_after}m)", is_buffer=True)
        # Draw Red Line Indicator for Current Time (Day View)
        now = datetime.now()
        if self.current_date == now.date():
            if self.start_hour <= now.hour <= self.end_hour:
                if now.hour in cell_slots:
                    self._draw_current_time_indicator(cell_slots[now.hour], now.minute)

    def open_event_action_dialog(self, ev_data: dict):
        EventActionDialog(self, self.db, ev_data, on_update_callback=self.render_grid)

    def _find_conflicts(self, check_date: date, start_t: time, dur: int, buf: int, recurrence_days: List[str]) -> List[str]:
        """Strict conflict checking that accounts for the mandatory travel/prep buffer window."""
        conflicts = []
        event_start_min = start_t.hour * 60 + start_t.minute
        # The true locked window includes the buffer
        locked_start = event_start_min - buf
        locked_end = event_start_min + dur + buf

        day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        target_day_idx = (check_date.weekday() + 1) % 7

        # 1. Routines Check
        _, routine_details = self.db.load_user_profile_with_colors()
        for r_info in routine_details:
            r = r_info["slot"]
            applies = False
            if recurrence_days:
                if day_labels[r.day_of_week] in recurrence_days:
                    applies = True
            elif r.day_of_week == target_day_idx:
                applies = True

            if applies:
                r_start = r.start_clock.hour * 60 + r.start_clock.minute - r.buffer_before_minutes
                r_end = r.start_clock.hour * 60 + r.start_clock.minute + r.duration_minutes + r.buffer_after_minutes
                if max(locked_start, r_start) < min(locked_end, r_end):
                    conflicts.append(f"Core Habit: '{r.title}' (Includes buffer, {r.start_clock.strftime('%H:%M')})")

        # 2. Existing Events Check
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, event_date, end_date, start_clock, duration_minutes,
                       buffer_before_minutes, buffer_after_minutes, recurrence_freq, recurrence_days
                FROM events;
            """)
            for row in cursor.fetchall():
                ev_title, s_date_str, e_date_str, e_time_str, e_dur, b_before, b_after, freq, rec_days = row
                e_start_d = date.fromisoformat(s_date_str)
                e_end_d = date.fromisoformat(e_date_str) if e_date_str else e_start_d
                t_parts = [int(p) for p in e_time_str.split(":")]
                ev_s = t_parts[0] * 60 + t_parts[1] - b_before
                ev_e = t_parts[0] * 60 + t_parts[1] + e_dur + b_after

                overlap_day = False
                if freq == "None" or not freq:
                    if e_start_d <= check_date <= e_end_d:
                        overlap_day = True
                elif freq == "Weekly":
                    if rec_days:
                        if day_labels[target_day_idx] in [d.strip() for d in rec_days.split(",")]:
                            overlap_day = True
                    elif (e_start_d.weekday() + 1) % 7 == target_day_idx:
                        overlap_day = True
                elif freq == "Monthly":
                    last_day = calendar.monthrange(check_date.year, check_date.month)[1]
                    if check_date.day == min(e_start_d.day, last_day):
                        overlap_day = True

                if overlap_day and max(locked_start, ev_s) < min(locked_end, ev_e):
                    conflicts.append(f"Event: '{ev_title}' (Occupies {b_before}m buffer to {e_dur+b_after}m end)")

        return list(set(conflicts))

    def add_event(self):
        try:
            e_title = self.entry_title.get().strip()
            e_cat = self.combo_cat.get()
            start_d = date.fromisoformat(self.entry_date.get().strip())

            if self.is_multiday.get():
                end_d = date.fromisoformat(self.entry_end_date.get().strip())
                if end_d < start_d:
                    messagebox.showerror("Error", "End date cannot be earlier than start date.")
                    return
            else:
                end_d = start_d

            t_parts = [int(p) for p in self.entry_time.get().strip().split(":")]
            e_time = time(t_parts[0], t_parts[1])
            dur = int(self.entry_dur.get().strip())
            buf = int(self.entry_buf.get().strip())

            if not e_title:
                messagebox.showerror("Error", "Event title cannot be empty.")
                return

            # 1. getting reminder in minutes
            reminder_str = self.combo_reminder.get()
            reminder_mapping = {
                "None": 0,
                "15 min before": 15,
                "30 min before": 30,
                "1 hour before": 60
            }
            reminder_min = reminder_mapping.get(reminder_str, 0)

            # 2. חזרתיות
            freq = self.combo_freq.get() if self.is_recurring.get() else "None"
            selected_days = []
            if self.is_recurring.get() and freq == "Weekly":
                for day_label, (var, _) in self.days_vars.items():
                    if var.get():
                        selected_days.append(day_label)

            # 3. בדיקת חפיפות (כולל ה-buffer)
            conflicts = self._find_conflicts(start_d, e_time, dur, buf, selected_days)
            if conflicts:
                conflict_details = "\n • ".join(conflicts)
                msg = (
                    f"⚠️ Schedule / Buffer Conflict Detected!\n\n"
                    f"The required window for '{e_title}' (including {buf}m buffer) overlaps with:\n • {conflict_details}\n\n"
                    f"Do you want to overlap anyway?\n"
                    f"• Click 'Yes' to force schedule.\n"
                    f"• Click 'No' to pick an alternate open slot."
                )
                proceed = messagebox.askyesno("Schedule Conflict", msg, icon="warning")
                if not proceed:
                    self.entry_time.focus()
                    return

            start_dt = datetime.combine(start_d, e_time)
            total_start = start_dt - timedelta(minutes=buf)
            total_end = start_dt + timedelta(minutes=dur + buf)
            recurrence_days_str = ",".join(selected_days)
            color = self.category_colors.get(e_cat, "#d1e7dd")

            # 4. שמירה במסד הנתונים
            self.db.save_event_record(
                title=e_title,
                category=e_cat,
                event_date_str=start_d.isoformat(),
                end_date_str=end_d.isoformat(),
                start_clock_str=e_time.isoformat(),
                duration=dur,
                buf_before=buf,
                buf_after=buf,
                total_start_str=total_start.isoformat(),
                total_end_str=total_end.isoformat(),
                color_hex=color,
                recurrence_freq=freq,
                recurrence_days=recurrence_days_str,
                reminder_min=reminder_min
            )

            self.render_grid()
            messagebox.showinfo("Success", f"Event '{e_title}' scheduled with {buf}m buffer!")
            self.reset_event_form()

        except Exception as err:
            messagebox.showerror("Input Error", f"Invalid input parameters:\n{err}")

    def reset_event_form(self):
        """Resets all input fields, checkboxes, and selections back to clean defaults."""
        self.entry_title.delete(0, tk.END)

        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, str(self.current_date))

        self.is_multiday.set(False)
        self.entry_end_date.configure(state="disabled")
        self.entry_end_date.delete(0, tk.END)
        self.entry_end_date.insert(0, str(self.current_date + timedelta(days=2)))

        self.entry_time.delete(0, tk.END)
        self.entry_time.insert(0, "14:00")

        self.entry_dur.delete(0, tk.END)
        self.entry_dur.insert(0, "60")

        self.entry_buf.delete(0, tk.END)
        self.entry_buf.insert(0, "15")

        if self.combo_cat["values"]:
            self.combo_cat.current(0)

        self.is_recurring.set(False)
        self.combo_freq.configure(state="disabled")
        self.combo_freq.current(0)
        self.combo_reminder.current(0)

        for var, chk in self.days_vars.values():
            var.set(False)
            chk.configure(state="disabled")