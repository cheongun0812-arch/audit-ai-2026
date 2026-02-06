import streamlit as st
import pandas as pd
import re
from datetime import date, time
from io import BytesIO

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.11 FINAL (KR) - 단순화(표+다운로드 중심) + 심야 23:00~06:00"

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
    """
    업로드 파일 헤더 자동 인식.
    - '승인일자'(날짜) + '승인일시'(시간) 분리형을 최우선으로 지원
    """
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
    # 1) 날짜+시간 분리형(권장/가장 정확)
    if m.get("date") and m.get("time") and m["date"] in df.columns and m["time"] in df.columns:
        return combine_date_time(df[m["date"]], df[m["time"]])
    # 2) 통합 일시
    if m.get("datetime") and m["datetime"] in df.columns:
        return pd.to_datetime(df[m["datetime"]], errors="coerce")
    # 3) 날짜만(심야 판정 불가 → 아래에서 차단)
    if m.get("date") and m["date"] in df.columns:
        return pd.to_datetime(df[m["date"]], errors="coerce")
    return pd.to_datetime(pd.Series([pd.NaT] * len(df)), errors="coerce")

def to_excel_bytes(d: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        d.to_excel(writer, index=False, sheet_name="data")
    return out.getvalue()

# =========================================================
# ENGINE (단순/명확)
# =========================================================
def run_audit(
    df_raw: pd.DataFrame,
    include_weekend: bool,
    include_public_holiday: bool,
    exclude_vehicle_from_night: bool,
    restricted_keywords: list[str],
    vehicle_keywords: list[str],
    exclude_bar_club: bool = True,
    exclude_branch_store: bool = True,
    exclusive_priority: list[str] | None = None,
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

    # 날짜만 들어가 00:00:00이 대량인 경우 차단(심야 오탐 방지)
    hour0_ratio = (df["일시"].dt.hour.fillna(-1).eq(0)).mean()
    if hour0_ratio > 0.85 and not m.get("time"):
        raise ValueError(
            "일시에 시간이 거의 없습니다(대부분 00:00:00).\n"
            "승인일자(날짜만)로 분석되고 있을 가능성이 큽니다.\n"
            "시간이 포함된 컬럼(승인일시/거래일시/일시)을 확인하세요."
        )

    # 문서제목/카드명 괄호
    df["문서제목"] = df[m["title"]].astype(str) if m.get("title") else ""
    df["카드사용자명(괄호)"] = df[m["card_name"]].astype(str).apply(extract_parentheses_name) if m.get("card_name") else ""

    # 금액
    df["P_AMT"] = pd.to_numeric(
        df[m["amount"]].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
        errors="coerce"
    ).fillna(0).astype(int)

    df["DATE"] = df["일시"].dt.date

    # 차량비(심야 제외용)
    vkeys = [normalize_text(k) for k in vehicle_keywords if k.strip()]
    def is_vehicle_row(row) -> bool:
        hay = " ".join([str(row.get("가맹점","")), str(row.get("문서제목",""))])
        n = normalize_text(hay)
        return any(k in n for k in vkeys)

    df["F_VEHICLE"] = df.apply(is_vehicle_row, axis=1)

    # ✅ 심야 기준 고정: 23:00:00 ~ 06:00:00 (06:00:00 포함)
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

    # 제한업종: "명시적 유흥"만 + bar/club/지점/점/branch 제외
    rkeys = [normalize_text(k) for k in restricted_keywords if k.strip()]

    def is_restricted(name: str) -> bool:
        n = normalize_text(name)

        if exclude_branch_store and (("지점" in n) or ("branch" in n) or n.endswith("점")):
            return False

        if exclude_bar_club and any(k in n for k in ["bar", "club", "클럽", "pub", "lounge"]):
            return False

        return any(k in n for k in rkeys)

    df["F_RESTRICT"] = df["가맹점"].apply(is_restricted)

    # 위반 사유(중복 가능)
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

    # 배타적(합계 일치) 분류
    if exclusive_priority is None:
        # 기관표준 기본값
        exclusive_priority = ["심야", "공휴일", "주말", "제한업종"]

    def primary_type(row):
        for p in exclusive_priority:
            if p == "심야" and row["F_NIGHT"]:
                return "심야"
            if p == "공휴일" and row["F_HOLIDAY"]:
                return "공휴일"
            if p == "주말" and row["F_WEEKEND"]:
                return "주말"
            if p == "제한업종" and row["F_RESTRICT"]:
                return "제한업종"
        return ""

    df["주요위반유형(배타)"] = df.apply(primary_type, axis=1)

    features = {
        "mapping": m,
        "exclusive_priority": exclusive_priority,
        "late_start": "23:00:00",
        "late_end": "06:00:00",
        "holiday_enabled": HAS_HOLIDAYS,
    }
    return df, features

# =========================================================
# UI (단순 구성)
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

include_weekend = st.sidebar.checkbox("휴무일(주말) 포함", value=True)
include_public_holiday = st.sidebar.checkbox("공휴일 포함", value=True)
exclude_vehicle_from_night = st.sidebar.checkbox("차량비는 심야 위반에서 제외", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("배타 분류 우선순위(합계 일치)")
preset = st.sidebar.selectbox(
    "기관 기준 선택",
    options=[
        "기관표준: 심야 > 공휴일 > 주말 > 제한업종",
        "기관표준: 심야 > 주말 > 공휴일 > 제한업종",
        "기존: 제한업종 > 심야 > 공휴일 > 주말",
    ],
    index=0,
)
if preset.startswith("기관표준: 심야 > 공휴일"):
    exclusive_priority = ["심야", "공휴일", "주말", "제한업종"]
elif preset.startswith("기관표준: 심야 > 주말"):
    exclusive_priority = ["심야", "주말", "공휴일", "제한업종"]
else:
    exclusive_priority = ["제한업종", "심야", "공휴일", "주말"]

st.sidebar.markdown("---")
st.sidebar.subheader("제한업종 키워드(명시적 유흥만)")
restricted_text = st.sidebar.text_area(
    "줄바꿈/쉼표로 구분",
    value="유흥주점\n단란주점\n나이트클럽\n안마시술소\n안마\n마사지",
    height=110
)
restricted_keywords = [x.strip() for x in re.split(r"[,\n]+", restricted_text) if x.strip()]

st.sidebar.subheader("차량비 키워드(심야 제외용)")
vehicle_text = st.sidebar.text_area(
    "줄바꿈/쉼표로 구분",
    value="차량운전비,차량,유류,주유,하이패스,통행료,주차,주차비,택시,대리운전,카카오T,렌터카,고속도로,정비,세차",
    height=90
)
vehicle_keywords = [x.strip() for x in re.split(r"[,\n]+", vehicle_text) if x.strip()]

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
        exclusive_priority=exclusive_priority,
    )
except Exception as e:
    st.error(str(e))
    st.stop()

with st.expander("컬럼 자동 인식 결과", expanded=False):
    st.json(feat["mapping"])

# =========================================================
# 핵심 요약(감사 보고용)
# =========================================================
viol = df[df["운영기준위반"]].copy()

total_unique = int(viol.shape[0])
night_cnt = int(viol["F_NIGHT"].sum())
weekend_cnt = int(viol["F_WEEKEND"].sum())
holiday_cnt = int(viol["F_HOLIDAY"].sum())
restrict_cnt = int(viol["F_RESTRICT"].sum())
dup_rows = int((viol[["F_NIGHT","F_WEEKEND","F_HOLIDAY","F_RESTRICT"]].sum(axis=1) > 1).sum())

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("전체 위반(유니크)", total_unique)
c2.metric("심야(중복포함)", night_cnt)
c3.metric("주말(중복포함)", weekend_cnt)
c4.metric("공휴일(중복포함)", holiday_cnt)
c5.metric("제한업종(중복포함)", restrict_cnt)
c6.metric("복수위반 행", dup_rows)

st.markdown("### 배타 분류(합계 일치)")
st.caption("한 건당 1개의 유형만 부여(우선순위 적용) → 합계가 전체 위반과 정확히 일치")
st.write("우선순위:", " > ".join(feat["exclusive_priority"]))

exc_counts = viol["주요위반유형(배타)"].value_counts().reindex(["심야","공휴일","주말","제한업종"]).fillna(0).astype(int)
d1, d2, d3, d4 = st.columns(4)
d1.metric("심야(배타)", int(exc_counts.get("심야", 0)))
d2.metric("공휴일(배타)", int(exc_counts.get("공휴일", 0)))
d3.metric("주말(배타)", int(exc_counts.get("주말", 0)))
d4.metric("제한업종(배타)", int(exc_counts.get("제한업종", 0)))

st.markdown("---")

# =========================================================
# 사용자 기준 점검(표만)
# =========================================================
st.subheader("사용자별 위반 현황(감사용)")

user_summary = (
    viol.groupby("사용자", as_index=False)
    .agg(
        위반건수=("운영기준위반", "count"),
        심야=("F_NIGHT", "sum"),
        주말=("F_WEEKEND", "sum"),
        공휴일=("F_HOLIDAY", "sum"),
        제한업종=("F_RESTRICT", "sum"),
        총금액=("P_AMT", "sum"),
    )
    .sort_values("위반건수", ascending=False)
)

st.dataframe(user_summary, use_container_width=True, height=280)

pick_user = st.selectbox("상세 확인할 사용자", options=(user_summary["사용자"].astype(str).tolist() if len(user_summary) else ["(위반 없음)"]), index=0)
df_user = viol[viol["사용자"].astype(str) == str(pick_user)].copy() if len(user_summary) else viol.iloc[0:0].copy()

st.markdown(f"#### {pick_user} - 위반 상세")
DISPLAY_COLS = ["사용자", "가맹점", "P_AMT", "일시", "위반사유", "주요위반유형(배타)", "문서제목", "카드사용자명(괄호)"]
st.dataframe(df_user[DISPLAY_COLS], use_container_width=True, height=360)

st.markdown("---")

# =========================================================
# 위반 유형별 탭 + 다운로드
# =========================================================
def download_block(d: pd.DataFrame, key: str):
    b1, b2 = st.columns(2)
    with b1:
        st.download_button(
            "CSV 다운로드(현재 탭)",
            data=d.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            key=f"dl_csv_{key}",
            use_container_width=True
        )
    with b2:
        st.download_button(
            "엑셀 다운로드(현재 탭)",
            data=to_excel_bytes(d),
            file_name=f"{key}.xlsx",
            key=f"dl_xlsx_{key}",
            use_container_width=True
        )

tabs = st.tabs(["전체(위반)", "심야", "주말", "공휴일", "제한업종", "배타분류(합계일치)"])

with tabs[0]:
    d = viol.copy()
    download_block(d[DISPLAY_COLS], "all_violations")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[1]:
    d = df[df["F_NIGHT"]].copy()
    download_block(d[DISPLAY_COLS], "late_night")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[2]:
    d = df[df["F_WEEKEND"]].copy()
    download_block(d[DISPLAY_COLS], "weekend")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[3]:
    d = df[df["F_HOLIDAY"]].copy()
    download_block(d[DISPLAY_COLS], "public_holiday")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[4]:
    d = df[df["F_RESTRICT"]].copy()
    download_block(d[DISPLAY_COLS], "restricted")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[5]:
    d = viol.sort_values(["주요위반유형(배타)", "일시"]).copy()
    download_block(d[DISPLAY_COLS], "exclusive")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

st.caption("엑셀 다운로드: openpyxl 필요 | 공휴일 판정: holidays 필요")
