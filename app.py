import streamlit as st
import pandas as pd
import re
from datetime import date, time
from io import BytesIO

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.13 FINAL (KR) - 사용자 클릭 즉시 상세표 노출(하단 선택 제거) + 배타 우선순위(기관기준)"

# =========================================================
# 공휴일(법정/대체) - holidays 라이브러리 사용
# requirements.txt: holidays, openpyxl
# =========================================================
HAS_HOLIDAYS = True
try:
    import holidays  # type: ignore
except Exception:
    HAS_HOLIDAYS = False

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="법인카드 운영기준 위반 점검(최종)", layout="wide")

# =========================================================
# UTILS
# =========================================================
def normalize_text(x) -> str:
    if pd.isna(x):
        return ""
    x = str(x).lower()
    x = re.sub(r"[^a-z0-9가-힣]", "", x)
    return x

def extract_parentheses_name(x: str) -> str:
    if pd.isna(x):
        return ""
    m = re.search(r"\((.*?)\)", str(x))
    return m.group(1).strip() if m else ""

def combine_date_time(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    dt_str = date_series.astype(str).str.strip() + " " + time_series.astype(str).str.strip()
    return pd.to_datetime(dt_str, errors="coerce")

def pick_col(df: pd.DataFrame, *cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

def detect_columns(df: pd.DataFrame) -> dict:
    date_col = pick_col(df, "승인일자", "거래일자", "결제일자", "사용일자", "일자", "날짜", "Approval date")
    time_col = pick_col(df, "승인일시", "승인시간", "거래시간", "결제시간", "시간", "Approval time")
    datetime_col = pick_col(df, "거래일시", "결제일시", "일시", "Approval datetime", "승인일시(일시)")

    return {
        "user": pick_col(df, "사용자", "성명", "사원명", "User"),
        "merchant": pick_col(df, "거래처명", "거래처", "가맹점", "가맹점명", "Customer name"),
        "amount": pick_col(df, "금액", "금액1", "금액.1", "금액(원)", "이용금액", "승인금액", "결제금액", "Amount", "Amount 1"),
        "date": date_col,
        "time": time_col,
        "datetime": datetime_col,
        "title": pick_col(df, "문서 내용(제목)", "문서내용(제목)", "문서 내용", "Document content (title)"),
        "card_name": pick_col(df, "카드명", "Card name"),
    }

def build_datetime(df: pd.DataFrame, m: dict) -> pd.Series:
    if m.get("date") and m.get("time") and m["date"] in df.columns and m["time"] in df.columns:
        return combine_date_time(df[m["date"]], df[m["time"]])
    if m.get("datetime") and m["datetime"] in df.columns:
        return pd.to_datetime(df[m["datetime"]], errors="coerce")
    if m.get("date") and m["date"] in df.columns:
        return pd.to_datetime(df[m["date"]], errors="coerce")
    return pd.to_datetime(pd.Series([pd.NaT] * len(df)), errors="coerce")

def to_excel_bytes(d: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        d.to_excel(writer, index=False, sheet_name="data")
    return out.getvalue()

def download_block(d: pd.DataFrame, key: str):
    b1, b2 = st.columns(2)
    with b1:
        st.download_button(
            "CSV 다운로드",
            data=d.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            key=f"dl_csv_{key}",
            use_container_width=True
        )
    with b2:
        st.download_button(
            "엑셀 다운로드",
            data=to_excel_bytes(d),
            file_name=f"{key}.xlsx",
            key=f"dl_xlsx_{key}",
            use_container_width=True
        )

# =========================================================
# ENGINE
# =========================================================
def run_audit(
    df_raw: pd.DataFrame,
    include_weekend: bool,
    include_public_holiday: bool,
    exclude_vehicle_from_night: bool,
    restricted_keywords: list[str],
    vehicle_keywords: list[str],
    # ✅ 배타 우선순위(강함→약함): 제한업종 > 주말 > 공휴일 > 심야
    exclusive_priority_high_to_low: list[str],
    exclude_bar_club: bool = True,
    exclude_branch_store: bool = True,
) -> tuple[pd.DataFrame, dict]:
    df = df_raw.copy()
    m = detect_columns(df)

    if not m.get("merchant") or not m.get("amount"):
        raise KeyError(
            "필수 컬럼(거래처명/가맹점, 금액)을 찾지 못했습니다.\n"
            f"현재 컬럼: {list(df.columns)}"
        )

    df["사용자"] = df[m["user"]].astype(str) if m.get("user") else "미지정"
    df["가맹점"] = df[m["merchant"]].astype(str)
    df["일시"] = build_datetime(df, m)

    if df["일시"].notna().mean() < 0.5:
        raise ValueError("일시 파싱 실패(유효 일시 < 50%). '승인일자+승인일시(시간)' 또는 '거래일시/일시' 컬럼을 확인하세요.")

    hour0_ratio = (df["일시"].dt.hour.fillna(-1).eq(0)).mean()
    if hour0_ratio > 0.85 and not m.get("time"):
        raise ValueError(
            "일시에 시간이 거의 없습니다(대부분 00:00:00).\n"
            "승인일자(날짜만)로 분석되고 있을 가능성이 큽니다.\n"
            "시간이 포함된 컬럼(승인일시/거래일시/일시)을 확인하세요."
        )

    df["문서제목"] = df[m["title"]].astype(str) if m.get("title") else ""
    df["카드사용자명(괄호)"] = df[m["card_name"]].astype(str).apply(extract_parentheses_name) if m.get("card_name") else ""

    df["P_AMT"] = pd.to_numeric(
        df[m["amount"]].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
        errors="coerce"
    ).fillna(0).astype(int)

    df["DATE"] = df["일시"].dt.date

    # 차량비(심야 제외)
    vkeys = [normalize_text(k) for k in vehicle_keywords if k.strip()]

    def is_vehicle_row(row) -> bool:
        hay = " ".join([str(row.get("가맹점", "")), str(row.get("문서제목", ""))])
        n = normalize_text(hay)
        return any(k in n for k in vkeys)

    df["F_VEHICLE"] = df.apply(is_vehicle_row, axis=1)

    # ✅ 심야: 23:00:00 ~ 06:00:00 (06:00:00 포함)
    late_start = time(23, 0, 0)
    late_end = time(6, 0, 0)
    tseries = df["일시"].dt.time
    df["F_NIGHT"] = tseries.apply(lambda x: (x >= late_start) or (x <= late_end) if pd.notna(x) else False)

    if exclude_vehicle_from_night:
        df.loc[df["F_VEHICLE"] == True, "F_NIGHT"] = False

    # 주말(토/일)
    df["F_WEEKEND"] = (df["일시"].dt.weekday >= 5) if include_weekend else False

    # 공휴일(법정/대체)
    if include_public_holiday and HAS_HOLIDAYS:
        years = sorted({d.year for d in df["DATE"].dropna() if isinstance(d, date)})
        kr = holidays.KR(years=years)  # type: ignore
        df["F_HOLIDAY"] = df["DATE"].isin(kr)
    else:
        df["F_HOLIDAY"] = False

    # 제한업종(명시적 유흥만) + bar/club + 지점/점/branch 제외
    rkeys = [normalize_text(k) for k in restricted_keywords if k.strip()]

    def is_restricted(name: str) -> bool:
        n = normalize_text(name)

        if exclude_branch_store and (("지점" in n) or ("branch" in n) or n.endswith("점")):
            return False

        if exclude_bar_club and any(k in n for k in ["bar", "club", "클럽", "pub", "lounge"]):
            return False

        return any(k in n for k in rkeys)

    df["F_RESTRICT"] = df["가맹점"].apply(is_restricted)

    # 위반사유(중복 가능)
    def reason(row):
        r = []
        if row["F_NIGHT"]:
            r.append("심야(23:00~06:00)")
        if row["F_WEEKEND"]:
            r.append("휴무일(주말)")
        if row["F_HOLIDAY"]:
            r.append("공휴일(법정/대체)")
        if row["F_RESTRICT"]:
            r.append("제한업종(명시적 유흥)")
        return " / ".join(r)

    df["위반사유"] = df.apply(reason, axis=1)
    df["운영기준위반"] = df["위반사유"] != ""

    # 배타 분류(합계 일치): 강한 위반 우선 부여
    def primary_type(row):
        for p in exclusive_priority_high_to_low:
            if p == "제한업종" and row["F_RESTRICT"]:
                return "제한업종"
            if p == "주말" and row["F_WEEKEND"]:
                return "주말"
            if p == "공휴일" and row["F_HOLIDAY"]:
                return "공휴일"
            if p == "심야" and row["F_NIGHT"]:
                return "심야"
        return ""

    df["주요위반유형(배타)"] = df.apply(primary_type, axis=1)

    features = {
        "mapping": m,
        "exclusive_priority_high_to_low": exclusive_priority_high_to_low,
        "late_start": "23:00:00",
        "late_end": "06:00:00",
        "holiday_enabled": HAS_HOLIDAYS,
    }
    return df, features

# =========================================================
# SESSION STATE
# =========================================================
if "focus_exclusive" not in st.session_state:
    st.session_state["focus_exclusive"] = "전체"
if "excluded_users" not in st.session_state:
    st.session_state["excluded_users"] = []
if "selected_user" not in st.session_state:
    st.session_state["selected_user"] = None
if "selection_supported" not in st.session_state:
    st.session_state["selection_supported"] = True

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("RAW DATA 업로드")
uploaded = st.sidebar.file_uploader("지출결의현황.xlsx (또는 CSV)", type=["xlsx", "csv"])

st.sidebar.markdown("---")
st.sidebar.subheader("기준(고정)")
st.sidebar.write("- 심야: **23:00:00 ~ 06:00:00**")
st.sidebar.write("- 휴무일: **토/일**")
st.sidebar.write("- 공휴일: **법정/대체(holidays.KR)**")
if not HAS_HOLIDAYS:
    st.sidebar.warning("공휴일 판정을 위해 `holidays` 패키지 설치가 필요합니다.")

include_weekend = st.sidebar.checkbox("휴무일(주말) 포함", value=True, key="opt_weekend")
include_public_holiday = st.sidebar.checkbox("공휴일 포함", value=True, key="opt_holiday")
exclude_vehicle_from_night = st.sidebar.checkbox("차량비는 심야 위반에서 제외", value=True, key="opt_vehicle_excl")

st.sidebar.markdown("---")
st.sidebar.subheader("배타 분류(기관 기준)")
st.sidebar.write("우선순위(강함→약함): **제한업종 > 주말 > 공휴일 > 심야**")
exclusive_priority_high_to_low = ["제한업종", "주말", "공휴일", "심야"]

st.sidebar.markdown("---")
st.sidebar.subheader("제한업종 키워드(명시적 유흥만)")
restricted_text = st.sidebar.text_area(
    "줄바꿈/쉼표로 구분",
    value="유흥주점\n단란주점\n나이트클럽\n안마시술소\n안마\n마사지",
    height=110,
    key="kw_restricted"
)
restricted_keywords = [x.strip() for x in re.split(r"[,\n]+", restricted_text) if x.strip()]

st.sidebar.subheader("차량비 키워드(심야 제외용)")
vehicle_text = st.sidebar.text_area(
    "줄바꿈/쉼표로 구분",
    value="차량운전비,차량,유류,주유,하이패스,통행료,주차,주차비,택시,대리운전,카카오T,렌터카,고속도로,정비,세차",
    height=90,
    key="kw_vehicle"
)
vehicle_keywords = [x.strip() for x in re.split(r"[,\n]+", vehicle_text) if x.strip()]

# =========================================================
# MAIN
# =========================================================
st.title("법인카드 운영기준 위반 점검(최종)")
st.caption(f"BUILD: {BUILD} | 공휴일판정: {'활성' if HAS_HOLIDAYS else '비활성'}")

if not uploaded:
    st.info("왼쪽에서 RAW DATA 파일을 업로드하세요.")
    st.stop()

# LOAD
try:
    if uploaded.name.lower().endswith(".xlsx"):
        df_raw = pd.read_excel(uploaded)
    else:
        try:
            df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
        except Exception:
            df_raw = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"파일 로드 실패: {e}")
    st.stop()

# AUDIT
try:
    df, feat = run_audit(
        df_raw=df_raw,
        include_weekend=include_weekend,
        include_public_holiday=include_public_holiday,
        exclude_vehicle_from_night=exclude_vehicle_from_night,
        restricted_keywords=restricted_keywords,
        vehicle_keywords=vehicle_keywords,
        exclusive_priority_high_to_low=exclusive_priority_high_to_low,
    )
except Exception as e:
    st.error(str(e))
    st.stop()

with st.expander("컬럼 자동 인식 결과", expanded=False):
    st.json(feat["mapping"])

# =========================================================
# DATA PREP
# =========================================================
DISPLAY_COLS = ["사용자", "가맹점", "P_AMT", "일시", "위반사유", "주요위반유형(배타)", "문서제목", "카드사용자명(괄호)"]
viol = df[df["운영기준위반"]].copy()

# =========================================================
# ① TOP SUMMARY (배타 클릭형)
# =========================================================
st.subheader("① 위반 요약(배타 분류: 합계 일치)")
st.caption("아래 버튼을 누르면 해당 배타 분류 위반 사례가 즉시 표시됩니다.")

total_unique = int(viol.shape[0])
counts_excl = viol["주요위반유형(배타)"].value_counts().reindex(["심야", "공휴일", "주말", "제한업종"]).fillna(0).astype(int)
dup_rows = int((viol[["F_NIGHT","F_WEEKEND","F_HOLIDAY","F_RESTRICT"]].sum(axis=1) > 1).sum())

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("전체 위반(유니크)", total_unique)
m2.metric("심야(배타)", int(counts_excl.get("심야", 0)))
m3.metric("공휴일(배타)", int(counts_excl.get("공휴일", 0)))
m4.metric("주말(배타)", int(counts_excl.get("주말", 0)))
m5.metric("제한업종(배타)", int(counts_excl.get("제한업종", 0)))
m6.metric("복수위반 행", dup_rows)

st.markdown("**배타 우선순위(강함→약함): 제한업종 > 주말 > 공휴일 > 심야**")

b0, b1, b2, b3, b4 = st.columns(5)
if b0.button(f"전체 보기 ({total_unique})", key="btn_focus_all", use_container_width=True):
    st.session_state["focus_exclusive"] = "전체"
if b1.button(f"심야 보기 ({int(counts_excl.get('심야',0))})", key="btn_focus_night", use_container_width=True):
    st.session_state["focus_exclusive"] = "심야"
if b2.button(f"공휴일 보기 ({int(counts_excl.get('공휴일',0))})", key="btn_focus_holiday", use_container_width=True):
    st.session_state["focus_exclusive"] = "공휴일"
if b3.button(f"주말 보기 ({int(counts_excl.get('주말',0))})", key="btn_focus_weekend", use_container_width=True):
    st.session_state["focus_exclusive"] = "주말"
if b4.button(f"제한업종 보기 ({int(counts_excl.get('제한업종',0))})", key="btn_focus_restrict", use_container_width=True):
    st.session_state["focus_exclusive"] = "제한업종"

focus = st.session_state["focus_exclusive"]

# =========================================================
# ② FOCUSED CASES
# =========================================================
st.markdown("---")
st.subheader(f"② 선택된 배타 분류 위반 사례: {focus}")
if focus == "전체":
    focus_df = viol.copy()
else:
    focus_df = viol[viol["주요위반유형(배타)"] == focus].copy()

download_block(focus_df[DISPLAY_COLS], f"exclusive_{focus}")
st.dataframe(focus_df[DISPLAY_COLS], use_container_width=True, height=320)

# =========================================================
# ③ USER SUMMARY + 즉시 상세 표시(하단 선택 제거)
# =========================================================
st.markdown("---")
st.subheader("③ 사용자별 위반 현황(클릭 즉시 상세 표시)")
st.caption("사용자 행을 클릭하면, 바로 아래에 해당 사용자의 위반 사례가 즉시 표시됩니다. (하단 선택창 없음)")

excluded = set(st.session_state.get("excluded_users", []))
user_summary = (
    focus_df.groupby("사용자", as_index=False)
    .agg(
        위반건수=("운영기준위반", "count"),
        심야=("F_NIGHT", "sum"),
        주말=("F_WEEKEND", "sum"),
        공휴일=("F_HOLIDAY", "sum"),
        제한업종=("F_RESTRICT", "sum"),
        총금액=("P_AMT", "sum"),
    )
    .sort_values(["위반건수", "총금액"], ascending=[False, False])
)
user_summary_view = user_summary[~user_summary["사용자"].astype(str).isin(excluded)].copy() if excluded else user_summary.copy()

# 제외 목록 관리(상단에만)
x1, x2, x3 = st.columns([2, 2, 1])
with x1:
    st.write(f"제외(검토완료) 사용자: **{len(excluded)}명**")
with x2:
    st.session_state["excluded_users"] = st.multiselect(
        "제외 사용자 관리(검토완료)",
        options=sorted(user_summary["사용자"].astype(str).unique().tolist()),
        default=sorted(list(excluded)),
        key="ms_excluded_users"
    )
with x3:
    if st.button("제외 목록 초기화", key="btn_clear_excluded", use_container_width=True):
        st.session_state["excluded_users"] = []
        st.session_state["selected_user"] = None
        st.rerun()

# 사용자 클릭 선택
selected_user = st.session_state.get("selected_user")
selection_supported = st.session_state.get("selection_supported", True)

sel_rows = []
if selection_supported:
    try:
        event = st.dataframe(
            user_summary_view,
            use_container_width=True,
            height=300,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="df_user_summary_select"
        )
        sel_rows = event.selection.rows  # type: ignore
    except Exception:
        # 클릭 선택 미지원 환경
        st.session_state["selection_supported"] = False
        selection_supported = False

if not selection_supported:
    st.warning("현재 실행 환경의 Streamlit 버전에서는 '표 클릭 선택'이 제한됩니다. 아래에서 사용자만 선택해 주세요(하단 선택창은 없습니다).")
    all_users = user_summary_view["사용자"].astype(str).tolist()
    if all_users:
        selected_user = st.selectbox("사용자 선택", options=all_users, index=0, key="sb_user_inline")
        st.session_state["selected_user"] = selected_user

if sel_rows:
    idx = sel_rows[0]
    if 0 <= idx < len(user_summary_view):
        selected_user = str(user_summary_view.iloc[idx]["사용자"])
        st.session_state["selected_user"] = selected_user

# 선택 사용자 제외 버튼
bb1, bb2 = st.columns([1, 3])
with bb1:
    if st.button("선택 사용자 제외(검토완료)", key="btn_exclude_selected", use_container_width=True):
        if st.session_state.get("selected_user"):
            cur = str(st.session_state["selected_user"])
            cur_list = set(st.session_state.get("excluded_users", []))
            cur_list.add(cur)
            st.session_state["excluded_users"] = sorted(list(cur_list))
            st.session_state["selected_user"] = None
            st.rerun()
with bb2:
    if not selected_user:
        st.info("사용자 표에서 행을 클릭하면, 바로 아래에 위반 사례가 표시됩니다.")

# ✅ 바로 아래에 사용자 위반사례 즉시 표시
st.markdown("#### 사용자 위반 사례(즉시 표시)")
if selected_user:
    st.write(f"선택 사용자: **{selected_user}**  |  배타 분류: **{focus}**")
    detail_df = focus_df[focus_df["사용자"].astype(str) == str(selected_user)].copy()
else:
    st.write(f"선택 사용자: (없음)  |  배타 분류: **{focus}**")
    detail_df = focus_df.copy()

download_block(detail_df[DISPLAY_COLS], f"detail_{focus}_{selected_user or 'all'}")
st.dataframe(detail_df[DISPLAY_COLS], use_container_width=True, height=520)

# =========================================================
# ④ 유형별 탭(선택 사항)
# =========================================================
st.markdown("---")
st.subheader("④ 위반 유형별 전체 목록(다운로드)")

def tab_df(mode: str) -> pd.DataFrame:
    if mode == "전체":
        return viol.copy()
    if mode == "심야":
        return df[df["F_NIGHT"]].copy()
    if mode == "주말":
        return df[df["F_WEEKEND"]].copy()
    if mode == "공휴일":
        return df[df["F_HOLIDAY"]].copy()
    if mode == "제한업종":
        return df[df["F_RESTRICT"]].copy()
    if mode == "배타":
        return viol.sort_values(["주요위반유형(배타)", "일시"]).copy()
    return df.iloc[0:0].copy()

tabs = st.tabs(["전체(위반)", "심야", "공휴일", "주말", "제한업종", "배타(합계일치)"])

tab_keys = ["전체", "심야", "공휴일", "주말", "제한업종", "배타"]
for i, tname in enumerate(tab_keys):
    with tabs[i]:
        d = tab_df(tname)
        download_block(d[DISPLAY_COLS], f"tab_{tname}")
        st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

st.caption("엑셀 다운로드: openpyxl 필요 | 공휴일 판정: holidays 필요")
