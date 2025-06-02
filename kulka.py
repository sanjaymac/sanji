import streamlit as st
import datetime
import calendar
import pandas as pd

# ——————————————————————————————————————————————————————————————————————————
# 14‐day rotation thresholds (as given)
# ——————————————————————————————————————————————————————————————————————————
raw_custom = {
    "Sundar":    {"threshold": datetime.date(2025, 5, 28), "start_shift": "Night"},
    "Samyugtha": {"threshold": datetime.date(2025, 5, 28), "start_shift": "Day"},
    "Jalapathy": {"threshold": datetime.date(2025, 5, 31), "start_shift": "Day"},
}

employees = [
    {"name": "Periyasamy", "shift_type": "Day Shift Only", "week_offs": ["Tuesday", "Wednesday"]},
    {"name": "Sundar",      "shift_type": "Day/Night Shift", "week_offs": ["Monday", "Tuesday"]},
    {"name": "Jalapathy",   "shift_type": "Day/Night Shift", "week_offs": ["Thursday", "Friday"]},
    {"name": "Samyugtha",   "shift_type": "Day/Night Shift", "week_offs": ["Monday", "Tuesday"]},
    {"name": "Durgeshini",  "shift_type": "Day Shift Only",   "week_offs": ["Friday"]},
]

day_map = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2,
    "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
}

def get_shift(threshold: datetime.date, start_shift: str, date: datetime.date) -> str:
    """
    Compute 14-day rotation correctly, using floor division on a signed delta:
      • delta_days = (date - threshold).days
      • period     = delta_days // 14   (Python's // is floor‐division for ints)
      • If period % 2 == 0 → same as start_shift
        else             → the opposite ("Day" ↔ "Night")
    """
    delta_days = (date - threshold).days
    period = delta_days // 14      # floor division: e.g. -17//14 = -2, -14//14 = -1, 15//14 = 1, etc.
    if (period % 2) == 0:
        return start_shift
    else:
        return "Night" if start_shift == "Day" else "Day"


def count_shifts(emp: dict, year: int, month: int) -> tuple[int, int]:
    """
    Count Day vs. Night “units” (including off-days) for the given employee/month.
    - Every date in the month is assigned to either Day or Night based on:
        (a) If it’s a working day:
              • Day Shift Only → Day-count += 1
              • Day/Night      → get_shift(date) → increment that bucket
        (b) If it’s an off-day:
              • Look backwards (same month) for the last non-off date.
              • Take that date’s shift (Day or Night).  If no prior working day in the same month, default to Day.
    """
    name = emp["name"]
    shift_type = emp["shift_type"]
    week_off_days = {day_map[d] for d in emp["week_offs"]}
    days_in_month = calendar.monthrange(year, month)[1]
    morning = 0
    night = 0

    def _last_working_day(prev_date: datetime.date) -> datetime.date | None:
        candidate = prev_date - datetime.timedelta(days=1)
        while candidate.month == prev_date.month:
            if candidate.weekday() not in week_off_days:
                return candidate
            candidate -= datetime.timedelta(days=1)
        return None

    for d in range(1, days_in_month + 1):
        date = datetime.date(year, month, d)
        wd = date.weekday()

        # (1) If it’s an off-day:
        if wd in week_off_days:
            prev_work = _last_working_day(date)
            if prev_work is None:
                # No prior working day in this month → default to “Day”
                morning += 1
            else:
                if shift_type == "Day Shift Only":
                    morning += 1
                else:
                    prior = get_shift(
                        raw_custom[name]["threshold"],
                        raw_custom[name]["start_shift"],
                        prev_work
                    )
                    if prior == "Day":
                        morning += 1
                    else:
                        night += 1

        # (2) Otherwise it’s a working day:
        else:
            if shift_type == "Day Shift Only":
                morning += 1
            else:
                today_shift = get_shift(
                    raw_custom[name]["threshold"],
                    raw_custom[name]["start_shift"],
                    date
                )
                if today_shift == "Day":
                    morning += 1
                else:
                    night += 1

    return morning, night


def get_employee_calendar(emp: dict, year: int, month: int) -> pd.DataFrame:
    """
    Build a DataFrame with columns [Date, Weekday, ShiftLabel]:
      – If it’s a working day:
          • “Day” or “Night” per get_shift(...), or always “Day” for Day-Only.
      – If it’s an off-day:
          • “Off – (Day)” or “Off – (Night)”, where the parenthesis is the shift
             of the last non-off date in the same month. If none prior in month, default “Day.”
    """
    name = emp["name"]
    shift_type = emp["shift_type"]
    week_off_days = {day_map[d] for d in emp["week_offs"]}
    days_in_month = calendar.monthrange(year, month)[1]
    rows = []

    def _last_working_day(prev_date: datetime.date) -> datetime.date | None:
        candidate = prev_date - datetime.timedelta(days=1)
        while candidate.month == prev_date.month:
            if candidate.weekday() not in week_off_days:
                return candidate
            candidate -= datetime.timedelta(days=1)
        return None

    for d in range(1, days_in_month + 1):
        date = datetime.date(year, month, d)
        wd = date.weekday()
        wd_name = calendar.day_name[wd]

        if wd in week_off_days:
            # Off-day: tag to prior shift
            prev_work = _last_working_day(date)
            if prev_work is None:
                label = "Off – (Day)"
            else:
                if shift_type == "Day Shift Only":
                    label = "Off – (Day)"
                else:
                    prior = get_shift(
                        raw_custom[name]["threshold"],
                        raw_custom[name]["start_shift"],
                        prev_work
                    )
                    label = f"Off – ({prior})"
            rows.append({"Date": date.strftime("%Y-%m-%d"), "Weekday": wd_name, "Shift": label})

        else:
            # Working day
            if shift_type == "Day Shift Only":
                rows.append({"Date": date.strftime("%Y-%m-%d"), "Weekday": wd_name, "Shift": "Day"})
            else:
                shift_label = get_shift(
                    raw_custom[name]["threshold"],
                    raw_custom[name]["start_shift"],
                    date
                )
                rows.append({"Date": date.strftime("%Y-%m-%d"), "Weekday": wd_name, "Shift": shift_label})

    return pd.DataFrame(rows)


# ——————————————————————————————————————————————————————————————————————————
#  Streamlit App UI
# ——————————————————————————————————————————————————————————————————————————

st.title("Employee Shift Counter (14-Day Rotation, Offs Under Prior Shift)")

# Month selector (default to May 2025)
month_options = [(datetime.date(2025, m, 1).strftime("%B"), m) for m in range(1, 13)]
month_name, selected_month = st.selectbox("Select Month", month_options, index=4)
year = 2025

# Build summary table
summary_rows = []
for emp in employees:
    morning, night = count_shifts(emp, year, selected_month)
    summary_rows.append([
        emp["name"],
        emp["shift_type"],
        f"{month_name} {year}",
        morning,
        night,
        morning + night
    ])

df_summary = pd.DataFrame(
    summary_rows,
    columns=["Name", "Shift Type", "Month", "Morning Shift", "Night Shift", "Total (Incl. Offs)"]
)
st.dataframe(df_summary, use_container_width=True)

st.header("Select an Employee to View Detailed Calendar")
employee_names = [emp["name"] for emp in employees]
chosen_name = st.selectbox("Employee", [""] + employee_names)

if chosen_name:
    emp = next(filter(lambda e: e["name"] == chosen_name, employees))
    st.subheader(f"Shift Calendar – {chosen_name}")
    cal_df = get_employee_calendar(emp, year, selected_month)
    st.dataframe(cal_df, use_container_width=True)
