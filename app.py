import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from io import BytesIO

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.5 FINAL"

# =========================================================
# Public holidays (KR)
# =========================================================
HAS_HOLIDAYS = True
try:
    import holidays
except Exception:
    HAS_HOLIDAYS = False

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Corporate Card Compliance Audit v6.5",
    layout="wide"
)

# =========================================================
# UI HELPERS
# =========================================================
def panel(title, sub=None):
    st.markdown(f"### {title}")
    if sub:
        st.caption(sub)

# =========================================================
# AUDIT ENGINE v6.5
# =========================================================
class AuditEngineV6_5:

    @staticmethod
    def normalize_text(x):
        if pd.isna(x):
            return ""
        x = str(x).lower()
        x = re.sub(r"[^a-z0-9가-힣]", "", x)
        return x

    @staticmethod
    def run_card_audit(df):
        df = df.copy()

        # ---------- column auto mapping ----------
        def pick(*cands):
            for c in cands:
                if c in df.columns:
                    return c
            return None

        u_src = pick("사용자", "성명", "사원명", "User")
        m_src = pick("가맹점", "가맹점명", "거래처명", "Customer name")
        a_src = pick("금액", "금액.1", "이용금액", "승인금액", "Amount")
        t_src = pick("일시", "승인일시", "Approval date", "거래일시")

        if not (m_src and a_src and t_src):
            raise KeyError("필수 컬럼(가맹점/금액/일시)을 찾지 못했습니다.")

        df["사용자"] = df[u_src].astype(str) if u_src else "미지정"
        df["가맹점"] = df[m_src].astype(str)
        df["일시"] = pd.to_datetime(df[t_src], errors="coerce")

        # ---------- amount ----------
        df["P_AMT"] = pd.to_numeric(
            df[a_src].astype(str).str.replace(r"[^0-9]", "", regex=True),
            errors="coerce"
        ).fillna(0).astype(int)

        df["HOUR"] = df["일시"].dt.hour
        df["DATE"] = df["일시"].dt.date

        # ---------- rules ----------
        df["F_NIGHT"] = df["HOUR"].apply(lambda h: (h >= 23 or h <= 6) if pd.notna(h) else False)
        df["F_WEEKEND"] = df["일시"].dt.weekday >= 5

        if HAS_HOLIDAYS:
            years = sorted({d.year for d in df["DATE"].dropna()})
            kr_holidays = holidays.KR(years=years)
            df["F_HOLIDAY"] = df["DATE"].isin(kr_holidays)
        else:
            df["F_HOLIDAY"] = False

        # ---------- restricted industries ----------
        RESTRICTED = [
            "주점", "유흥", "노래방", "클럽", "bar", "lounge",
            "마사지", "안마", "사우나", "스파",
            "상품권", "면세", "성인"
        ]

        EXCEPTIONS = ["편의점", "구내식당", "공공기관", "차량운전비"]

        def is_restricted(name):
            n = AuditEngineV6_5.normalize_text(name)
            for ex in EXCEPTIONS:
                if ex in n:
                    return False
            return any(k in n for k in RESTRICTED)

        df["F_RESTRICT"] = df["가맹점"].apply(is_restricted)

        # ---------- violation reason ----------
        def reason(row):
            r = []
            if row.F_NIGHT: r.append("🌙 Late Night")
            if row.F_WEEKEND: r.append("📅 Weekend")
            if row.F_HOLIDAY: r.append("🎌 Public Holiday")
            if row.F_RESTRICT: r.append("🚫 Restricted Industry")
            return " / ".join(r)

        df["violation_reason"] = df.apply(reason, axis=1)
        df["IS_VIOLATION"] = df["violation_reason"] != ""

        return df


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("Upload RAW DATA")
uploaded = st.sidebar.file_uploader(
    "Upload 지출결의현황.xlsx",
    type=["xlsx", "csv"]
)

if not uploaded:
    st.info("📂 지출결의현황.xlsx 파일을 업로드하세요.")
    st.stop()

# =========================================================
# LOAD DATA
# =========================================================
if uploaded.name.endswith(".xlsx"):
    df_raw = pd.read_excel(uploaded)
else:
    df_raw = pd.read_csv(uploaded)

df = AuditEngineV6_5.run_card_audit(df_raw)

# =========================================================
# DASHBOARD
# =========================================================
panel("Violation Summary Board", "업로드 즉시 위반 현황 확인")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🚨 Total", int(df.IS_VIOLATION.sum()))
c2.metric("🌙 Late Night", int(df.F_NIGHT.sum()))
c3.metric("📅 Weekend", int(df.F_WEEKEND.sum()))
c4.metric("🎌 Holiday", int(df.F_HOLIDAY.sum()))
c5.metric("🚫 Restricted", int(df.F_RESTRICT.sum()))

# =========================================================
# FILTER + DOWNLOAD
# =========================================================
def view(df, key):
    return df[df[key]] if key != "ALL" else df[df.IS_VIOLATION]

def table_block(title, df_view, key):
    st.subheader(title)

    csv = df_view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download CSV",
        csv,
        file_name=f"{key}.csv",
        key=f"csv_{key}"
    )

    st.dataframe(
        df_view[["사용자", "가맹점", "P_AMT", "일시", "violation_reason"]],
        use_container_width=True
    )

# =========================================================
# TABS
# =========================================================
tab_all, tab_night, tab_weekend, tab_holiday, tab_rest = st.tabs(
    ["All", "🌙 Late Night", "📅 Weekend", "🎌 Holiday", "🚫 Restricted"]
)

with tab_all:
    table_block("All Violations", view(df, "ALL"), "all")

with tab_night:
    table_block("Late Night", view(df, "F_NIGHT"), "night")

with tab_weekend:
    table_block("Weekend", view(df, "F_WEEKEND"), "weekend")

with tab_holiday:
    table_block("Public Holiday", view(df, "F_HOLIDAY"), "holiday")

with tab_rest:
    table_block("Restricted Industries", view(df, "F_RESTRICT"), "restricted")

st.caption("AuditEngine v6.5 | Corporate Card Compliance")
