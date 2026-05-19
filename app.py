import streamlit as st
import pandas as pd
import numpy as np
import random
import calendar
import sqlite3
import json
from datetime import date

st.set_page_config(page_title="GA 월간 근무 스케줄", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%); }
.main-title { font-size: 34px; font-weight: 800; color: #1e293b; }
.sub-title { font-size: 16px; color: #64748b; margin-bottom: 25px; }
.section-title { font-size: 22px; font-weight: 700; color: #334155; margin-top: 18px; margin-bottom: 10px; }
.store-badge { display: inline-block; background: #4f46e5; color: white; padding: 7px 14px; border-radius: 999px; font-weight: 700; }
div[data-testid="stMetric"] { background: white; padding: 18px; border-radius: 16px; box-shadow: 0 3px 10px rgba(15, 23, 42, 0.08); }
</style>
""", unsafe_allow_html=True)

shifts = ["오픈", "마감"]
weekdays = ["월", "화", "수", "목", "금", "토", "일"]


def init_db():
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            name TEXT,
            employee_type TEXT,
            monthly_off_count INTEGER,
            max_work INTEGER,
            available_days TEXT,
            available_shifts TEXT,
            day_off_requests TEXT
        )
    """)

    conn.commit()
    conn.close()


def register_store(store_name, password):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO stores (store_name, password) VALUES (?, ?)",
            (store_name, password)
        )
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def login_store(store_name, password):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()
    c.execute(
        "SELECT * FROM stores WHERE store_name=? AND password=?",
        (store_name, password)
    )
    result = c.fetchone()
    conn.close()
    return result is not None


def load_employees(store_name):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()
    c.execute("SELECT * FROM employees WHERE store_name=?", (store_name,))
    rows = c.fetchall()
    conn.close()

    employees = []

    for row in rows:
        employees.append({
            "id": row[0],
            "이름": row[2],
            "직원유형": row[3],
            "월휴무개수": None if row[4] == -1 else row[4],
            "월최대근무횟수": row[5],
            "출근가능요일": json.loads(row[6]),
            "가능근무": json.loads(row[7]),
            "휴무요청": [date.fromisoformat(d) for d in json.loads(row[8])]
        })

    return employees


def save_employee(store_name, emp):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO employees
        (store_name, name, employee_type, monthly_off_count, max_work,
         available_days, available_shifts, day_off_requests)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        store_name,
        emp["이름"],
        emp["직원유형"],
        emp["월휴무개수"] if emp["월휴무개수"] is not None else -1,
        emp["월최대근무횟수"],
        json.dumps(emp["출근가능요일"], ensure_ascii=False),
        json.dumps(emp["가능근무"], ensure_ascii=False),
        json.dumps([d.isoformat() for d in emp["휴무요청"]], ensure_ascii=False)
    ))

    conn.commit()
    conn.close()


def update_employee(emp_id, emp):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()

    c.execute("""
        UPDATE employees
        SET name=?, employee_type=?, monthly_off_count=?, max_work=?,
            available_days=?, available_shifts=?, day_off_requests=?
        WHERE id=?
    """, (
        emp["이름"],
        emp["직원유형"],
        emp["월휴무개수"] if emp["월휴무개수"] is not None else -1,
        emp["월최대근무횟수"],
        json.dumps(emp["출근가능요일"], ensure_ascii=False),
        json.dumps(emp["가능근무"], ensure_ascii=False),
        json.dumps([d.isoformat() for d in emp["휴무요청"]], ensure_ascii=False),
        emp_id
    ))

    conn.commit()
    conn.close()


def delete_employee(emp_id):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()


def clear_employees(store_name):
    conn = sqlite3.connect("schedule.db")
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE store_name=?", (store_name,))
    conn.commit()
    conn.close()


init_db()

if "login" not in st.session_state:
    st.session_state.login = False

if "store_name" not in st.session_state:
    st.session_state.store_name = None


if not st.session_state.login:
    st.markdown('<div class="main-title">GA 기반 월간 근무 스케줄 자동 생성 시스템</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">매장별 직원 정보를 저장하고 유전 알고리즘으로 월간 근무표를 생성합니다.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["매장 로그인", "매장 등록"])

    with tab1:
        store_name = st.text_input("매장명")
        password = st.text_input("비밀번호", type="password")

        if st.button("로그인", use_container_width=True):
            if login_store(store_name, password):
                st.session_state.login = True
                st.session_state.store_name = store_name
                st.session_state.employees = load_employees(store_name)
                st.rerun()
            else:
                st.error("매장명 또는 비밀번호가 틀렸습니다.")

    with tab2:
        new_store = st.text_input("새 매장명")
        new_pw = st.text_input("새 비밀번호", type="password")

        if st.button("매장 등록", use_container_width=True):
            if new_store and new_pw:
                if register_store(new_store, new_pw):
                    st.success("매장 등록이 완료되었습니다.")
                else:
                    st.error("이미 등록된 매장입니다.")
            else:
                st.warning("매장명과 비밀번호를 입력해주세요.")

    st.stop()


st.markdown('<div class="main-title">GA 기반 월간 근무 스케줄 자동 생성 시스템</div>', unsafe_allow_html=True)
st.markdown(f'<span class="store-badge">현재 매장: {st.session_state.store_name}</span>', unsafe_allow_html=True)

if st.button("로그아웃"):
    st.session_state.login = False
    st.session_state.store_name = None
    st.rerun()

if "employees" not in st.session_state:
    st.session_state.employees = load_employees(st.session_state.store_name)

st.markdown('<div class="section-title">1. 스케줄 생성 월 설정</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    year = st.number_input("년도", 2024, 2030, 2026)

with col2:
    month = st.number_input("월", 1, 12, 5)

last_day = calendar.monthrange(year, month)[1]
dates = [date(year, month, d) for d in range(1, last_day + 1)]


def get_weekday(work_date):
    return weekdays[work_date.weekday()]


def calendar_dayoff_selector(dates, year, month, key_prefix, default_selected=None):
    if default_selected is None:
        default_selected = []

    st.sidebar.markdown("### 휴무 요청일 선택")

    first_weekday, _ = calendar.monthrange(year, month)
    selected_days = []

    header_cols = st.sidebar.columns(7)
    for i, wd in enumerate(weekdays):
        header_cols[i].markdown(f"**{wd}**")

    week = [None] * first_weekday

    for d in dates:
        week.append(d)

        if len(week) == 7:
            cols = st.sidebar.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day is None:
                        st.write("")
                    else:
                        checked = st.checkbox(
                            str(day.day),
                            value=day in default_selected,
                            key=f"{key_prefix}_{day.isoformat()}"
                        )
                        if checked:
                            selected_days.append(day)
            week = []

    if week:
        while len(week) < 7:
            week.append(None)

        cols = st.sidebar.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day is None:
                    st.write("")
                else:
                    checked = st.checkbox(
                        str(day.day),
                        value=day in default_selected,
                        key=f"{key_prefix}_{day.isoformat()}"
                    )
                    if checked:
                        selected_days.append(day)

    return selected_days


st.sidebar.header("직원 등록 / 수정")

employees = st.session_state.employees
employee_options = ["신규 직원"] + [emp["이름"] for emp in employees]

selected_employee_name = st.sidebar.selectbox("직원 등록 내역 불러오기", employee_options)

selected_emp = None
if selected_employee_name != "신규 직원":
    selected_emp = next(emp for emp in employees if emp["이름"] == selected_employee_name)

default_name = "" if selected_emp is None else selected_emp["이름"]
default_type = "시급제" if selected_emp is None else selected_emp["직원유형"]
default_max_work = 22 if selected_emp is None else selected_emp["월최대근무횟수"]
default_days = weekdays if selected_emp is None else selected_emp["출근가능요일"]
default_shifts = shifts if selected_emp is None else selected_emp["가능근무"]
default_dayoff = [] if selected_emp is None else selected_emp["휴무요청"]
default_monthly_off = 8 if selected_emp is None or selected_emp["월휴무개수"] is None else selected_emp["월휴무개수"]

name = st.sidebar.text_input("직원 이름", value=default_name)

employee_type = st.sidebar.selectbox(
    "직원 유형",
    ["시급제", "월급제"],
    index=["시급제", "월급제"].index(default_type)
)

available_shifts = st.sidebar.multiselect(
    "가능 근무",
    shifts,
    default=default_shifts
)

if employee_type == "시급제":
    available_days = st.sidebar.multiselect(
        "출근 가능 요일",
        weekdays,
        default=default_days
    )
    monthly_off_count = None
else:
    available_days = weekdays
    monthly_off_count = st.sidebar.number_input(
        "월 휴무 개수",
        min_value=0,
        max_value=15,
        value=int(default_monthly_off)
    )

max_work = st.sidebar.slider(
    "월 최대 근무 횟수",
    1,
    31,
    int(default_max_work)
)

selected_day_off = calendar_dayoff_selector(
    dates,
    year,
    month,
    key_prefix=f"dayoff_{selected_employee_name}_{name}",
    default_selected=default_dayoff
)

new_emp = {
    "이름": name,
    "직원유형": employee_type,
    "월휴무개수": monthly_off_count,
    "월최대근무횟수": max_work,
    "출근가능요일": available_days,
    "가능근무": available_shifts,
    "휴무요청": selected_day_off
}

if st.sidebar.button("직원 추가", use_container_width=True):
    if name:
        save_employee(st.session_state.store_name, new_emp)
        st.session_state.employees = load_employees(st.session_state.store_name)
        st.rerun()
    else:
        st.sidebar.warning("직원 이름을 입력해주세요.")

if st.sidebar.button("직원 정보 수정", use_container_width=True):
    if selected_emp is not None:
        update_employee(selected_emp["id"], new_emp)
        st.session_state.employees = load_employees(st.session_state.store_name)
        st.rerun()
    else:
        st.sidebar.warning("수정할 직원을 선택해주세요.")

if st.sidebar.button("직원 삭제", use_container_width=True):
    if selected_emp is not None:
        delete_employee(selected_emp["id"])
        st.session_state.employees = load_employees(st.session_state.store_name)
        st.rerun()
    else:
        st.sidebar.warning("삭제할 직원을 선택해주세요.")


st.markdown('<div class="section-title">2. 등록된 직원</div>', unsafe_allow_html=True)

employees = st.session_state.employees

if len(employees) == 0:
    st.warning("왼쪽 사이드바에서 직원을 먼저 등록해주세요.")
    st.stop()

emp_df = pd.DataFrame(employees)
emp_df_show = emp_df.copy()

emp_df_show["출근가능요일"] = emp_df_show["출근가능요일"].apply(lambda x: ", ".join(x))
emp_df_show["가능근무"] = emp_df_show["가능근무"].apply(lambda x: ", ".join(x))
emp_df_show["휴무요청"] = emp_df_show["휴무요청"].apply(
    lambda x: ", ".join([d.strftime("%m/%d") for d in x])
)
emp_df_show = emp_df_show.drop(columns=["id"])

st.dataframe(emp_df_show, use_container_width=True)

if st.button("현재 매장 직원 전체 초기화"):
    clear_employees(st.session_state.store_name)
    st.session_state.employees = []
    st.rerun()


st.markdown('<div class="section-title">3. 필요 인원 설정</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    open_required = st.number_input("오픈 필요 인원", 1, 20, 2)

with col2:
    close_required = st.number_input("마감 필요 인원", 1, 20, 2)

with col3:
    generations = st.slider("GA 반복 세대 수", 30, 300, 120)

required_staff = {
    "오픈": open_required,
    "마감": close_required
}

employee_names = [e["이름"] for e in employees]


def is_available(emp, work_date, shift):
    weekday = get_weekday(work_date)

    if work_date in emp["휴무요청"]:
        return False

    if shift not in emp["가능근무"]:
        return False

    if emp["직원유형"] == "시급제":
        if weekday not in emp["출근가능요일"]:
            return False

    return True


def create_empty_schedule():
    schedule = {}

    for d in dates:
        schedule[d] = {}
        for shift in shifts:
            schedule[d][shift] = []

    return schedule


def get_work_days(schedule, name):
    work_days = []

    for d in dates:
        worked = False

        for shift in shifts:
            if name in schedule[d][shift]:
                worked = True

        if worked:
            work_days.append(d)

    return work_days


def get_work_count(schedule, name):
    return len(get_work_days(schedule, name))


def get_target_work_count(emp):
    if emp["직원유형"] == "월급제":
        return last_day - emp["월휴무개수"]
    return emp["월최대근무횟수"]


def is_already_working_today(schedule, work_date, name):
    for shift in shifts:
        if name in schedule[work_date][shift]:
            return True
    return False


def can_assign(schedule, emp, work_date, shift):
    name = emp["이름"]

    if not is_available(emp, work_date, shift):
        return False

    if is_already_working_today(schedule, work_date, name):
        return False

    if get_work_count(schedule, name) >= get_target_work_count(emp):
        return False

    return True


def max_consecutive_work_days(work_days):
    if not work_days:
        return 0

    work_set = set(work_days)
    max_count = 0
    current_count = 0

    for d in dates:
        if d in work_set:
            current_count += 1
            max_count = max(max_count, current_count)
        else:
            current_count = 0

    return max_count


def create_individual():
    schedule = create_empty_schedule()

    slots = [(d, shift) for d in dates for shift in shifts]
    random.shuffle(slots)

    for d, shift in slots:
        required = required_staff[shift]

        candidates = [
            emp for emp in employees
            if can_assign(schedule, emp, d, shift)
        ]

        random.shuffle(candidates)
        selected = candidates[:required]
        schedule[d][shift] = [emp["이름"] for emp in selected]

    return schedule


def repair_schedule(schedule):
    # 불가능한 배정 제거
    for d in dates:
        for shift in shifts:
            cleaned = []

            for name in schedule[d][shift]:
                emp = next(e for e in employees if e["이름"] == name)

                if is_available(emp, d, shift):
                    cleaned.append(name)

            schedule[d][shift] = cleaned[:required_staff[shift]]

    # 부족한 인원 채우기
    slots = [(d, shift) for d in dates for shift in shifts]
    random.shuffle(slots)

    for d, shift in slots:
        required = required_staff[shift]

        while len(schedule[d][shift]) < required:
            candidates = [
                emp for emp in employees
                if can_assign(schedule, emp, d, shift)
            ]

            if not candidates:
                break

            random.shuffle(candidates)
            schedule[d][shift].append(candidates[0]["이름"])

    return schedule


def fitness(schedule):
    score = 0
    work_count = {name: 0 for name in employee_names}

    for d in dates:
        for shift in shifts:
            assigned = schedule[d][shift]
            required = required_staff[shift]

            shortage = max(0, required - len(assigned))
            excess = max(0, len(assigned) - required)

            score -= shortage * 10000
            score -= excess * 500

            for name in assigned:
                emp = next(e for e in employees if e["이름"] == name)

                if not is_available(emp, d, shift):
                    score -= 100000

                work_count[name] += 1

    for emp in employees:
        name = emp["이름"]
        target = get_target_work_count(emp)
        actual = get_work_count(schedule, name)

        if emp["직원유형"] == "월급제":
            score -= abs(target - actual) * 10000
        else:
            if actual > target:
                score -= (actual - target) * 10000

    for i in range(len(dates) - 1):
        today = dates[i]
        tomorrow = dates[i + 1]

        for name in employee_names:
            if name in schedule[today]["마감"] and name in schedule[tomorrow]["오픈"]:
                score -= 1000

    for name in employee_names:
        work_days = get_work_days(schedule, name)
        max_consecutive = max_consecutive_work_days(work_days)

        if max_consecutive > 5:
            score -= (max_consecutive - 5) * 5000

    score -= np.std(list(work_count.values())) * 10

    return score


def crossover(parent1, parent2):
    child = create_empty_schedule()

    for d in dates:
        for shift in shifts:
            if random.random() < 0.5:
                child[d][shift] = parent1[d][shift][:]
            else:
                child[d][shift] = parent2[d][shift][:]

    return repair_schedule(child)


def mutate(schedule, mutation_rate=0.05):
    for d in dates:
        for shift in shifts:
            if random.random() < mutation_rate:
                schedule[d][shift] = []

                required = required_staff[shift]
                candidates = [
                    emp for emp in employees
                    if can_assign(schedule, emp, d, shift)
                ]

                random.shuffle(candidates)
                selected = candidates[:required]
                schedule[d][shift] = [emp["이름"] for emp in selected]

    return repair_schedule(schedule)


def run_ga():
    population_size = 30
    population = [repair_schedule(create_individual()) for _ in range(population_size)]

    best_schedule = None
    best_score = -999999999999

    for _ in range(generations):
        population = sorted(population, key=fitness, reverse=True)

        current_score = fitness(population[0])

        if current_score > best_score:
            best_score = current_score
            best_schedule = population[0]

        next_generation = population[:8]

        while len(next_generation) < population_size:
            parent1, parent2 = random.sample(population[:15], 2)
            child = crossover(parent1, parent2)
            child = mutate(child)
            next_generation.append(child)

        population = next_generation

    return best_schedule, best_score


def make_calendar_df(schedule):
    first_weekday, _ = calendar.monthrange(year, month)

    calendar_rows = []
    week = [""] * 7
    day_index = first_weekday

    for d in dates:
        open_workers = ", ".join(schedule[d]["오픈"]) if schedule[d]["오픈"] else "-"
        close_workers = ", ".join(schedule[d]["마감"]) if schedule[d]["마감"] else "-"

        cell = f"{d.day}일\n오픈: {open_workers}\n마감: {close_workers}"

        week[day_index] = cell
        day_index += 1

        if day_index == 7:
            calendar_rows.append(week)
            week = [""] * 7
            day_index = 0

    if any(cell != "" for cell in week):
        calendar_rows.append(week)

    return pd.DataFrame(calendar_rows, columns=weekdays)


if st.button("GA로 월간 스케줄 생성", type="primary", use_container_width=True):
    with st.spinner("유전 알고리즘으로 최적 스케줄을 탐색 중입니다..."):
        best_schedule, best_score = run_ga()

    st.markdown('<div class="section-title">4. 월간 캘린더 스케줄</div>', unsafe_allow_html=True)
    st.info(f"적합도 점수: {round(best_score, 2)}")

    calendar_df = make_calendar_df(best_schedule)
    st.dataframe(calendar_df, use_container_width=True, height=500)

    st.markdown('<div class="section-title">5. 상세 스케줄표</div>', unsafe_allow_html=True)

    rows = []

    for d in dates:
        rows.append({
            "날짜": d.strftime("%m/%d"),
            "요일": get_weekday(d),
            "오픈": ", ".join(best_schedule[d]["오픈"]) if best_schedule[d]["오픈"] else "없음",
            "마감": ", ".join(best_schedule[d]["마감"]) if best_schedule[d]["마감"] else "없음",
            "오픈 부족": max(0, open_required - len(best_schedule[d]["오픈"])),
            "마감 부족": max(0, close_required - len(best_schedule[d]["마감"]))
        })

    result_df = pd.DataFrame(rows)
    st.dataframe(result_df, use_container_width=True)

    st.markdown('<div class="section-title">6. 직원별 근무 분석</div>', unsafe_allow_html=True)

    analysis_rows = []

    for emp in employees:
        name = emp["이름"]
        work_days = get_work_days(best_schedule, name)
        max_consecutive = max_consecutive_work_days(work_days)

        open_count = 0
        close_count = 0
        close_to_open_count = 0

        for i, d in enumerate(dates):
            if name in best_schedule[d]["오픈"]:
                open_count += 1

            if name in best_schedule[d]["마감"]:
                close_count += 1

            if i < len(dates) - 1:
                if name in best_schedule[d]["마감"] and name in best_schedule[dates[i + 1]]["오픈"]:
                    close_to_open_count += 1

        work_count = len(work_days)
        off_count = last_day - work_count

        target_work = get_target_work_count(emp)
        target_off = last_day - target_work

        analysis_rows.append({
            "직원": name,
            "유형": emp["직원유형"],
            "목표근무일수": target_work,
            "실제근무일수": work_count,
            "목표휴무일수": target_off,
            "실제휴무일수": off_count,
            "오픈횟수": open_count,
            "마감횟수": close_count,
            "최대연속근무": max_consecutive,
            "마감→다음날오픈": close_to_open_count
        })

    analysis_df = pd.DataFrame(analysis_rows)
    st.dataframe(analysis_df, use_container_width=True)

    total_shortage = int(result_df["오픈 부족"].sum() + result_df["마감 부족"].sum())
    total_close_to_open = int(analysis_df["마감→다음날오픈"].sum())
    over_5_count = int((analysis_df["최대연속근무"] > 5).sum())

    col1, col2, col3 = st.columns(3)
    col1.metric("총 부족 인원", total_shortage)
    col2.metric("마감→다음날 오픈", total_close_to_open)
    col3.metric("5일 초과 연속근무 직원 수", over_5_count)

    st.success("월간 스케줄 생성이 완료되었습니다.")
