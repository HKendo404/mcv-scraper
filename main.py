import math
import os
import pickle
from datetime import datetime as dt
from datetime import timedelta
from typing import NamedTuple

import colorama
import pandas as pd
import requests
from bs4 import BeautifulSoup
from colorama import Fore
from dotenv import load_dotenv

load_dotenv()

userid = os.getenv("ID")
password = os.getenv("PASSWD")


# https://stackoverflow.com/a/45426493
class Course(NamedTuple):
    name: str
    cid: str  # The ID used in course URLs
    course_num: str


# https://github.com/kcnti/mycourseville-crispy
def login_and_get_session(username: str, passwd: str) -> requests.Session:
    oauthURL = "https://www.mycourseville.com/api/oauth/authorize?response_type=code&client_id=mycourseville.com&redirect_uri=https://www.mycourseville.com&login_page=itchula"
    s = requests.Session()
    s.get(oauthURL)

    chulaLogin = "https://www.mycourseville.com/api/chulalogin"
    r = s.get(chulaLogin)
    soup = BeautifulSoup(r.content, "html.parser")
    token = soup.select_one("input[name=_token]")["value"]

    data = {
        "_token": token,
        "username": username,
        "password": passwd,
        "remember": "on",
    }

    req = s.post(chulaLogin, data=data)  # login session
    req.raise_for_status()
    return s


def get_course_data(s: requests.Session) -> dict:
    url = "https://www.mycourseville.com/?q=courseville/ajax/cvhomepanel_get_filter"

    r = s.get(url)
    r.raise_for_status()
    data = r.json().get("data")  # Array of dictionaries of course data

    real_data = {}

    for course_data in data:
        course_year = course_data.get("year")
        course_sem = course_data.get("semester")
        course_name = course_data.get("title")
        cv_cid = course_data.get("cv_cid")
        course_num = course_data.get("nid")

        if course_year not in real_data:
            real_data[course_year] = {}
        if course_sem not in real_data[course_year]:
            real_data[course_year][course_sem] = []

        real_data[course_year][course_sem].append(
            Course(course_name, cv_cid, course_num)
        )

    return real_data


def get_assignments_table_for_course(
    s: requests.Session, course: Course, cols: pd.Index
) -> pd.DataFrame:
    url = f"https://www.mycourseville.com/?q=courseville/course/{course.cid}/assignment"

    r = s.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    # Initial check cuz there might be no assignments
    assignment_table = soup.select_one("table#cv-assignment-table")
    if assignment_table is None:
        print(f"No assignments for {course.name}")
        return pd.DataFrame()

    tbody = soup.select_one("table#cv-assignment-table > tbody")

    # Try to loadmore all the assignments
    loadmore_panel = soup.find(id="courseville-assignment-list-loadmore-panel")
    if (
        loadmore_panel is not None
    ):  # The element won't be there if there are no more assignments to load
        print(f"Loading more assignments for {course.name}")
        data_total = int(loadmore_panel["data-total"])
        data_next = int(loadmore_panel["data-next"])
        # Ex. data_total = 24, data_next = 5 -> load 4 times = ceil((24-5)/5)

        for i in range(math.ceil((data_total - data_next) / 5)):
            next_param = 5 + 5 * i  # 0, 1, 2, 3 -> 5, 10, 15, 20
            table_rows: BeautifulSoup = load_more(s, course, next_param)
            tbody.append(table_rows)
    else:
        print(f"All assignments are here for {course.name}")

    df = pd.DataFrame(columns=cols)

    for row in soup.select(
        "table#cv-assignment-table > tbody > tr"
    ):  # There are other 'tr' in the table that aren't assignments Ex: if there is a score line in the Feedback column. Use '>' CSS selector to only get the direct child, the assignments
        columns = row.find_all("td")

        title = columns[1].a.text
        link = f"https://www.mycourseville.com/{columns[1].a.get('href')}"
        post_date_string = columns[2].div.text
        due_date_string = columns[3].div.text
        due_time_string: str = columns[3].select_one(".cv-fa-button")["data-content"]
        due_time_string = due_time_string.split()[-1]
        submitted = columns[5].div.text != "-"

        post_date = None
        if not (
            post_date_string.isspace() or post_date_string == ""
        ):  # Sometimes its empty idk lol
            full_post_string = " ".join(post_date_string.split())
            post_date = dt.strptime(full_post_string, "%b %d %Y")

        full_due_string = " ".join(due_date_string.split()) + " " + due_time_string
        due_date: dt = dt.strptime(full_due_string, "%b %d %Y %H:%M")

        # https://stackoverflow.com/a/67678982
        df = pd.concat(
            [
                pd.DataFrame(
                    [
                        [
                            course.course_num,
                            course.name,
                            title,
                            link,
                            post_date,
                            due_date,
                            submitted,
                        ]
                    ],
                    columns=df.columns,
                ),
                df,
            ],
        )

    return df


# This took so long to figure out :skull:
def load_more(
    s: requests.Session, course: Course, next_parameter: int
) -> BeautifulSoup:
    print(
        Fore.YELLOW,
        f"Sending loadmore request current assignments: {next_parameter}, for {course.name}...",
        Fore.RESET,
    )
    url = "https://www.mycourseville.com/?q=courseville/ajax/loadmoreassignmentrows"
    data = {"cv_cid": course.cid, "next": next_parameter}

    r = s.post(url, data=data)
    r.raise_for_status()

    table_rows = r.json()["data"]["html"]
    return BeautifulSoup(table_rows, "html.parser")


def check_if_data_exists(year: str, sem: str, real_data: dict) -> bool:
    if year not in real_data:
        print(Fore.RED, f"Year {year} not in data", Fore.RESET)
        print(real_data.keys())
        return False
    if sem not in real_data[year]:
        print(Fore.RED, f"Sem {sem} not in data", Fore.RESET)
        return False

    return True


def load_cookies(s: requests.Session) -> bool:
    try:
        with open("./.login_cookies", "rb") as f:
            s.cookies.update(pickle.load(f))
        return True
    except FileNotFoundError:
        return False


def save_cookies(s: requests.Session) -> None:
    with open("./.login_cookies", "wb") as f:
        pickle.dump(s.cookies, f)


def fresh_login(userid, password) -> requests.Session:
    s = login_and_get_session(userid, password)
    save_cookies(s)
    return s


def load_courses(s: requests.Session) -> dict:
    print(Fore.RED, "Loading Courses...", Fore.RESET)
    data = get_course_data(s)
    print(Fore.GREEN, "Done!", Fore.RESET)
    return data


def run_everything(year="2026", sem="1") -> bool:
    colorama.init()

    try:
        print(Fore.RED, "Logging In...", Fore.RESET, sep="")
        # Find saved cookies
        s = requests.Session()
        used_old_cookies = load_cookies(s)
        if used_old_cookies:
            print(
                Fore.YELLOW,
                "Found saved cookies",
                Fore.RESET,
            )
        else:
            print(
                Fore.YELLOW,
                "Can't find/use saved cookies, logging in and saving...",
                Fore.RESET,
            )
            s = fresh_login(userid, password)
        print(Fore.GREEN, "Done!", Fore.RESET)
    except requests.HTTPError:
        print(Fore.RED, "Login Failed", Fore.RESET)
        return False

    try:
        real_data = load_courses(s)
    except requests.HTTPError:
        print(Fore.RED, "Load Failed", Fore.RESET)
        return False

    df = pd.DataFrame(
        columns=[
            "Course Number",
            "Course Name",
            "Title",
            "Link",
            "Post Date",
            "Due Date",
            "Submitted",
        ]
    )

    try:
        if not check_if_data_exists(year, sem, real_data):
            if not used_old_cookies:
                return False
            # Sometimes old cookies are outdated or smth so retry login
            print(
                Fore.RED,
                "This might be an old cookie issue, retrying...",
                Fore.RESET,
            )
            try:
                s = fresh_login(userid, password)
                real_data = load_courses(s)
                if not check_if_data_exists(year, sem, real_data):
                    return False
            except requests.HTTPError:
                print(Fore.RED, "Load Failed", Fore.RESET)
                return False

        print(Fore.RED, f"Consolidating Assignments for {year}/{sem}...", Fore.RESET)

        num_courses = len(real_data[year][sem])
        for i in range(num_courses):
            course: Course = real_data[year][sem][i]

            this_df = get_assignments_table_for_course(s, course, cols=df.columns)
            df = pd.concat([this_df, df])

        print(Fore.GREEN, "Done!", Fore.RESET)

        df = df.set_index("Course Number")
        df = df.sort_values(by="Due Date")

        print(df)
        print(df.info())

        with open("./data.csv", "w", encoding="utf-8") as f:
            f.write(df.to_csv(encoding="utf-8"))

        return True

    except requests.HTTPError:
        print(Fore.RED, "Get data Failed", Fore.RESET)
        return False


def timedelta_to_day_hour(t: timedelta) -> str:
    days = t.days
    hours = t.seconds // 3600
    minutes = (t.seconds // 60) % 60

    parts = []
    if days > 0:
        parts.append(f"{days} Day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} Hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} Minute{'s' if minutes > 1 else ''}")

    return " ".join(parts)


def main():
    run_everything()


if __name__ == "__main__":
    main()
