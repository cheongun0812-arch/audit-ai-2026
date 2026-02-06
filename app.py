import streamlit as st
import pandas as pd
import re
from datetime import date, time
from io import BytesIO
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.10 FINAL (KR) - 배타우선순위 설정 + 한글폰트 고정 + 심야(23:00:00~06:00:00)"

# =========================================================
# 대한민국 공휴일(법정/대체 포함) - holidays 라이브러리 사용
#   requirements.txt: holidays, openpyxl
# =========================================================
HAS_HOLIDAYS = True
try:
    import holidays  # type: ignore
except Exception:
    HAS_HOLIDAYS = False

# =========================================================
# Matplotlib 한글 폰트(깨짐 방지)
# =========================================================
def set_korean_font() -> str | None:
    # Streamlit Cloud/리눅스에서도 흔히 있는 순서로 시도
    preferred = [
        "NanumGothic",
        "NanumBarunGothic",
        "NanumSquare",
        "UnDotum",
        "Noto Sans CJK KR",
        "Noto Sans CJK",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in preferred:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    # fallback: 기본 폰트 사용(한글 깨질 수 있음)
    matplotlib.rcParams["axes.unicode_minus"] = False
    return None

KOR_FONT = set_korean_font()

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="법인카드 운영기준 위반 점검 (최종 v6.10)",
    layout="wide"
)

# =========================================================
# TEXT UTILS
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

# =========================================================
# AUDIT ENGINE
# =========================================================
class AuditEngineFinal:
    @staticmethod
    def map_columns(df: pd.DataFrame) -> dict:
        def pick(*cands):
            for c in cands:
                if c in df.columns:
                    return c
            return None

        date_col = pick("승인일자", "Approval date", "거래일자", "사용일자", "결제일자", "일자", "날짜")
        time_col = pick("승인일시", "승인시간", "시간", "Approval time", "거래시간", "결제시간")
        datetime_col = pick("거래일시", "결제일시", "일시", "Approval datetime", "승인일시(일시)")

        return {
            "user": pick("사용자", "성명", "사원명", "User"),
            "merchant": pick("거래처명", "거래처", "가맹점", "가맹점명", "Customer name"),
            "amount": pick("금액", "금액1", "금액.1", "금액(원)", "이용금액", "승인금액", "결제금액", "Amount", "Amount 1"),
            "date": date_col,
            "time": time_col,
            "datetime": datetime_col,
            "title": pick("문서 내용(제목)", "문서 내용", "문서내용(제목)", "Document content (title)"),
            "card_name": pick("카드명", "Card name"),
        }

    @staticmethod
    def build_datetime(df: pd.DataFrame, mapping: dict) -> pd.Series:
        d_col = mapping.get("date")
        t_col = mapping.get("time")
        dt_col = mapping.get("datetime")

        if d_col and t_col and d_col in df.columns and t_col in df.columns:
            return combine_date_time(df[d_col], df[t_col])

        if dt_col and dt_col in df.columns:
            return pd.to_datetime(df[dt_col], errors="coerce")

        if d_col and d_col in df.columns:
            return pd.to_datetime(df[d_col], errors="coerce")

        return pd.to_datetime(pd.Series([pd.NaT] * len(df)), errors="coerce")

    @staticmethod
    def analyze(
        df_raw: pd.DataFrame,
        include_weekend: bool,
        include_public_holiday: bool,
        restricted_explicit: list[str],
        vehicle_keywords: list[str],
        exclude_vehicle_from_night: bool,
        exclude_bar_club: bool,
        exclude_branch_store: bool,
        exclusive_priority: list[str],
    ) -> tuple[pd.DataFrame, dict]:
        df = df_raw.copy()
        mapping = AuditEngineFinal.map_columns(df)

        if not (mapping["merchant"] and mapping["amount"]):
            raise KeyError(
                "필수 컬럼(거래처명/가맹점, 금액)을 찾지 못했습니다.\n"
                f"현재 컬럼: {list(df.columns)}"
            )

        df["사용자"] = df[mapping["user"]].astype(str) if mapping["user"] else "미지정"
        df["가맹점"] = df[mapping["merchant"]].astype(str)

        df["일시"] = AuditEngineFinal.build_datetime(df, mapping)

        if mapping["title"] and mapping["title"] in df.columns:
            df["문서제목"] = df[mapping["title"]].astype(str)
        else:
            df["문서제목"] = ""

        if mapping["card_name"] and mapping["card_name"] in df.columns:
            df["카드사용자명(괄호)"] = df[mapping["card_name"]].astype(str).apply(extract_parentheses_name)
        else:
            df["카드사용자명(괄호)"] = ""

        df["P_AMT"] = pd.to_numeric(
            df[mapping["amount"]].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
            errors="coerce"
        ).fillna(0).astype(int)

        # ---- 일시 안전장치 ----
        valid_ratio = df["일시"].notna().mean()
        if valid_ratio < 0.5:
            raise ValueError("일시 파싱 실패(유효 일시 비율 < 50%). 승인일자/승인일시(시간) 또는 거래일시 컬럼을 확인하세요.")

        hour0_ratio = (df["일시"].dt.hour.fillna(-1).eq(0)).mean()
        if hour0_ratio > 0.85 and not mapping.get("time"):
            raise ValueError(
                "일시에 시간이 거의 없습니다(대부분 00:00:00).\n"
                "승인일자(날짜만)로 분석되고 있을 가능성이 큽니다.\n"
                "시간이 포함된 '거래일시/결제일시/일시' 컬럼 또는 '승인일시(시간)' 컬럼을 확인하세요."
            )

        df["DATE"] = df["일시"].dt.date

        # ---- 차량비 ----
        vkeys = [normalize_text(k) for k in vehicle_keywords]

        def is_vehicle_row(row) -> bool:
            hay = " ".join([str(row.get("사용자", "")), str(row.get("가맹점", "")), str(row.get("문서제목", ""))])
            n = normalize_text(hay)
            return any(k in n for k in vkeys)

        df["F_VEHICLE"] = df.apply(is_vehicle_row, axis=1)

        # =====================================================
        # ✅ 기준 재설정(고정):
        # 심야 23:00:00 ~ 06:00:00  (06:00:00 포함)
        # =====================================================
        tseries = df["일시"].dt.time
        late_start = time(23, 0, 0)
        late_end = time(6, 0, 0)
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

        # 제한업종(명시적 유흥만) + bar/club/지점 제외
        rkeys = [normalize_text(k) for k in restricted_explicit]

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
            if bool(row.get("F_NIGHT", False)): r.append("🌙 심야(23:00~06:00)")
            if bool(row.get("F_WEEKEND", False)): r.append("📅 휴무일(주말)")
            if bool(row.get("F_HOLIDAY", False)): r.append("🎌 공휴일(법정/대체)")
            if bool(row.get("F_RESTRICT", False)): r.append("🚫 제한업종(명시적 유흥)")
            return " / ".join(r)

        df["위반사유"] = df.apply(reason, axis=1)
        df["운영기준위반"] = df["위반사유"] != ""

        # ---- 배타적 분류(합계 일치) ----
        # exclusive_priority 예: ["심야","공휴일","주말","제한업종"]
        def primary_type(row):
            for p in exclusive_priority:
                if p == "심야" and row["F_NIGHT"]:
                    return "심야"
                if p == "주말" and row["F_WEEKEND"]:
                    return "주말"
                if p == "공휴일" and row["F_HOLIDAY"]:
                    return "공휴일"
                if p == "제한업종" and row["F_RESTRICT"]:
                    return "제한업종"
            return ""

        df["주요위반유형(배타)"] = df.apply(primary_type, axis=1)

        features = {
            "mapping": mapping,
            "late_start": "23:00:00",
            "late_end": "06:00:00",
            "exclusive_priority": exclusive_priority,
            "kor_font": KOR_FONT,
        }
        return df, features


# =========================================================
# UI
# =========================================================
st.sidebar.title("RAW DATA 업로드")
uploaded = st.sidebar.file_uploader("지출결의현황.xlsx (또는 CSV)", type=["xlsx", "csv"])

st.sidebar.markdown("---")
st.sidebar.subheader("운영기준(고정)")
st.sidebar.info("✅ 심야: 23:00:00 ~ 06:00:00\n✅ 주말: 토/일\n✅ 공휴일: 법정/대체(holidays.KR)")

include_weekend = st.sidebar.checkbox("휴무일(주말) 포함(토/일)", value=True)
include_public_holiday = st.sidebar.checkbox("공휴일(법정/대체) 포함", value=True)
exclude_vehicle_from_night = st.sidebar.checkbox("차량비는 심야 위반에서 제외", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("배타적 분류(합계 일치) 우선순위")
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
restricted_text = st.sidebar.text_area(
    "제한업종(명시적 유흥 키워드)",
    value="유흥주점\n단란주점\n나이트클럽\n안마시술소\n안마\n마사지",
    height=120,
)
restricted_explicit = [x.strip() for x in re.split(r"[,\n]+", restricted_text) if x.strip()]

vehicle_text = st.sidebar.text_area(
    "차량비 키워드(심야 제외용)",
    value="차량운전비,차량,유류,주유,하이패스,통행료,주차,주차비,택시,대리운전,카카오T,렌터카,고속도로,정비,세차",
    height=90,
)
vehicle_keywords = [x.strip() for x in re.split(r"[,\n]+", vehicle_text) if x.strip()]

if not HAS_HOLIDAYS and include_public_holiday:
    st.sidebar.warning("공휴일 판정을 위해 `holidays` 설치가 필요합니다. (현재 비활성)")

st.markdown("## 🧾 법인카드 운영기준 위반 점검 (최종 v6.10)")
st.caption(f"BUILD: {BUILD} | 공휴일: {'활성' if HAS_HOLIDAYS else '비활성'} | 그래프폰트: {KOR_FONT or '기본(일부 깨질 수 있음)'}")

if not uploaded:
    st.info("왼쪽에서 RAW DATA를 업로드하세요.")
    st.stop()

# LOAD
if uploaded.name.lower().endswith(".xlsx"):
    df_raw = pd.read_excel(uploaded)
else:
    try:
        df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
    except Exception:
        df_raw = pd.read_csv(uploaded)

# ANALYZE
df, features = AuditEngineFinal.analyze(
    df_raw=df_raw,
    include_weekend=include_weekend,
    include_public_holiday=include_public_holiday,
    restricted_explicit=restricted_explicit,
    vehicle_keywords=vehicle_keywords,
    exclude_vehicle_from_night=exclude_vehicle_from_night,
    exclude_bar_club=True,
    exclude_branch_store=True,
    exclusive_priority=exclusive_priority,
)

with st.expander("🔎 컬럼 인식 결과(자동 매핑)", expanded=False):
    st.json(features["mapping"])

st.markdown("### ✅ 집계 기준 안내(신뢰용)")
st.write(
    "- **전체 위반(유니크)**: 위반사유가 1개 이상인 행의 개수\n"
    "- **유형별(심야/주말/공휴일/제한업종)**: 중복 포함 (한 행이 여러 기준에 동시에 걸릴 수 있음)\n"
    "- **배타적 분류(합계 일치)**: 우선순위에 따라 한 행당 1개의 유형만 부여 → 합계가 전체 위반과 1:1로 일치"
)

# SUMMARY
total_unique = int(df["운영기준위반"].sum())
night_cnt = int(df["F_NIGHT"].sum())
weekend_cnt = int(df["F_WEEKEND"].sum())
holiday_cnt = int(df["F_HOLIDAY"].sum())
restrict_cnt = int(df["F_RESTRICT"].sum())
vehicle_cnt = int(df["F_VEHICLE"].sum())
dup_rows = int((df[["F_NIGHT","F_WEEKEND","F_HOLIDAY","F_RESTRICT"]].sum(axis=1) > 1).sum())

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("🚨 전체 위반(유니크)", total_unique)
c2.metric("🌙 심야(중복포함)", night_cnt)
c3.metric("📅 주말(중복포함)", weekend_cnt)
c4.metric("🎌 공휴일(중복포함)", holiday_cnt)
c5.metric("🚫 제한업종(중복포함)", restrict_cnt)
c6.metric("🚗 차량비(심야 제외)", vehicle_cnt)
c7.metric("🔁 복수 위반 행", dup_rows)

exclusive = df[df["운영기준위반"]].copy()
exclusive_counts = exclusive["주요위반유형(배타)"].value_counts().reindex(["심야","주말","공휴일","제한업종"]).fillna(0).astype(int)

st.markdown("#### 📌 배타적 분류(합계 일치) — 현재 우선순위")
st.write(" > ".join(exclusive_priority))

b1, b2, b3, b4 = st.columns(4)
b1.metric("🌙 심야(배타)", int(exclusive_counts.get("심야", 0)))
b2.metric("📅 주말(배타)", int(exclusive_counts.get("주말", 0)))
b3.metric("🎌 공휴일(배타)", int(exclusive_counts.get("공휴일", 0)))
b4.metric("🚫 제한업종(배타)", int(exclusive_counts.get("제한업종", 0)))

st.markdown("---")

# 사용자별 요약
st.subheader("👤 사용자 기준 상세 위반 검토")
viol = df[df["운영기준위반"]].copy()

user_summary = (
    viol.groupby("사용자", as_index=False)
    .agg(
        총위반건수=("운영기준위반", "count"),
        심야=("F_NIGHT", "sum"),
        주말=("F_WEEKEND", "sum"),
        공휴일=("F_HOLIDAY", "sum"),
        제한업종=("F_RESTRICT", "sum"),
        총금액=("P_AMT", "sum"),
    )
    .sort_values("총위반건수", ascending=False)
)

left, right = st.columns([2, 1], gap="large")
with left:
    st.dataframe(user_summary, use_container_width=True, height=260)

with right:
    st.markdown("#### 📊 TOP 사용자 그래프(총위반건수)")
    topN = st.slider("TOP N", 5, 30, 10, 1)
    top = user_summary.head(topN).sort_values("총위반건수", ascending=True)
    if len(top) > 0:
        fig, ax = plt.subplots()
        ax.barh(top["사용자"].astype(str), top["총위반건수"])
        ax.set_xlabel("위반 건수(유니크)")
        ax.set_ylabel("사용자")
        ax.set_title("사용자별 위반 TOP")
        ax.grid(axis="x", alpha=0.2)
        st.pyplot(fig, clear_figure=True)
    else:
        st.info("위반 데이터가 없습니다.")

users = user_summary["사용자"].astype(str).tolist()
pick_user = st.selectbox("상세 확인할 사용자 선택", options=(users if users else ["(위반 없음)"]), index=0)
df_user = viol[viol["사용자"].astype(str) == str(pick_user)].copy() if users else viol.iloc[0:0].copy()

if not df_user.empty:
    st.markdown(f"### 🔎 {pick_user} - 위반 상세")
    counts = {
        "심야": int(df_user["F_NIGHT"].sum()),
        "주말": int(df_user["F_WEEKEND"].sum()),
        "공휴일": int(df_user["F_HOLIDAY"].sum()),
        "제한업종": int(df_user["F_RESTRICT"].sum()),
    }
    fig2, ax2 = plt.subplots()
    ax2.bar(list(counts.keys()), list(counts.values()))
    ax2.set_title("선택 사용자 위반 유형 분포(중복 포함)")
    ax2.set_ylabel("건수")
    ax2.grid(axis="y", alpha=0.2)
    st.pyplot(fig2, clear_figure=True)

# 탭 + 다운로드
DISPLAY_COLS = ["사용자", "가맹점", "P_AMT", "일시", "위반사유", "주요위반유형(배타)", "문서제목", "카드사용자명(괄호)"]

def filter_view(mode: str) -> pd.DataFrame:
    if mode == "all":
        return df[df["운영기준위반"]].copy()
    if mode == "night":
        return df[df["F_NIGHT"]].copy()
    if mode == "weekend":
        return df[df["F_WEEKEND"]].copy()
    if mode == "holiday":
        return df[df["F_HOLIDAY"]].copy()
    if mode == "restricted":
        return df[df["F_RESTRICT"]].copy()
    if mode == "exclusive":
        return df[df["운영기준위반"]].copy().sort_values(["주요위반유형(배타)", "일시"])
    return df.iloc[0:0].copy()

def download_buttons(d: pd.DataFrame, key: str):
    b1, b2 = st.columns(2)
    with b1:
        st.download_button(
            label="⬇️ CSV 다운로드(현재 탭)",
            data=d.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            key=f"dl_csv_{key}",
            use_container_width=True,
        )
    with b2:
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            d.to_excel(writer, index=False, sheet_name="data")
        st.download_button(
            label="⬇️ 엑셀 다운로드(현재 탭)",
            data=out.getvalue(),
            file_name=f"{key}.xlsx",
            key=f"dl_xlsx_{key}",
            use_container_width=True,
        )

tabs = st.tabs(["전체(위반)", "🌙 심야", "📅 주말", "🎌 공휴일", "🚫 제한업종", "✅ 배타적 분류(합계일치)"])

with tabs[0]:
    st.subheader("전체 위반 내역(유니크)")
    d = filter_view("all")
    download_buttons(d, "all")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[1]:
    st.subheader("심야 위반 내역(23:00:00~06:00:00)")
    st.caption("※ 차량비(F_VEHICLE=True)는 심야 위반에서 제외 처리됩니다.")
    d = filter_view("night")
    download_buttons(d, "late_night")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[2]:
    st.subheader("휴무일(주말: 토/일) 위반 내역")
    d = filter_view("weekend")
    download_buttons(d, "weekend")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[3]:
    st.subheader("공휴일(법정/대체) 위반 내역")
    d = filter_view("holiday")
    download_buttons(d, "holiday")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[4]:
    st.subheader("제한업종 위반 내역(명시적 유흥만)")
    st.caption("※ 'OO bar', 'OO club', 'OO지점/OO점/branch' 표기 거래처는 제한업종에서 제외합니다.")
    d = filter_view("restricted")
    download_buttons(d, "restricted")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[5]:
    st.subheader("배타적 분류(중복 제거) — 합계가 전체 위반과 정확히 일치")
    st.caption("사이드바에서 우선순위를 기관 기준으로 선택할 수 있습니다.")
    d = filter_view("exclusive")
    download_buttons(d, "exclusive_breakdown")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

st.markdown("---")
st.caption("※ 엑셀 다운로드: openpyxl 필요 / 공휴일 판정: holidays 필요")
