import streamlit as st
import pandas as pd
import re
from datetime import date
from io import BytesIO

# =========================================================
# BUILD INFO
# =========================================================
BUILD = "AuditEngine v6.5 FINAL (KR)"

# =========================================================
# 대한민국 공휴일(법정/대체 포함) - holidays 라이브러리 사용
#   - requirements.txt에 holidays 추가 권장
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
    page_title="법인카드 운영기준 위반 점검 (v6.5)",
    layout="wide"
)

# =========================================================
# AUDIT ENGINE v6.5 (KR UI)
# =========================================================
class AuditEngineV6_5:
    @staticmethod
    def normalize_text(x) -> str:
        """가맹점명 정규화: 소문자/특수문자 제거/공백 제거"""
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

        # RAW DATA(지출결의현황.xlsx)에서 흔히 등장하는 헤더 후보들
        u_src = pick("사용자", "성명", "사원명", "User")
        m_src = pick("거래처명", "가맹점", "가맹점명", "거래처", "Customer name")
        a_src = pick("금액", "금액1", "금액.1", "이용금액", "승인금액", "Amount", "결제금액", "금액(원)")
        t_src = pick("승인일시", "일시", "Approval date", "거래일시", "결제일시", "승인일자")

        if not (m_src and a_src and t_src):
            raise KeyError(
                "필수 컬럼(거래처명/가맹점, 금액, 승인일시/일시)을 찾지 못했습니다.\n"
                "엑셀 1행(헤더)을 확인하세요.\n"
                f"- 현재 컬럼: {list(df.columns)}"
            )

        # 표준 컬럼명으로 복사 (UI 표시/다운로드용)
        df["사용자"] = df[u_src].astype(str) if u_src else "미지정"
        df["가맹점"] = df[m_src].astype(str)
        df["일시"] = pd.to_datetime(df[t_src], errors="coerce")

        # ---------- 금액 파싱 ----------
        df["P_AMT"] = pd.to_numeric(
            df[a_src].astype(str).str.replace(r"[^0-9\-]", "", regex=True),
            errors="coerce"
        ).fillna(0).astype(int)

        # ---------- 시간/일자 ----------
        df["HOUR"] = df["일시"].dt.hour
        df["DATE"] = df["일시"].dt.date

        # ---------- 운영기준 룰 ----------
        # 심야(23~06)
        df["F_NIGHT"] = df["HOUR"].apply(lambda h: (h >= 23 or h <= 6) if pd.notna(h) else False)
        # 주말
        df["F_WEEKEND"] = df["일시"].dt.weekday >= 5

        # 공휴일(법정/대체 포함)
        if HAS_HOLIDAYS:
            years = sorted({d.year for d in df["DATE"].dropna() if isinstance(d, date)})
            kr_holidays = holidays.KR(years=years)  # type: ignore
            df["F_HOLIDAY"] = df["DATE"].isin(kr_holidays)
        else:
            df["F_HOLIDAY"] = False

        # 제한/유흥 업종(키워드 + 정규화)
        RESTRICTED = [
            # 유흥/주점
            "유흥", "유흥주점", "단란", "단란주점", "주점", "호프", "bar", "lounge", "pub", "클럽", "club",
            "노래방", "karaoke",
            # 위생/대인 서비스(예시)
            "마사지", "안마", "안마시술소", "스파", "사우나", "찜질", "목욕",
            # 상품권/면세/성인
            "상품권", "면세", "성인"
        ]

        # 예외(오탐 방지) - 조직 사정에 맞게 추가 가능
        EXCEPTIONS = [
            "편의점", "구내식당", "공공기관", "차량운전비"
        ]

        def is_restricted(merchant_name: str) -> bool:
            n = AuditEngineV6_5.normalize_text(merchant_name)
            for ex in EXCEPTIONS:
                if AuditEngineV6_5.normalize_text(ex) in n:
                    return False
            return any(AuditEngineV6_5.normalize_text(k) in n for k in RESTRICTED)

        df["F_RESTRICT"] = df["가맹점"].apply(is_restricted)

        # ---------- 위반 사유(한국어) ----------
        def reason(row):
            r = []
            if bool(row.get("F_NIGHT", False)):
                r.append("🌙 심야(23~06)")
            if bool(row.get("F_WEEKEND", False)):
                r.append("📅 휴무일(주말)")
            if bool(row.get("F_HOLIDAY", False)):
                r.append("🎌 공휴일(법정/대체)")
            if bool(row.get("F_RESTRICT", False)):
                r.append("🚫 제한/유흥 업종")
            return " / ".join(r)

        df["위반사유"] = df.apply(reason, axis=1)
        df["운영기준위반"] = df["위반사유"] != ""

        return df


# =========================================================
# SIDEBAR - FILE UPLOAD
# =========================================================
st.sidebar.title("RAW DATA 업로드")
uploaded = st.sidebar.file_uploader(
    "지출결의현황.xlsx (또는 CSV) 업로드",
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
# VIOLATION SUMMARY BOARD (Korean)
# =========================================================
st.markdown(f"## 🧾 운영기준 위반 요약 보드")
st.caption(f"BUILD: {BUILD}  |  공휴일 판정: {'활성' if HAS_HOLIDAYS else '비활성(holidays 미설치)'}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🚨 전체 위반", int(df["운영기준위반"].sum()))
c2.metric("🌙 심야", int(df["F_NIGHT"].sum()))
c3.metric("📅 주말", int(df["F_WEEKEND"].sum()))
c4.metric("🎌 공휴일", int(df["F_HOLIDAY"].sum()))
c5.metric("🚫 제한업종", int(df["F_RESTRICT"].sum()))

# =========================================================
# HELPERS
# =========================================================
DISPLAY_COLS = ["사용자", "가맹점", "P_AMT", "일시", "위반사유"]

def filter_view(df_in: pd.DataFrame, key: str) -> pd.DataFrame:
    if key == "ALL":
        return df_in[df_in["운영기준위반"]].copy()
    return df_in[df_in[key]].copy()

def download_buttons(df_view: pd.DataFrame, key: str):
    b1, b2 = st.columns(2)

    with b1:
        csv = df_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ CSV 다운로드(현재 탭)",
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
            label="⬇️ 엑셀 다운로드(현재 탭)",
            data=out.getvalue(),
            file_name=f"{key}.xlsx",
            key=f"xlsx_{key}",
            use_container_width=True
        )

def table_block(title: str, df_view: pd.DataFrame, key: str):
    st.subheader(title)
    download_buttons(df_view, key)
    st.dataframe(df_view[DISPLAY_COLS], use_container_width=True)

# =========================================================
# TABS (Korean)
# =========================================================
tab_all, tab_night, tab_weekend, tab_holiday, tab_restrict = st.tabs(
    [
        "전체(위반)",
        "🌙 심야",
        "📅 휴무일(주말)",
        "🎌 공휴일",
        "🚫 제한/유흥 업종"
    ]
)

with tab_all:
    table_block("전체 위반 내역", filter_view(df, "ALL"), "all")

with tab_night:
    table_block("심야 위반 내역(23~06)", filter_view(df, "F_NIGHT"), "late_night")

with tab_weekend:
    table_block("휴무일(주말) 위반 내역", filter_view(df, "F_WEEKEND"), "weekend")

with tab_holiday:
    table_block("공휴일(법정/대체) 위반 내역", filter_view(df, "F_HOLIDAY"), "holiday")

with tab_restrict:
    table_block("제한/유흥 업종 위반 내역", filter_view(df, "F_RESTRICT"), "restricted")

st.caption("※ 엑셀 다운로드는 openpyxl 필요 / 공휴일 판정은 holidays 필요")
