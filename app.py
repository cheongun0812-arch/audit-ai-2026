import streamlit as st
import pandas as pd
import re
from datetime import date
from io import BytesIO
import matplotlib.pyplot as plt

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.7 FINAL (KR)"

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
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="법인카드 운영기준 위반 점검 (최종)",
    layout="wide"
)

# =========================================================
# TEXT UTILS
# =========================================================
def normalize_text(x) -> str:
    """가맹점/제목 문자열 정규화: 소문자/특수문자 제거"""
    if pd.isna(x):
        return ""
    x = str(x).lower()
    x = re.sub(r"[^a-z0-9가-힣]", "", x)
    return x

def extract_parentheses_name(x: str) -> str:
    """BC카드(박성진) -> 박성진 / BC Card (Seongjin Park) -> Seongjin Park"""
    if pd.isna(x):
        return ""
    m = re.search(r"\((.*?)\)", str(x))
    return m.group(1).strip() if m else ""

# =========================================================
# AUDIT ENGINE
# =========================================================
class AuditEngineFinal:
    @staticmethod
    def map_columns(df: pd.DataFrame) -> dict:
        """RAW DATA 컬럼 자동 매핑"""
        def pick(*cands):
            for c in cands:
                if c in df.columns:
                    return c
            return None

        return {
            "user": pick("사용자", "성명", "사원명", "User"),
            "merchant": pick("거래처명", "거래처", "가맹점", "가맹점명", "Customer name"),
            "amount": pick("금액", "금액1", "금액.1", "금액(원)", "이용금액", "승인금액", "결제금액", "Amount", "Amount 1"),
            "datetime": pick("승인일시", "일시", "Approval date", "거래일시", "결제일시", "승인일자"),
            "title": pick("문서 내용(제목)", "문서 내용", "문서내용(제목)", "Document content (title)"),
            "card_name": pick("카드명", "Card name"),
        }

    @staticmethod
    def analyze(
        df_raw: pd.DataFrame,
        night_start: int = 23,
        night_end: int = 6,
        include_weekend: bool = True,
        include_public_holiday: bool = True,
        restricted_explicit=None,
        exclude_bar_club: bool = True,
        exclude_branch_store: bool = True,
        exclude_vehicle_from_night: bool = True,
        vehicle_keywords=None,
    ) -> tuple[pd.DataFrame, dict]:
        df = df_raw.copy()
        mapping = AuditEngineFinal.map_columns(df)

        if not (mapping["merchant"] and mapping["amount"] and mapping["datetime"]):
            raise KeyError(
                "필수 컬럼(거래처명/가맹점, 금액, 승인일시/일시)을 찾지 못했습니다.\n"
                f"현재 컬럼: {list(df.columns)}"
            )

        # 표준 컬럼 생성
        df["사용자"] = df[mapping["user"]].astype(str) if mapping["user"] else "미지정"
        df["가맹점"] = df[mapping["merchant"]].astype(str)

        df["일시"] = pd.to_datetime(df[mapping["datetime"]], errors="coerce")
        df["DATE"] = df["일시"].dt.date
        df["HOUR"] = df["일시"].dt.hour

        # 금액
        df["P_AMT"] = pd.to_numeric(
            df[mapping["amount"]].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
            errors="coerce"
        ).fillna(0).astype(int)

        # (선택) 카드명 괄호 안 사용자명 추출
        if mapping["card_name"]:
            df["카드사용자명(괄호)"] = df[mapping["card_name"]].astype(str).apply(extract_parentheses_name)
        else:
            df["카드사용자명(괄호)"] = ""

        # 제목
        if mapping["title"]:
            df["문서제목"] = df[mapping["title"]].astype(str)
        else:
            df["문서제목"] = ""

        # -------------------------
        # 차량비 판정 (심야 위반 제외용)
        # -------------------------
        if vehicle_keywords is None:
            vehicle_keywords = [
                "차량", "차량운전비", "유류", "주유", "하이패스", "톨게이트", "통행료",
                "주차", "주차비", "렌터카", "렌트카", "대리운전", "택시", "카카오t", "카카오택시",
                "고속도로", "세차", "정비", "차량수선"
            ]
        vehicle_keywords_norm = [normalize_text(k) for k in vehicle_keywords]

        def is_vehicle_row(row) -> bool:
            hay = " ".join([str(row.get("사용자", "")), str(row.get("가맹점", "")), str(row.get("문서제목", ""))])
            n = normalize_text(hay)
            return any(k in n for k in vehicle_keywords_norm)

        df["F_VEHICLE"] = df.apply(is_vehicle_row, axis=1)

        # -------------------------
        # 위반 룰: 심야/주말/공휴일
        # -------------------------
        # 심야 23:00:00 ~ 06:00:00
        df["F_NIGHT"] = df["HOUR"].apply(lambda h: (h >= night_start or h < night_end) if pd.notna(h) else False)

        # 차량비는 심야 위반에서 제외 (요청사항)
        if exclude_vehicle_from_night:
            df.loc[df["F_VEHICLE"] == True, "F_NIGHT"] = False

        # 주말(토/일)
        df["F_WEEKEND"] = (df["일시"].dt.weekday >= 5) if include_weekend else False

        # 공휴일(법정/대체 포함)
        if include_public_holiday and HAS_HOLIDAYS:
            years = sorted({d.year for d in df["DATE"].dropna() if isinstance(d, date)})
            kr = holidays.KR(years=years)  # type: ignore
            df["F_HOLIDAY"] = df["DATE"].isin(kr)
        else:
            df["F_HOLIDAY"] = False

        # -------------------------
        # 제한/유흥 업종 판정
        # - 'OO bar', 'OO club'은 유흥 아님 → 전부 제외
        # - 'OO지점/OO점/branch' 표기 거래처는 제한업종에서 제외
        # - 첨부 데이터 기준: "명시적 유흥" 키워드만 제한으로 반영
        # -------------------------
        if restricted_explicit is None:
            restricted_explicit = [
                "유흥주점", "단란주점", "나이트클럽", "안마시술소", "안마", "마사지"
            ]
        restricted_explicit_norm = [normalize_text(k) for k in restricted_explicit]

        def is_restricted(merchant_name: str) -> bool:
            n = normalize_text(merchant_name)

            if exclude_branch_store:
                if ("지점" in n) or ("branch" in n) or n.endswith("점"):
                    return False

            if exclude_bar_club:
                if any(k in n for k in ["bar", "club", "클럽", "pub", "lounge"]):
                    return False

            return any(k in n for k in restricted_explicit_norm)

        df["F_RESTRICT"] = df["가맹점"].apply(is_restricted)

        # -------------------------
        # 위반 사유(한국어)
        # -------------------------
        def reason(row):
            r = []
            if bool(row.get("F_NIGHT", False)):
                r.append("🌙 심야(23~06)")
            if bool(row.get("F_WEEKEND", False)):
                r.append("📅 휴무일(주말)")
            if bool(row.get("F_HOLIDAY", False)):
                r.append("🎌 공휴일(법정/대체)")
            if bool(row.get("F_RESTRICT", False)):
                r.append("🚫 제한업종(명시적 유흥)")
            return " / ".join(r)

        df["위반사유"] = df.apply(reason, axis=1)
        df["운영기준위반"] = df["위반사유"] != ""

        features = {
            "mapping": mapping,
            "night_start": night_start,
            "night_end": night_end,
            "restricted_explicit": restricted_explicit,
            "vehicle_keywords": vehicle_keywords,
        }
        return df, features


# =========================================================
# UI - SIDEBAR
# =========================================================
st.sidebar.title("RAW DATA 업로드")
uploaded = st.sidebar.file_uploader(
    "지출결의현황.xlsx (또는 CSV)",
    type=["xlsx", "csv"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("운영기준 설정")

night_start, night_end = st.sidebar.select_slider(
    "심야 시간대 (23:00~06:00)",
    options=list(range(0, 24)),
    value=(23, 6),
    help="심야 위반 기준: 23:00:00 ~ 06:00:00"
)

include_weekend = st.sidebar.checkbox("휴무일(주말) 포함(토/일)", value=True)
include_public_holiday = st.sidebar.checkbox("공휴일(법정/대체) 포함", value=True)
exclude_vehicle_from_night = st.sidebar.checkbox("차량비는 심야 위반에서 제외", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("제한업종(명시적 유흥만)")
restricted_text = st.sidebar.text_area(
    "명시적 유흥 키워드(줄바꿈 또는 쉼표로 구분)",
    value="유흥주점\n단란주점\n나이트클럽\n안마시술소\n안마\n마사지",
    height=120
)
restricted_explicit = [x.strip() for x in re.split(r"[,\n]+", restricted_text) if x.strip()]

st.sidebar.subheader("차량비 키워드(심야 제외용)")
vehicle_text = st.sidebar.text_area(
    "차량비 키워드(줄바꿈 또는 쉼표로 구분)",
    value="차량운전비,차량,유류,주유,하이패스,통행료,주차,주차비,택시,대리운전,카카오T,렌터카,고속도로,정비,세차",
    height=90
)
vehicle_keywords = [x.strip() for x in re.split(r"[,\n]+", vehicle_text) if x.strip()]

if not HAS_HOLIDAYS and include_public_holiday:
    st.sidebar.warning("공휴일 판정을 위해 `holidays` 패키지 설치가 필요합니다. (현재 비활성)")

# =========================================================
# MAIN
# =========================================================
st.markdown("## 🧾 법인카드 운영기준 위반 점검 (최종)")
st.caption(f"BUILD: {BUILD} | 공휴일 판정: {'활성' if HAS_HOLIDAYS else '비활성(holidays 미설치)'}")

if not uploaded:
    st.info("왼쪽에서 RAW DATA(지출결의현황.xlsx 또는 CSV)를 업로드하세요.")
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

# ANALYZE
try:
    df, features = AuditEngineFinal.analyze(
        df_raw,
        night_start=night_start,
        night_end=night_end,
        include_weekend=include_weekend,
        include_public_holiday=include_public_holiday,
        restricted_explicit=restricted_explicit,
        exclude_bar_club=True,
        exclude_branch_store=True,
        exclude_vehicle_from_night=exclude_vehicle_from_night,
        vehicle_keywords=vehicle_keywords,
    )
except Exception as e:
    st.error(str(e))
    st.stop()

# =========================================================
# SUMMARY BOARD
# =========================================================
total_viol = int(df["운영기준위반"].sum())
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("🚨 전체 위반", total_viol)
c2.metric("🌙 심야", int(df["F_NIGHT"].sum()))
c3.metric("📅 주말", int(df["F_WEEKEND"].sum()))
c4.metric("🎌 공휴일", int(df["F_HOLIDAY"].sum()))
c5.metric("🚫 제한업종", int(df["F_RESTRICT"].sum()))
c6.metric("🚗 차량비(심야 제외)", int(df["F_VEHICLE"].sum()))

st.markdown("---")

# =========================================================
# USER(S열) 기준 상세 검토
# =========================================================
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

left_u, right_u = st.columns([2, 1], gap="large")
with left_u:
    st.dataframe(user_summary, use_container_width=True, height=260)

with right_u:
    st.markdown("#### 📊 TOP 사용자 그래프")
    topN = st.slider("TOP N", 5, 30, 10, 1)
    top = user_summary.head(topN).sort_values("총위반건수", ascending=True)
    if len(top) > 0:
        fig, ax = plt.subplots()
        ax.barh(top["사용자"].astype(str), top["총위반건수"])
        ax.set_xlabel("위반 건수")
        ax.set_ylabel("사용자")
        ax.set_title("사용자별 위반 TOP")
        st.pyplot(fig, clear_figure=True)
    else:
        st.info("위반 데이터가 없습니다.")

st.markdown("---")

# 사용자 선택 상세
all_users = user_summary["사용자"].astype(str).tolist()
pick_user = st.selectbox("상세 확인할 사용자 선택", options=(all_users if all_users else ["(위반 없음)"]), index=0)

if all_users:
    df_user = viol[viol["사용자"].astype(str) == str(pick_user)].copy()
    st.markdown(f"### 🔎 {pick_user} - 위반 상세")
else:
    df_user = viol.iloc[0:0].copy()

# 사용자별 유형 분포 그래프
if not df_user.empty:
    counts = {
        "심야": int(df_user["F_NIGHT"].sum()),
        "주말": int(df_user["F_WEEKEND"].sum()),
        "공휴일": int(df_user["F_HOLIDAY"].sum()),
        "제한업종": int(df_user["F_RESTRICT"].sum()),
    }
    fig2, ax2 = plt.subplots()
    ax2.bar(list(counts.keys()), list(counts.values()))
    ax2.set_title("선택 사용자 위반 유형 분포")
    ax2.set_ylabel("건수")
    st.pyplot(fig2, clear_figure=True)

# =========================================================
# DOWNLOAD + TABS
# =========================================================
DISPLAY_COLS = ["사용자", "가맹점", "P_AMT", "일시", "위반사유", "문서제목", "카드사용자명(괄호)"]

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

tabs = st.tabs(["전체(위반)", "🌙 심야", "📅 주말", "🎌 공휴일", "🚫 제한업종(명시적 유흥)"])

with tabs[0]:
    st.subheader("전체 위반 내역")
    d = filter_view("all")
    download_buttons(d, "all")
    st.dataframe(d[DISPLAY_COLS], use_container_width=True, height=520)

with tabs[1]:
    st.subheader("심야 위반 내역(23:00~06:00)")
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

st.markdown("---")
st.caption("※ 엑셀 다운로드: openpyxl 필요 / 공휴일 판정: holidays 필요")
