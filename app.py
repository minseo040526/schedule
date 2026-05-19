import streamlit as st
import pandas as pd
import numpy as np
import random
import calendar
import sqlite3
import json
import time
from datetime import date

st.set_page_config(page_title="GA 월간 근무 스케줄", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%); }
.main-title { font-size: 34px; font-weight: 800; color: #1e293b; }
.sub-title { font-size: 16px; color: #64748b; margin-bottom: 25px; }
.section-title { font-size: 22px; font-weight: 700; color: #334155; margin-top: 18px; margin-bottom: 10px; }
.store-badge { display: inline-block; background: #4f46e5; color: white; padding: 7px 14px; border-radius: 999px; font-weight: 700; }
div[data-testid="stMetric"] { background: white; padding: 18px; border-radius: 16px; box-shadow: 0 3px 10px rgba(15,23,42,0.08); }
</style>
""", unsafe_allow_html=True)

SHIFTS = ["오픈", "마감"]
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

# ─────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────

def get_conn():
    return sqlite3.connect("schedule.db")

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_name TEXT UNIQUE,
                password TEXT
            )
        """)
        conn.execute("""
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

def register_store(store_name, password):
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO stores (store_name, password) VALUES (?,?)", (store_name, password))
        return True
    except Exception:
        return False

def login_store(store_name, password):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM stores WHERE store_name=? AND password=?", (store_name, password)
        ).fetchone()
    return row is not None

def _row_to_emp(row):
    return {
        "id": row[0],
        "이름": row[2],
        "직원유형": row[3],
        "월휴무개수": None if row[4] == -1 else row[4],
        "월최대근무횟수": row[5],
        "출근가능요일": json.loads(row[6]),
        "가능근무": json.loads(row[7]),
        "휴무요청": [date.fromisoformat(d) for d in json.loads(row[8])],
    }

def load_employees(store_name):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM employees WHERE store_name=?", (store_name,)).fetchall()
    return [_row_to_emp(r) for r in rows]

def _emp_params(store_name, emp):
    return (
        store_name,
        emp["이름"], emp["직원유형"],
        -1 if emp["월휴무개수"] is None else emp["월휴무개수"],
        emp["월최대근무횟수"],
        json.dumps(emp["출근가능요일"], ensure_ascii=False),
        json.dumps(emp["가능근무"], ensure_ascii=False),
        json.dumps([d.isoformat() for d in emp["휴무요청"]], ensure_ascii=False),
    )

def save_employee(store_name, emp):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO employees (store_name,name,employee_type,monthly_off_count,max_work,"
            "available_days,available_shifts,day_off_requests) VALUES (?,?,?,?,?,?,?,?)",
            _emp_params(store_name, emp)[0:],
        )

def update_employee(emp_id, emp):
    with get_conn() as conn:
        conn.execute(
            "UPDATE employees SET name=?,employee_type=?,monthly_off_count=?,max_work=?,"
            "available_days=?,available_shifts=?,day_off_requests=? WHERE id=?",
            _emp_params("", emp)[1:] + (emp_id,),
        )

def delete_employee(emp_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))

def clear_employees(store_name):
    with get_conn() as conn:
        conn.execute("DELETE FROM employees WHERE store_name=?", (store_name,))

# ─────────────────────────────────────────────
# 로그인
# ─────────────────────────────────────────────

init_db()

if "login" not in st.session_state:
    st.session_state.login = False
if "store_name" not in st.session_state:
    st.session_state.store_name = None

if not st.session_state.login:
    st.markdown('<div class="main-title">GA 기반 월간 근무 스케줄 자동 생성 시스템</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">매장별 직원 정보를 저장하고 유전 알고리즘으로 월간 근무표를 생성합니다.</div>', unsafe_allow_html=True)

    tab_login, tab_reg = st.tabs(["매장 로그인", "매장 등록"])

    with tab_login:
        sn = st.text_input("매장명")
        pw = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True):
            if login_store(sn, pw):
                st.session_state.login = True
                st.session_state.store_name = sn
                st.session_state.employees = load_employees(sn)
                st.rerun()
            else:
                st.error("매장명 또는 비밀번호가 틀렸습니다.")

    with tab_reg:
        new_sn = st.text_input("새 매장명")
        new_pw = st.text_input("새 비밀번호", type="password")
        if st.button("매장 등록", use_container_width=True):
            if new_sn and new_pw:
                st.success("등록 완료") if register_store(new_sn, new_pw) else st.error("이미 등록된 매장입니다.")
            else:
                st.warning("매장명과 비밀번호를 입력해주세요.")
    st.stop()

# ─────────────────────────────────────────────
# 메인 헤더
# ─────────────────────────────────────────────

st.markdown('<div class="main-title">GA 기반 월간 근무 스케줄 자동 생성 시스템</div>', unsafe_allow_html=True)
st.markdown(f'<span class="store-badge">현재 매장: {st.session_state.store_name}</span>', unsafe_allow_html=True)

if st.button("로그아웃"):
    st.session_state.login = False
    st.session_state.store_name = None
    st.rerun()

if "employees" not in st.session_state:
    st.session_state.employees = load_employees(st.session_state.store_name)

# ─────────────────────────────────────────────
# 1. 월 설정
# ─────────────────────────────────────────────

st.markdown('<div class="section-title">1. 스케줄 생성 월 설정</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
year  = col1.number_input("년도", 2024, 2030, 2026)
month = col2.number_input("월", 1, 12, 5)

last_day = calendar.monthrange(year, month)[1]
dates = [date(year, month, d) for d in range(1, last_day + 1)]

def weekday_str(d): return WEEKDAYS[d.weekday()]

# ─────────────────────────────────────────────
# 사이드바 – 직원 등록/수정
# ─────────────────────────────────────────────

st.sidebar.header("직원 등록 / 수정")

employees = st.session_state.employees
options   = ["신규 직원"] + [e["이름"] for e in employees]
sel_name  = st.sidebar.selectbox("직원 등록 내역 불러오기", options)
sel_emp   = next((e for e in employees if e["이름"] == sel_name), None)

def _default(key, fallback):
    return sel_emp[key] if sel_emp else fallback

name      = st.sidebar.text_input("직원 이름", value=_default("이름", ""))
emp_type  = st.sidebar.selectbox("직원 유형", ["시급제", "월급제"],
                                  index=["시급제", "월급제"].index(_default("직원유형", "시급제")))
avail_shifts = st.sidebar.multiselect("가능 근무", SHIFTS, default=_default("가능근무", SHIFTS))

if emp_type == "시급제":
    avail_days = st.sidebar.multiselect("출근 가능 요일", WEEKDAYS, default=_default("출근가능요일", WEEKDAYS))
    monthly_off = None
else:
    avail_days  = WEEKDAYS
    monthly_off = st.sidebar.number_input("월 휴무 개수", 0, 15,
                                           int(_default("월휴무개수", 8) or 8))

max_work = st.sidebar.slider("월 최대 근무 횟수", 1, 31, int(_default("월최대근무횟수", 22)))

# 달력형 휴무 요청 선택
def calendar_dayoff_selector(dates, year, month, key_prefix, default_selected=None):
    default_selected = default_selected or []
    st.sidebar.markdown("### 휴무 요청일 선택")
    first_weekday, _ = calendar.monthrange(year, month)
    selected = []

    for wd in WEEKDAYS:
        pass  # header
    header_cols = st.sidebar.columns(7)
    for i, wd in enumerate(WEEKDAYS):
        header_cols[i].markdown(f"**{wd}**")

    week = [None] * first_weekday
    for d in dates:
        week.append(d)
        if len(week) == 7:
            cols = st.sidebar.columns(7)
            for i, day in enumerate(week):
                if day:
                    if cols[i].checkbox(str(day.day), value=day in default_selected,
                                        key=f"{key_prefix}_{day.isoformat()}"):
                        selected.append(day)
            week = []
    if week:
        week += [None] * (7 - len(week))
        cols = st.sidebar.columns(7)
        for i, day in enumerate(week):
            if day:
                if cols[i].checkbox(str(day.day), value=day in default_selected,
                                    key=f"{key_prefix}_{day.isoformat()}"):
                    selected.append(day)
    return selected

sel_day_off = calendar_dayoff_selector(
    dates, year, month,
    key_prefix=f"dayoff_{sel_name}_{name}",
    default_selected=_default("휴무요청", [])
)

new_emp = {
    "이름": name, "직원유형": emp_type,
    "월휴무개수": monthly_off, "월최대근무횟수": max_work,
    "출근가능요일": avail_days, "가능근무": avail_shifts,
    "휴무요청": sel_day_off,
}

if st.sidebar.button("직원 추가", use_container_width=True):
    if name:
        save_employee(st.session_state.store_name, new_emp)
        st.session_state.employees = load_employees(st.session_state.store_name)
        st.rerun()
    else:
        st.sidebar.warning("직원 이름을 입력해주세요.")

if st.sidebar.button("직원 정보 수정", use_container_width=True):
    if sel_emp:
        update_employee(sel_emp["id"], new_emp)
        st.session_state.employees = load_employees(st.session_state.store_name)
        st.rerun()
    else:
        st.sidebar.warning("수정할 직원을 선택해주세요.")

if st.sidebar.button("직원 삭제", use_container_width=True):
    if sel_emp:
        delete_employee(sel_emp["id"])
        st.session_state.employees = load_employees(st.session_state.store_name)
        st.rerun()
    else:
        st.sidebar.warning("삭제할 직원을 선택해주세요.")

# ─────────────────────────────────────────────
# 2. 등록된 직원 목록
# ─────────────────────────────────────────────

st.markdown('<div class="section-title">2. 등록된 직원</div>', unsafe_allow_html=True)

employees = st.session_state.employees
if not employees:
    st.warning("왼쪽 사이드바에서 직원을 먼저 등록해주세요.")
    st.stop()

show_df = pd.DataFrame(employees).drop(columns=["id"])
show_df["출근가능요일"] = show_df["출근가능요일"].apply(", ".join)
show_df["가능근무"]     = show_df["가능근무"].apply(", ".join)
show_df["휴무요청"]     = show_df["휴무요청"].apply(lambda x: ", ".join(d.strftime("%m/%d") for d in x))
st.dataframe(show_df, use_container_width=True)

if st.button("현재 매장 직원 전체 초기화"):
    clear_employees(st.session_state.store_name)
    st.session_state.employees = []
    st.rerun()

# ─────────────────────────────────────────────
# 3. 필요 인원 설정
# ─────────────────────────────────────────────

st.markdown('<div class="section-title">3. 필요 인원 설정</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
open_required  = col1.number_input("오픈 필요 인원", 1, 20, 2)
close_required = col2.number_input("마감 필요 인원", 1, 20, 2)
generations    = col3.slider("GA 반복 세대 수", 30, 300, 120)

required_staff = {"오픈": open_required, "마감": close_required}

# ─────────────────────────────────────────────
# GA 로직
# ─────────────────────────────────────────────

def get_target_work(emp):
    """목표 근무일수 (하드 제약 기준)"""
    if emp["직원유형"] == "월급제":
        return last_day - emp["월휴무개수"]
    return emp["월최대근무횟수"]

def is_available(emp, work_date, shift):
    """
    하드 제약:
      - 휴무요청일은 절대 배정 불가
      - 가능 근무 외 시프트 불가
      - 시급제: 가능 요일 외 불가
    """
    if work_date in emp["휴무요청"]:          # ← 하드 제약
        return False
    if shift not in emp["가능근무"]:
        return False
    if emp["직원유형"] == "시급제" and weekday_str(work_date) not in emp["출근가능요일"]:
        return False
    return True

def work_count(schedule, name):
    """분석/fitness용 — 날짜 기준 근무일수"""
    return sum(1 for d in dates if any(name in schedule[d][s] for s in SHIFTS))

def can_assign_wc(wc, emp, work_date, shift, schedule):
    """wc dict를 직접 받아 O(1) 판단 (create_individual / repair 내부용)"""
    if not is_available(emp, work_date, shift):
        return False
    if any(emp["이름"] in schedule[work_date][s] for s in SHIFTS):
        return False
    if wc[emp["이름"]] >= get_target_work(emp):
        return False
    return True

def empty_schedule():
    return {d: {s: [] for s in SHIFTS} for d in dates}

def create_individual():
    schedule = empty_schedule()
    wc = {e["이름"]: 0 for e in employees}
    slots = [(d, s) for d in dates for s in SHIFTS]
    random.shuffle(slots)
    for d, s in slots:
        candidates = [e for e in employees if can_assign_wc(wc, e, d, s, schedule)]
        random.shuffle(candidates)
        selected = candidates[:required_staff[s]]
        schedule[d][s] = [e["이름"] for e in selected]
        for e in selected:
            # 당일 처음 배정될 때만 wc 증가
            in_other = any(e["이름"] in schedule[d][sx] for sx in SHIFTS if sx != s)
            if not in_other:
                wc[e["이름"]] += 1
    return schedule

def repair_schedule(schedule):
    """
    1단계: 하드 제약 위반(휴무요청/가용불가) 제거
    2단계: 날짜 기준 근무일수 집계 후 초과분 제거
    3단계: 동일 wc dict 유지하면서 부족 인원 보충
    → wc를 단일 진실 공급원으로 사용해 work_count() 재순회 방지
    """
    lookup = emp_by_name if emp_by_name else {e["이름"]: e for e in employees}

    # 1단계: 하드 제약 위반 제거
    for d in dates:
        for s in SHIFTS:
            schedule[d][s] = [
                name for name in schedule[d][s]
                if is_available(lookup[name], d, s)
            ]
        # 당일 오픈+마감 중복 배정 제거
        today_assigned = set()
        for s in SHIFTS:
            deduped = []
            for name in schedule[d][s]:
                if name not in today_assigned:
                    deduped.append(name)
                    today_assigned.add(name)
            schedule[d][s] = deduped

    # 2단계: 날짜 기준 근무일수 집계 (오픈+마감 같은 날이면 1로 카운트)
    wc = {name: 0 for name in lookup}
    for d in dates:
        worked_today = set()
        for s in SHIFTS:
            for name in schedule[d][s]:
                worked_today.add(name)
        for name in worked_today:
            wc[name] += 1

    # 초과분 제거 (날짜 역순으로 제거해 앞쪽 근무 최대한 보존)
    for d in reversed(dates):
        for s in SHIFTS:
            cleaned = []
            for name in schedule[d][s]:
                target = get_target_work(lookup[name])
                if wc[name] > target:
                    # 이 날 다른 시프트에도 없으면 일수 감소
                    other_shifts = [sx for sx in SHIFTS if sx != s]
                    in_other = any(name in schedule[d][sx] for sx in other_shifts)
                    if not in_other:
                        wc[name] -= 1
                    # schedule에서 제거
                else:
                    cleaned.append(name)
            schedule[d][s] = cleaned[:required_staff[s]]

    # 3단계: 부족 보충 — wc dict를 직접 관리해 work_count() 재순회 없이 정확하게
    slots = [(d, s) for d in dates for s in SHIFTS]
    random.shuffle(slots)
    for d, s in slots:
        while len(schedule[d][s]) < required_staff[s]:
            # wc 기반으로 후보 필터 (하드 제약 + 목표치 미달 + 당일 미배정)
            candidates = []
            for emp in employees:
                name = emp["이름"]
                if not is_available(emp, d, s):
                    continue
                if any(name in schedule[d][sx] for sx in SHIFTS):
                    continue  # 당일 이미 배정
                if wc[name] >= get_target_work(emp):
                    continue  # 목표치 이미 달성
                candidates.append(emp)
            if not candidates:
                break
            random.shuffle(candidates)
            chosen = candidates[0]["이름"]
            schedule[d][s].append(chosen)
            # 당일 처음 배정되는 경우에만 wc 증가
            in_other = any(chosen in schedule[d][sx] for sx in SHIFTS if sx != s)
            if not in_other:
                wc[chosen] += 1
    return schedule

# 이름 → 직원 dict (매 함수 호출마다 linear search 방지)
emp_by_name: dict = {}

def build_emp_index():
    global emp_by_name
    emp_by_name = {e["이름"]: e for e in employees}

def max_consecutive(schedule, name):
    work_set = {d for d in dates if any(name in schedule[d][s] for s in SHIFTS)}
    max_c = cur = 0
    for d in dates:
        cur = cur + 1 if d in work_set else 0
        if cur > max_c:
            max_c = cur
    return max_c

def fitness(schedule):
    score = 0
    # 근무 횟수를 한 번에 집계
    wc = {name: 0 for name in emp_by_name}
    for d in dates:
        for s in SHIFTS:
            assigned = schedule[d][s]
            diff = len(assigned) - required_staff[s]
            if diff < 0:
                score -= abs(diff) * 10000   # 부족
            elif diff > 0:
                score -= diff * 500          # 초과
            for name in assigned:
                wc[name] += 1

    # 시급제 초과 페널티
    for emp in employees:
        if emp["직원유형"] == "시급제":
            over = wc[emp["이름"]] - get_target_work(emp)
            if over > 0:
                score -= over * 10000

    # 마감 → 다음날 오픈 페널티 (set 교집합으로 한 번에)
    for i in range(len(dates) - 1):
        closing = set(schedule[dates[i]]["마감"])
        opening = set(schedule[dates[i + 1]]["오픈"])
        score -= len(closing & opening) * 1000

    # 연속 근무 5일 초과 페널티
    for name in emp_by_name:
        work_set = {d for d in dates if any(name in schedule[d][s] for s in SHIFTS)}
        max_c = cur = 0
        for d in dates:
            cur = cur + 1 if d in work_set else 0
            if cur > max_c:
                max_c = cur
        if max_c > 5:
            score -= (max_c - 5) * 5000

    # 근무 분산 (순수 Python으로 np 호출 제거)
    vals = list(wc.values())
    mean = sum(vals) / len(vals)
    std  = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
    score -= std * 10

    return score

def crossover(p1, p2):
    child = empty_schedule()
    for d in dates:
        for s in SHIFTS:
            child[d][s] = (p1[d][s] if random.random() < 0.5 else p2[d][s])[:]
    return repair_schedule(child)

def mutate(schedule, rate=0.05):
    # 일부 슬롯을 초기화한 뒤 repair_schedule이 다시 채워줌
    for d in dates:
        for s in SHIFTS:
            if random.random() < rate:
                schedule[d][s] = []
    return repair_schedule(schedule)

def run_ga(on_progress=None):
    """
    on_progress(gen, total, elapsed, best_score) 콜백을 세대마다 호출.
    (score, schedule) 쌍으로 관리해 fitness 중복 계산 제거.
    """
    build_emp_index()

    pop_size   = 20
    elite_size = 5
    population = [repair_schedule(create_individual()) for _ in range(pop_size)]

    scored = [(fitness(ind), ind) for ind in population]
    best_score, best = max(scored, key=lambda x: x[0])
    start = time.time()

    for gen in range(generations):
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored[0][0] > best_score:
            best_score, best = scored[0]

        elites   = [ind for _, ind in scored[:elite_size]]
        top_pool = [ind for _, ind in scored[:10]]

        children = []
        while len(elites) + len(children) < pop_size:
            p1, p2 = random.sample(top_pool, 2)
            children.append(mutate(crossover(p1, p2)))

        # 엘리트는 점수 재사용, 자식만 새로 계산
        scored = scored[:elite_size] + [(fitness(c), c) for c in children]

        if on_progress:
            on_progress(gen + 1, generations, time.time() - start, best_score)

    return best, best_score

# ─────────────────────────────────────────────
# 4. 스케줄 생성 & 결과 출력
# ─────────────────────────────────────────────

if st.button("GA로 월간 스케줄 생성", type="primary", use_container_width=True):
    prog_bar  = st.progress(0)
    stat_text = st.empty()

    def on_progress(gen, total, elapsed, best_score):
        ratio    = gen / total
        avg_sec  = elapsed / gen
        remaining = avg_sec * (total - gen)
        prog_bar.progress(ratio)
        stat_text.markdown(
            f"**세대 {gen} / {total}** &nbsp;|&nbsp; "
            f"경과 {elapsed:.1f}s &nbsp;|&nbsp; "
            f"예상 남은 시간 **{remaining:.1f}s** &nbsp;|&nbsp; "
            f"현재 최고 점수 {best_score:,.0f}"
        )

    best_schedule, best_score = run_ga(on_progress=on_progress)
    prog_bar.progress(1.0)
    stat_text.success(f"완료! 총 소요 시간 및 최종 적합도 점수: {round(best_score, 2)}")

    st.markdown('<div class="section-title">4. 월간 캘린더 스케줄</div>', unsafe_allow_html=True)

    # 달력 뷰 (월급제 ★, 시급제 ◆ 마커)
    emp_type_map = {e["이름"]: e["직원유형"] for e in employees}
    def name_with_marker(name):
        return f"{name}{'★' if emp_type_map.get(name) == '월급제' else '◆'}"

    first_wd, _ = calendar.monthrange(year, month)
    rows, week  = [], [""] * first_wd
    for d in dates:
        o = ", ".join(name_with_marker(n) for n in best_schedule[d]["오픈"]) or "-"
        c = ", ".join(name_with_marker(n) for n in best_schedule[d]["마감"]) or "-"
        week.append(f"{d.day}일\n오픈: {o}\n마감: {c}")
        if len(week) == 7:
            rows.append(week); week = []
    if week:
        rows.append(week + [""] * (7 - len(week)))
    st.dataframe(pd.DataFrame(rows, columns=WEEKDAYS), use_container_width=True, height=500)
    st.caption("★ 월급제  ◆ 시급제")

    st.markdown('<div class="section-title">5. 상세 스케줄표</div>', unsafe_allow_html=True)
    detail = []
    for d in dates:
        detail.append({
            "날짜": d.strftime("%m/%d"), "요일": weekday_str(d),
            "오픈": ", ".join(name_with_marker(n) for n in best_schedule[d]["오픈"]) or "없음",
            "마감": ", ".join(name_with_marker(n) for n in best_schedule[d]["마감"]) or "없음",
            "오픈 부족": max(0, open_required  - len(best_schedule[d]["오픈"])),
            "마감 부족": max(0, close_required - len(best_schedule[d]["마감"])),
        })
    result_df = pd.DataFrame(detail)

    def highlight_shortage(row):
        styles = [""] * len(row)
        cols = list(row.index)
        if row.get("오픈 부족", 0) > 0:
            styles[cols.index("오픈 부족")] = "background-color:#fee2e2; color:#b91c1c; font-weight:bold"
        if row.get("마감 부족", 0) > 0:
            styles[cols.index("마감 부족")] = "background-color:#fee2e2; color:#b91c1c; font-weight:bold"
        return styles

    st.dataframe(result_df.style.apply(highlight_shortage, axis=1), use_container_width=True)

    st.markdown('<div class="section-title">6. 직원별 근무 분석</div>', unsafe_allow_html=True)
    analysis = []
    for emp in employees:
        name = emp["이름"]
        wc   = work_count(best_schedule, name)
        mc   = max_consecutive(best_schedule, name)
        open_cnt = close_cnt = c2o = 0
        for i, d in enumerate(dates):
            if name in best_schedule[d]["오픈"]: open_cnt += 1
            if name in best_schedule[d]["마감"]: close_cnt += 1
            if i < len(dates)-1 and name in best_schedule[d]["마감"] and name in best_schedule[dates[i+1]]["오픈"]:
                c2o += 1
        target = get_target_work(emp)
        analysis.append({
            "직원": name, "유형": emp["직원유형"],
            "목표근무일수": target, "실제근무일수": wc,
            "목표휴무일수": last_day - target, "실제휴무일수": last_day - wc,
            "오픈횟수": open_cnt, "마감횟수": close_cnt,
            "최대연속근무": mc, "마감→다음날오픈": c2o,
        })
    analysis_df = pd.DataFrame(analysis)

    def style_by_type(row):
        if row["유형"] == "월급제":
            base = "background-color:#dbeafe; color:#1e40af"   # 파란 계열
        else:
            base = "background-color:#dcfce7; color:#166534"   # 초록 계열
        # 실제 != 목표면 근무일수 셀 강조
        styles = [base] * len(row)
        cols = list(row.index)
        if row["실제근무일수"] != row["목표근무일수"]:
            styles[cols.index("실제근무일수")] = base + "; font-weight:bold; text-decoration:underline"
        return styles

    st.dataframe(analysis_df.style.apply(style_by_type, axis=1), use_container_width=True)
    st.caption("🟦 월급제  🟩 시급제  |  실제근무일수 밑줄 = 목표 불일치")

    total_shortage = int(result_df["오픈 부족"].sum() + result_df["마감 부족"].sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("총 부족 인원",         total_shortage)
    col2.metric("마감→다음날 오픈",      int(analysis_df["마감→다음날오픈"].sum()))
    col3.metric("5일 초과 연속근무 직원", int((analysis_df["최대연속근무"] > 5).sum()))

    st.success("월간 스케줄 생성이 완료되었습니다.")
