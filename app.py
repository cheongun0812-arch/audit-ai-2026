import streamlit as st
import pandas as pd
import re
from datetime import date
from io import BytesIO

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.6 FINAL (KR-STRICT)"

# =========================================================
# 대한민국 공휴일(2026 기준 포함)
#  - 법정공휴일/대체공휴일/크리스마스 포함
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
    page_title="법인카드 운영기준 위반 점검 (v6.6)",
    layout="wide"
)

# =========================================================
# AUDIT ENGINE v6.6 (KR)
# =========================================================
class AuditEngineV6_6:
    @staticmethod
    def normalize_text(x) -> str:
        if pd.isna(x):
            return ""
        x = str(x).lower()
        x = re.sub(r"[^a-z0-9가-힣]", "", x)
        return x

    @staticmethod
    def run_card_audit(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ---------- 컬럼 자동 매핑 ----------
        def pick(*cands):
            for c in cands:
                if c in df.columns:
                    return c
            return None

        u_src = pick("사용자", "성명", "사원명", "User")
        m_src = pick("거래처명", "가맹점", "가맹점명", "거래처", "Customer name")
        a_src = pick("금액", "금액1", "금액.1", "이용금액", "승인금액", "Amount", "결제금액", "금액(원)")
        t_src = pick("승인일시", "일시", "Approval date", "거래일시", "결제일시", "승인일자")

        if not (m_src and a_src and t_src):
            raise KeyError(
                "필수 컬럼(거래처명/가맹점, 금액, 승인일시/일시)을 찾지 못했습니다.\n"
                f"현재 컬럼: {list(df.columns)}"
            )

        df["사용자"] = df[u_src].astype(str) if u_src else "미지정"
        df["가맹점"] = df[m_src].astype(str)
        df["일시"] = pd.to_datetime(df[t_src], errors="coerce")

        # ---------- 금액 ----------
        df["P_AMT"] = pd.to_numeric(
            df[a_src].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
            errors="coerce"
        ).fillna(0).astype(int)

        # ---------- 시간/일자 ----------
        df["HOUR"] = df["일시"].dt.hour
        df["DATE"] = df["일시"].dt.date

        # ---------- 주말/심야 ----------
        # 주말: 토/일
        df["F_WEEKEND"] = df["일시"].dt.weekday >= 5
        # 심야: 23~06
        df["F_NIGHT"] = df["HOUR"].apply(lambda h: (h >= 23 or h <= 6) if pd.notna(h) else False)

        # ---------- 공휴일(2026 포함) ----------
        if HAS_HOLIDAYS:
            years = sorted({d.year for d in df["DATE"].dropna() if isinstance(d, date)})
            kr = holidays.KR(years=years)  # 법정/대체/크리스마스 포함
            df["F_HOLIDAY"] = df["DATE"].isin(kr)
        else:
            df["F_HOLIDAY"] = False

        # ---------- 차량비 전면 제외 ----------
        vehicle_patterns = [
            "차량", "차량운전비", "유류", "주유", "하이패스", "통행료", "주차", "주차비",
            "렌터카", "렌트카", "대리운전", "택시", "카카오t", "카카오택시", "고속도로",
            "세차", "차량수선", "정비"
        ]
        title_col = "문서 내용(제목)" if "문서 내용(제목)" in df.columns else None

        def is_vehicle(row):
            hay = []
            if title_col:
                hay.append(str(row.get(title_col, "")))
            hay.append(str(row.get("사용자", "")))
            hay.append(str(row.get("가맹점", "")))
            txt = " ".join(hay)
            return any(p in txt for p in vehicle_patterns)

        df = df[~df.apply(is_vehicle, axis=1)].copy()

        # ---------- 제한/비업무 업종(첨부 데이터 기준 최소 반영) ----------
        # NOTE:
        # - 'OO bar', 'OO club', '지점/branch' 표기 전부 제외 (요청사항)
        # - 실제 유흥으로 명확한 항목만 유지
        RESTRICTED_EXPLICIT = [
            "유흥주점", "단란주점", "나이트클럽", "안마시술소", "안마", "마사지"
        ]

        def is_restricted(name: str) -> bool:
            n = AuditEngineV6_6.normalize_text(name)
            # 지점/branch/점 표기 전부 제외
            if ("지점" in n) or ("branch" in n) or n.endswith("점"):
                return False
            # bar/club 전부 제외 (비유흥으로 간주)
            if any(k in n for k in ["bar", "club", "클럽", "pub", "lounge"]):
                return False
            # 명시적 유흥만 제한
            return any(AuditEngineV6_6.normalize_text(k) in n for k in RESTRICTED_EXPLICIT)

        df["F_RESTRICT"] = df["가맹점"].apply(is_restricted)

        # ---------- 위반 사유 ----------
        def reason(row):
            r = []
            if row.F_NIGHT: r.append("🌙 심야(23~06)")
            if row.F_WEEKEND: r.append("📅 휴무일(주말)")
            if row.F_HOLIDAY: r.append("🎌 공휴일(법정/대체/성탄절)")
            if row.F_RESTRICT: r.append("🚫 제한업종(명시적 유흥)")
            return " / ".join(r)

        df["위반사유"] = df.apply(reason, axis=1)
        df["운영기준위반"] = df["위반사유"] != ""

        return df


# =========================================================
# UI
# =========================================================
st.sidebar.title("RAW DATA 업로드")
uploaded = st.sidebar.file_uploader(
    "지출결의현황.xlsx (또는 CSV)",
    type=["xlsx", "csv"]
)

if not uploaded:
    st.info("파일을 업로드하세요.")
    st.stop()

# LOAD
if uploaded.name.lower().endswith(".xlsx"):
    raw = pd.read_excel(uploaded)
else:
    raw = pd.read_csv(uploaded)

df = AuditEngineV6_6.run_card_audit(raw)

# SUMMARY
st.markdown("## 🧾 운영기준 위반 요약")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🚨 전체 위반", int(df["운영기준위반"].sum()))
c2.metric("🌙 심야", int(df["F_NIGHT"].sum()))
c3.metric("📅 주말", int(df["F_WEEKEND"].sum()))
c4.metric("🎌 공휴일", int(df["F_HOLIDAY"].sum()))
c5.metric("🚫 제한업종", int(df["F_RESTRICT"].sum()))

DISPLAY = ["사용자", "가맹점", "P_AMT", "일시", "위반사유"]

def view(df, key):
    if key == "ALL":
        return df[df["운영기준위반"]]
    return df[df[key]]

def block(title, d, key):
    st.subheader(title)
    b1, b2 = st.columns(2)
    with b1:
        st.download_button("⬇️ CSV 다운로드", d.to_csv(index=False).encode("utf-8-sig"), f"{key}.csv")
    with b2:
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            d.to_excel(w, index=False)
        st.download_button("⬇️ 엑셀 다운로드", out.getvalue(), f"{key}.xlsx")
    st.dataframe(d[DISPLAY], use_container_width=True)

tabs = st.tabs(["전체(위반)", "🌙 심야", "📅 주말", "🎌 공휴일", "🚫 제한업종"])

with tabs[0]:
    block("전체 위반", view(df, "ALL"), "all")
with tabs[1]:
    block("심야", view(df, "F_NIGHT"), "late_night")
with tabs[2]:
    block("주말", view(df, "F_WEEKEND"), "weekend")
with tabs[3]:
    block("공휴일", view(df, "F_HOLIDAY"), "holiday")
with tabs[4]:
    block("제한업종(명시적 유흥)", view(df, "F_RESTRICT"), "restricted")

st.caption("v6.6 | 기준: 2025년 재원운영기준(첨부) 및 2026년 공휴일")
