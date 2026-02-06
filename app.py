import streamlit as st
import pandas as pd
import re
from datetime import date
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
    import holidays  # pip install holidays
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
    def run_card_audit(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ---------- column auto mapping ----------
        def pick(*cands):
            for c in cands:
                if c in df.columns:
                    return c
            return None

        u_src = pick("사용자", "성명", "사원명", "User")
        m_src = pick("가맹점", "가맹점명", "거래처명", "Customer name")
        a_src = pick("금액", "금액.1", "이용금액", "승인금액", "Amount", "결제금액")
        t_src = pick("일시", "승인일시", "Approval date", "거래일시", "결제일시")

        if not (m_src and a_src and t_src):
            raise KeyError("필수 컬럼(가맹점 / 금액 / 일시)을 찾지 못했습니다. (업로드 파일의 헤더를 확인하세요)")

        df["사용자"] = df[u_src].astype(str) if u_src else "미지정"
        df["가맹점"] = df[m_src].astype(str)
        df["일시"] = pd.to_datetime(df[t_src], errors="coerce")

        # ---------- amount ----------
        df["P_AMT"] = pd.to_numeric(
            df[a_src].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
            errors="coerce"
        ).fillna(0).astype(int)

        df["HOUR"] = df["일시"].dt.hour
        df["DATE"] = df["일시"].dt.date

        # ---------- rules ----------
        df["F_NIGHT"] = df["HOUR"].apply(lambda h: (h >= 23 or h <= 6) if pd.notna(h) else False)
        df["F_WEEKEND"] = df["일시"].dt.weekday >= 5

        if HAS_HOLIDAYS:
            years = sorted({d.year for d in df["DATE"].dropna() if isinstance(d, date)})
            kr_holidays = holidays.KR(years=years)  # type: ignore
            df["F_HOLIDAY"] = df["DATE"].isin(kr_holidays)
        else:
            df["F_HOLIDAY"] = False

        # ---------- restricted industries ----------
        RESTRICTED = [
            "주점", "유흥", "노래방", "클럽", "bar", "lounge",
            "마사지", "안마", "사우나", "스파",
            "상품권", "면세", "성인"
        ]

        EXCEPTIONS = [
            "편의점", "구내식당", "공공기관", "차량운전비"
        ]

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
            if bool(row.get("F_NIGHT", False)):
                r.append("🌙 Late Night")
            if bool(row.get("F_WEEKEND", False)):
                r.append("📅 Weekend")
            if bool(row.get("F_HOLIDAY", False)):
                r.append("🎌 Public Holiday")
            if bool(row.get("F_RESTRICT", False)):
                r.append("🚫 Restricted Industry")
            return " / ".join(r)

        df["violation_reason"] = df.apply(reason, axis=1)
        df["IS_VIOLATION"] = df["violation_reason"] != ""

        return df


# =========================================================
# SIDEBAR - FILE UPLOAD
# =========================================================
st.sidebar.title("Upload RAW DATA")
uploaded = st.sidebar.file_uploader(
    "Upload 지출결의현황.xlsx (or CSV)",
    type=["xlsx", "csv"]
)

if not uploaded:
    st.info("📂 지출결의현황.xlsx(또는 CSV) 파일을 업로드하세요.")
    st.stop()

# =========================================================
# LOAD DATA
# =========================================================
if uploaded.name.lower().endswith(".xlsx"):
    df_raw = pd.read_excel(uploaded)
else:
    try:
        df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
    except Exception:
        df_raw = pd.read_csv(uploaded)

df = AuditEngineV6_5.run_card_audit(df_raw)

# =========================================================
# DASHBOARD (VIOLATION BOARD)
# =========================================================
st.markdown(f"## 📟 Violation Summary Board  \n**BUILD:** `{BUILD}`")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🚨 Total Violations", int(df.IS_VIOLATION.sum()))
c2.metric("🌙 Late Night", int(df.F_NIGHT.sum()))
c3.metric("📅 Weekend", int(df.F_WEEKEND.sum()))
c4.metric("🎌 Holiday", int(df.F_HOLIDAY.sum()))
c5.metric("🚫 Restricted", int(df.F_RESTRICT.sum()))

# =========================================================
# HELPERS
# =========================================================
def filter_view(df_in: pd.DataFrame, key: str) -> pd.DataFrame:
    if key == "ALL":
        return df_in[df_in.IS_VIOLATION].copy()
    return df_in[df_in[key]].copy()

def table_block(title: str, df_view: pd.DataFrame, key: str):
    st.subheader(title)

    # Download buttons (CSV + Excel)
    b1, b2 = st.columns(2)
    with b1:
        csv = df_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Download CSV (current tab)",
            data=csv,
            file_name=f"{key}.csv",
            key=f"csv_{key}",
            use_container_width=True
        )

    with b2:
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df_view.to_excel(writer, index=False, sheet_name="data")
        st.download_button(
            label="⬇️ Download Excel (current tab)",
            data=out.getvalue(),
            file_name=f"{key}.xlsx",
            key=f"xlsx_{key}",
            use_container_width=True
        )

    st.dataframe(
        df_view[["사용자", "가맹점", "P_AMT", "일시", "violation_reason"]],
        use_container_width=True
    )

# =========================================================
# TABS
# =========================================================
tab_all, tab_night, tab_weekend, tab_holiday, tab_restrict = st.tabs(
    [
        "All (Violations)",
        "🌙 Late Night",
        "📅 Closed Days (Weekend)",
        "🎌 Public Holiday",
        "🚫 Limited / Focused Industries"
    ]
)

with tab_all:
    table_block("All Violations", filter_view(df, "ALL"), "all")

with tab_night:
    table_block("Late Night Violations", filter_view(df, "F_NIGHT"), "late_night")

with tab_weekend:
    table_block("Weekend Violations", filter_view(df, "F_WEEKEND"), "weekend")

with tab_holiday:
    table_block("Public Holiday Violations", filter_view(df, "F_HOLIDAY"), "holiday")

with tab_restrict:
    table_block("Restricted Industry Violations", filter_view(df, "F_RESTRICT"), "restricted")

st.caption("AuditEngine v6.5 | Corporate Card Compliance System | Excel download requires `openpyxl`.")
