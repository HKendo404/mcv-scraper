from datetime import datetime as dt
from datetime import timedelta

import humanize
import pandas as pd
import streamlit as st

import main
import json

import os

GREEN = "#052001"
BLACK = "#000000"
RED = "#200404"

st.set_page_config(layout="wide")


# Gemini
def round_timedelta_for_humanize(t: timedelta) -> timedelta:
    total_sec = t.total_seconds()

    # Only round to days if the duration is 24 hours or longer
    if abs(total_sec) >= 86400:
        rounded_days = round(abs(total_sec) / 86400)
        sign = 1 if total_sec >= 0 else -1
        return timedelta(days=sign * rounded_days)

    return t


def timedelta_to_day_hour(t: timedelta) -> str:
    return humanize.naturaltime(-1 * round_timedelta_for_humanize(t))


def save_metadata(year: str, sem: str):
    with open("./metadata.json", "w") as f:
        json.dump({"year": year, "sem": sem}, f)


def load_metadata() -> tuple:
    try:
        with open("./metadata.json", "r") as f:
            thing = json.load(f)
            return (thing["year"], thing["sem"])
    except FileNotFoundError:
        return ("2026", "1")


def reload_data(year: str, sem: str):
    result = main.run_everything(year, sem)
    if result:
        save_metadata(year, sem)
        st.success("Successssss :>")
        if "slider_range" in st.session_state:
            del st.session_state["slider_range"]
    else:
        print("Failed")
        st.error("It didnt work :<")


data_df = None
if os.path.isfile("./data.csv"):
    data_df = pd.read_csv("./data.csv", encoding="utf-8")
else:
    curr_year, curr_sem = load_metadata()
    reload_data(curr_year, curr_sem)
    st.rerun()

now = pd.Timestamp.now()
data_df["Due"] = pd.to_datetime(data_df["Due Date"])
data_df["Timedelta"] = data_df["Due"] - now
data_df["DayOffset"] = (data_df["Due"].dt.normalize() - now.normalize()).dt.days

min_day = int(data_df["DayOffset"].min())
max_day = int(data_df["DayOffset"].max())

st.header("I love MCV <3", text_alignment="center")


with st.container(horizontal=True, width="content"):
    curr_year, curr_sem = load_metadata()
    year = st.selectbox(
        "Year",
        options=[str(i) for i in range(2009, 2030 + 1)],
        index=int(curr_year) - 2009,
    )
    sem = st.segmented_control(
        "Semester",
        options=["1", "2", "3"],
        default=curr_sem,
    )
    st.button("Reload Assignments", on_click=reload_data, args=(year, sem))


def format_day(x: int) -> str:
    if x < 0:
        return f"{-x} Days ago" if x != -1 else f"{-x} Day ago"
    elif x == 0:
        return "Today"
    else:
        return f"in {x} Days" if x != 1 else f"in {x} Day"


def set_preset(past: int, future: int):
    past_clamped = max(min_day, min(past, max_day))
    future_clamped = max(min_day, min(future, max_day))
    st.session_state["slider_range"] = (past_clamped, future_clamped)


# smth to fix warning since buttons change the slider
if "slider_range" not in st.session_state:
    set_preset(-7, max_day)


(past_days, future_days) = st.select_slider(
    label="Select range",
    options=list(
        range(
            min_day,
            max_day + 1,
        )
    ),
    value=st.session_state["slider_range"],  # smth to fix that warning too
    format_func=format_day,
)


with st.container(horizontal_alignment="right", horizontal=True):
    st.button(
        label="Everything Preset",
        on_click=set_preset,
        args=(min_day, max_day),
    )
    st.button(
        label="Today Preset",
        on_click=set_preset,
        args=(0, 0),
    )
    st.button(
        label="Good student Preset",
        on_click=set_preset,
        args=(0, max_day),
    )
    st.button(label="Bad student Preset", on_click=set_preset, args=(-7, max_day))


vis_df = data_df[data_df["DayOffset"].between(past_days, future_days)].sort_values(
    by="Due Date"
)
vis_df["Time from Current"] = vis_df["Timedelta"].map(timedelta_to_day_hour)

# Move to front
col = vis_df.pop("Time from Current")
vis_df.insert(0, col.name, col)

styled = vis_df.style.apply(
    lambda row: (
        [
            f"background-color: {GREEN}"
            if row["Submitted"]
            else (
                f"background-color: {BLACK}"
                if row["Due"] >= dt.now()
                else f"background-color: {RED}"
            )
        ]
        * len(row)
    ),
    axis=1,
)


def legend(label: str, color: str):
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <div style="
                width: 24px; 
                height: 24px; 
                background-color: {color}; 
                border: 2px solid white; 
                flex-shrink: 0;
            "></div>
            <span style="font-size: 15px;">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.container(horizontal=True, horizontal_alignment="center"):
    st.dataframe(
        styled,
        width="content",
        height="content",
        column_order=(
            "Submitted",
            "Time from Current",
            "Due Date",
            "Course Name",
            "Title",
            "Link",
        ),
        column_config={
            "Time from Current": st.column_config.TextColumn(),
            "Due Date": st.column_config.DatetimeColumn(
                format="DD MMM YYYY - hh:mm A",
                # format="distance",
            ),
            "Title": st.column_config.TextColumn(alignment="center"),
            "Link": st.column_config.LinkColumn(display_text="Open link"),
        },
    )

    with st.container(width="content"):
        legend("Submitted", GREEN)
        legend("Due soon", BLACK)
        legend("LATE", RED)


# Removing this sends a virus to MCV btw
with st.container(horizontal=True, horizontal_alignment="center"):
    st.image(
        "https://media1.tenor.com/m/_8JN7UV-FXMAAAAC/onimai-mahiro.gif",
        width=200,
    )
