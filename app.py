import streamlit as st
import pandas as pd
from datetime import datetime

# =========================================================
# 1) 페이지 설정
# =========================================================
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# =========================================================
# 2) CSS (시인성 + 다크테마 + Alert 박스 다크화)
# =========================================================
st.markdown(
    """
<style>
.stApp { background-color: #0A0A0B; color: #FFFFFF; }

.header-box {
  background-color: #161618;
  padding: 22px 22px;
  border-radius: 14px;
  border: 1px solid #2C2C2E;
  margin-bottom: 22px;
  text-align: center;
}
.main-title { font-size: 44px; font-weight: 900; color: #FFD700; margin: 0; }
.sub-title  { color:#C9B458; font-size:16px; margin: 8px 0 0 0; }

[data-testid="stSidebar"] {
  background-color: #111112 !important;
  border-right: 1px solid #2C2C2E;
}

[data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 900 !important; font-size: 30px !important; }
[data-testid="stMetricLabel"] { color: #FFD700 !important; font-weight: 800 !important; }

/* 입력 요소 텍스트 */
[data-testid="stSelectbox"] *,
[data-testid="stNumberInput"] *,
[data-testid="stSlider"] *,
[data-testid="stTextInput"] *,
[data-testid="stTextArea"] * { color: #FFFFFF !important; }

/* 테이블/에디터 */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border: 1px solid #2C2C2E !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}

/* Alert 박스(흰 박스 문제 제거) */
div[data-testid="stAlert"] {
  border-radius: 12px !important;
  border: 1px solid #2C2C2E !important;
  background: #151517 !important;
}
div[data-testid="stAlert"] * { color: #FFFFFF !important; }
div[data-testid="stAlert"] a { color: #FFD700 !important; }

hr { border-top: 1px solid #2C2C2E !important; }
h1, h2, h3, h4 { color: #FFFFFF !important; }
</style>
""",
    unsafe_allow_html=True
)

# =========================================================
# 3) 감사 로직 엔진
# =========================================================
class AuditSystem:
    STANDARD_COLS = {
        "사용자": ["사용자", "성명", "이용자", "사원명", "성함", "User"],
        "가맹점": ["가맹점명", "거래처", "상호", "가맹점", "지점명", "Merchant", "Customer name"],
        "금액": ["이용금액", "금액", "결제금액", "승인금액", "합계", "Amount"],
        "일시": ["승인일시", "결제일시", "일시", "날짜", "거래일시", "Date", "Approval date"],
    }

    @staticmethod
    def get_standard_mapping(df: pd.DataFrame) -> dict:
        mapping = {}
        cols = [str(c).strip() for c in df.columns]
        for key, aliases in AuditSystem.STANDARD_COLS.items():
            for c in cols:
                if c in aliases:
                    mapping[key] = c
                    break
        return mapping

    @staticmethod
    def _is_hour_in_range(hour: float, start: int, end: int) -> bool:
        if pd.isna(hour):
            return False
        hour = int(hour)
        if start <= end:
            return start <= hour <= end
        return (hour >= start) or (hour <= end)

    @staticmethod
    def _parse_amount(series: pd.Series) -> pd.Series:
        s = (
            series.astype(str)
            .str.replace(r"[^0-9\-]", "", regex=True)
            .replace("", "0")
        )
        amt = pd.to_numeric(s, errors="coerce").fillna(0)
        return amt.abs().astype("int64")

    @staticmethod
    def analyze_risk(
        df: pd.DataFrame,
        mapping: dict,
        night_start: int,
        night_end: int,
        high_amount_limit: int,
        suspicious_keywords: list[str],
        score_weights: dict,
    ):
        df = df.copy()

        merchant_col = mapping["가맹점"]
        amt_col = mapping["금액"]
        dt_col = mapping["일시"]

        df["P_AMT"] = AuditSystem._parse_amount(df[amt_col])
        df["P_DT"] = pd.to_datetime(df[dt_col], errors="coerce")
        df["P_DATE"] = df["P_DT"].dt.date
        df["P_HOUR"] = df["P_DT"].dt.hour

        if "사용자" not in mapping:
            df["_P_USER"] = "미지정"
            mapping["사용자"] = "_P_USER"

        df["F_NIGHT"] = df["P_HOUR"].apply(lambda h: AuditSystem._is_hour_in_range(h, night_start, night_end))
        df["F_HIGH"] = df["P_AMT"] >= int(high_amount_limit)

        kw = [k.strip() for k in suspicious_keywords if str(k).strip()]
        if len(kw) == 0:
            df["F_SUSPICIOUS"] = False
        else:
            pattern = "|".join([pd.regex.escape(k) for k in kw])
            df["F_SUSPICIOUS"] = df[merchant_col].astype(str).str.contains(pattern, case=False, na=False)

        w_night = int(score_weights.get("night", 40))
        w_high = int(score_weights.get("high", 30))
        w_susp = int(score_weights.get("suspicious", 30))

        df["risk_score"] = (
            df["F_NIGHT"].astype(int) * w_night +
            df["F_HIGH"].astype(int) * w_high +
            df["F_SUSPICIOUS"].astype(int) * w_susp
        )

        def build_reasons(row):
            reasons = []
            if row["F_NIGHT"]:
                reasons.append("🌙심야")
            if row["F_HIGH"]:
                reasons.append("💰고액")
            if row["F_SUSPICIOUS"]:
                reasons.append("🔍위장의심(키워드)")
            return ", ".join(reasons)

        df["violation"] = df.apply(build_reasons, axis=1)

        features = {
            "user_col": mapping["사용자"],
            "merchant_col": merchant_col,
            "amt_col": amt_col,
            "dt_col": dt_col,
            "rule_cols": {"night": "F_NIGHT", "high": "F_HIGH", "suspicious": "F_SUSPICIOUS"},
        }
        return df, features


# =========================================================
# 4) 헤더
# =========================================================
st.markdown(
    """
<div class="header-box">
  <p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>
  <p class="sub-title">통합 감사 데이터 분석 시스템 v1.5 (matplotlib 제거 버전)</p>
</div>
""",
    unsafe_allow_html=True
)

# =========================================================
# 5) 사이드바 설정
# =========================================================
with st.sidebar:
    st.header("⚙️ 감사 기준 설정")
    night_range = st.slider("심야 시간 설정", 0, 23, (23, 6))
    high_amount_limit = st.number_input("고액 기준(원)", value=500000, step=50000, min_value=0)

    st.divider()
    st.markdown("### 🔍 위장 의심 키워드(사용자 정의)")
    default_keywords = "유통, 기획, 네트웍스, 컨설팅, 종합"
    keywords_text = st.text_area("쉼표(,)로 구분해서 입력", value=default_keywords, height=80)
    suspicious_keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]

    st.divider()
    st.markdown("### 🧮 점수 가중치(선택)")
    w_night = st.number_input("심야 가중치", value=40, step=5, min_value=0, max_value=100)
    w_high = st.number_input("고액 가중치", value=30, step=5, min_value=0, max_value=100)
    w_susp = st.number_input("위장의심(키워드) 가중치", value=30, step=5, min_value=0, max_value=100)

    st.divider()
    st.markdown("### 🧰 출력/필터 옵션")
    min_score = st.slider("표시 최소 위험점수", 0, 100, 40, step=5)

    st.info(
        "필수 컬럼: [가맹점명(또는 상호/거래처), 이용금액(또는 결제금액), 승인일시(또는 결제일시)]\n\n"
        "※ [사용자] 컬럼이 없으면 '미지정'으로 표시됩니다."
    )

# =========================================================
# 6) 업로드
# =========================================================
uploaded_file = st.file_uploader("가공된 엑셀(XLSX) 또는 CSV 파일을 업로드하세요.", type=["csv", "xlsx"])
if not uploaded_file:
    st.info("💡 파일을 업로드하면 자동으로 AI 분석이 시작됩니다.")
    st.stop()

# =========================================================
# 7) 파일 로드 + 분석
# =========================================================
try:
    if uploaded_file.name.lower().endswith(".xlsx"):
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        selected_sheet = sheet_names[0] if len(sheet_names) == 1 else st.selectbox("📝 데이터가 있는 시트를 선택하세요", sheet_names)
        df_raw = excel_file.parse(selected_sheet)
    else:
        try:
            df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except Exception:
            df_raw = pd.read_csv(uploaded_file)

    if df_raw is None or df_raw.empty:
        st.error("❗ 업로드된 파일이 비어있거나 읽을 수 없습니다.")
        st.stop()

    audit = AuditSystem()
    mapping = audit.get_standard_mapping(df_raw)

    missing = [k for k in ["가맹점", "금액", "일시"] if k not in mapping]
    if missing:
        st.error(
            "❗ 필수 컬럼을 찾을 수 없습니다.\n\n"
            f"- 누락: {', '.join(missing)}\n\n"
            "현재 컬럼 목록을 확인하세요."
        )
        st.write("현재 컬럼 목록:", list(df_raw.columns))
        st.stop()

    df_analyzed, features = audit.analyze_risk(
        df_raw,
        mapping=mapping,
        night_start=night_range[0],
        night_end=night_range[1],
        high_amount_limit=high_amount_limit,
        suspicious_keywords=suspicious_keywords,
        score_weights={"night": w_night, "high": w_high, "suspicious": w_susp},
    )

except Exception as e:
    st.error(f"⚠️ 처리 중 오류: {e}")
    st.stop()

# =========================================================
# 8) 대시보드
# =========================================================
st.subheader("📊 감사 요약 대시보드")

total_cnt = len(df_analyzed)
high_cnt = int((df_analyzed["risk_score"] >= 70).sum())
mid_cnt = int((df_analyzed["risk_score"] >= 40).sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("총 분석 건수", f"{total_cnt:,}건")
with c2:
    st.metric("고위험(≥70)", f"{high_cnt:,}건")
with c3:
    st.metric("주의(≥40)", f"{mid_cnt:,}건")
with c4:
    st.metric("심야(룰)", f"{int(df_analyzed['F_NIGHT'].sum()):,}건")

st.divider()

# =========================================================
# 9) 규칙별 필터 탭
# =========================================================
rule_cols = features["rule_cols"]
user_col = features["user_col"]
merchant_col = features["merchant_col"]
dt_col = features["dt_col"]

display_cols = [user_col, merchant_col, "P_AMT", dt_col, "risk_score", "violation"]

def filtered_view(base: pd.DataFrame, mode: str) -> pd.DataFrame:
    df = base.copy()
    if mode == "night":
        df = df[df[rule_cols["night"]] == True]
    elif mode == "high":
        df = df[df[rule_cols["high"]] == True]
    elif mode == "suspicious":
        df = df[df[rule_cols["suspicious"]] == True]
    df = df[df["risk_score"] >= int(min_score)]
    return df.sort_values("risk_score", ascending=False)

def render_table(df: pd.DataFrame, title: str):
    st.markdown(f"### {title}")
    if df.empty:
        st.info("조건에 해당하는 데이터가 없습니다.")
        return

    st.data_editor(
        df[display_cols],
        column_config={
            "risk_score": st.column_config.ProgressColumn("위험점수", min_value=0, max_value=100, format="%d점"),
            "P_AMT": st.column_config.NumberColumn("결제금액", format="%d원"),
            "violation": st.column_config.TextColumn("위반 사유"),
        },
        use_container_width=True,
        hide_index=True,
        disabled=True,
    )

tab_all, tab_night, tab_high, tab_susp = st.tabs(["전체", "🌙 심야", "💰 고액", "🔍 위장의심(키워드)"])

with tab_all:
    render_table(filtered_view(df_analyzed, "all"), "📋 정밀 검토 대상 리스트(전체)")

with tab_night:
    render_table(filtered_view(df_analyzed, "night"), "🌙 심야 거래(필터)")

with tab_high:
    render_table(filtered_view(df_analyzed, "high"), "💰 고액 거래(필터)")

with tab_susp:
    render_table(filtered_view(df_analyzed, "suspicious"), "🔍 위장 의심(키워드) 거래(필터)")

st.divider()

# =========================================================
# 10) 차트(설치 없이 Streamlit 기본 차트 사용)
# =========================================================
st.subheader("📈 시각화(분포/시간대/규칙별)")

chart_df = df_analyzed[df_analyzed["P_DT"].notna()].copy()

colA, colB = st.columns(2)

with colA:
    st.markdown("#### 위험점수 분포(히스토그램)")
    if chart_df.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
    else:
        # 히스토그램용 bin
        bins = pd.cut(chart_df["risk_score"], bins=list(range(0, 105, 5)), right=False)
        hist = bins.value_counts().sort_index()
        hist_df = hist.reset_index()
        hist_df.columns = ["score_bin", "count"]
        hist_df["score_bin"] = hist_df["score_bin"].astype(str)
        st.bar_chart(hist_df.set_index("score_bin"))

with colB:
    st.markdown("#### 시간대별 거래 건수")
    if chart_df.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
    else:
        hour_counts = chart_df["P_HOUR"].dropna().astype(int).value_counts().sort_index()
        st.bar_chart(hour_counts)

st.markdown("#### 규칙별 적발 건수")
r1, r2, r3 = st.columns(3)
with r1:
    st.metric("🌙 심야", f"{int(df_analyzed['F_NIGHT'].sum()):,}건")
with r2:
    st.metric("💰 고액", f"{int(df_analyzed['F_HIGH'].sum()):,}건")
with r3:
    st.metric("🔍 위장의심(키워드)", f"{int(df_analyzed['F_SUSPICIOUS'].sum()):,}건")

st.divider()

# =========================================================
# 11) 다운로드
# =========================================================
st.subheader("📥 분석 보고서 다운로드")

download_mode = st.selectbox(
    "다운로드 범위 선택",
    ["현재(전체 탭 기준)", "심야만", "고액만", "위장의심만", "원본+분석 전체(필터 미적용)"],
)

if download_mode == "현재(전체 탭 기준)":
    out_df = filtered_view(df_analyzed, "all")
elif download_mode == "심야만":
    out_df = filtered_view(df_analyzed, "night")
elif download_mode == "고액만":
    out_df = filtered_view(df_analyzed, "high")
elif download_mode == "위장의심만":
    out_df = filtered_view(df_analyzed, "suspicious")
else:
    out_df = df_analyzed.copy()

remove_temp = st.checkbox("임시 컬럼(_P_*) 제거 후 다운로드", value=True)
final_out = out_df.drop(columns=[c for c in out_df.columns if c.startswith("_P_")], errors="ignore") if remove_temp else out_df

csv_bytes = final_out.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ CSV 다운로드",
    data=csv_bytes,
    file_name=f"Audit_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)

st.caption("※ 점수/키워드/심야시간 설정은 사이드바에서 조정 가능합니다.")
