import streamlit as st
import pandas as pd
from datetime import datetime

# =========================================================
# 1) 페이지 설정
# =========================================================
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")


# =========================================================
# 2) 고급 UI CSS (통일감/품격/가독성)
#   - 전체 다크 톤 통일
#   - 카드(Panel) 레이아웃
#   - 입력/선택/업로더: 다크 배경 + 밝은 텍스트로 일관성 유지
#   - Dropdown(listbox)까지 함께 스타일링
# =========================================================
st.markdown(
    """
<style>
/* ===== Base ===== */
:root{
  --bg: #0B0D10;
  --panel: #12151B;
  --panel2:#0F1217;
  --border:#232836;
  --border2:#2D3446;
  --text:#EDEFF4;
  --muted:#AEB6C6;
  --muted2:#8791A6;
  --gold:#D6B25E;
  --gold2:#BFA04D;
  --danger:#2B1416;
  --dangerBorder:#4A2326;
  --success:#14271C;
  --successBorder:#284A37;
  --shadow: 0 10px 24px rgba(0,0,0,.35);
}

.stApp{
  background: radial-gradient(1200px 600px at 20% 0%, rgba(214,178,94,.08), transparent 60%),
              radial-gradient(1000px 600px at 90% 10%, rgba(90,132,255,.08), transparent 55%),
              var(--bg);
  color: var(--text);
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, #0E1116 0%, #0A0C10 100%) !important;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stMarkdown, 
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span{
  color: var(--text) !important;
}

/* ===== Typography ===== */
h1,h2,h3,h4{ color: var(--text) !important; }
hr{ border-top: 1px solid var(--border) !important; }

/* ===== Header ===== */
.hero{
  background: linear-gradient(135deg, rgba(214,178,94,.15) 0%, rgba(214,178,94,.06) 30%, rgba(255,255,255,.03) 100%);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 22px 24px;
  box-shadow: var(--shadow);
  margin-bottom: 18px;
}
.hero-top{
  display:flex; align-items:center; gap:10px;
  font-weight:900; letter-spacing:.2px;
}
.badge{
  display:inline-flex; align-items:center; justify-content:center;
  width:30px; height:30px; border-radius:10px;
  background: rgba(214,178,94,.18);
  border: 1px solid rgba(214,178,94,.35);
  color: var(--gold);
  font-weight:900;
}
.hero-title{ font-size: 18px; color: var(--text); margin:0; }
.hero-sub{ margin-top:6px; color: var(--muted); font-size: 13px; }

/* ===== Panels (Cards) ===== */
.panel{
  background: linear-gradient(180deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.015) 100%), var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px 16px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}
.panel-title{
  font-weight: 900;
  color: var(--text);
  margin: 0 0 10px 0;
  font-size: 14px;
  letter-spacing: .2px;
}
.panel-sub{
  color: var(--muted2);
  font-size: 12px;
  margin: -6px 0 10px 0;
}

/* ===== Metrics polish ===== */
[data-testid="stMetricValue"]{ color: var(--text) !important; font-weight: 900 !important; }
[data-testid="stMetricLabel"]{ color: var(--gold) !important; font-weight: 800 !important; }

/* ===== Tables / Data Editor ===== */
[data-testid="stDataFrame"], [data-testid="stDataEditor"]{
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  box-shadow: 0 8px 18px rgba(0,0,0,.25);
}

/* ===== Alerts ===== */
div[data-testid="stAlert"]{
  border-radius: 14px !important;
  border: 1px solid var(--border) !important;
  background: var(--panel2) !important;
}
div[data-testid="stAlert"] *{ color: var(--text) !important; }
div[data-testid="stAlert"] a{ color: var(--gold) !important; }

/* ===== Inputs (Select/Text/Number/TextArea) — Dark & crisp ===== */
/* Baseweb select container */
div[data-baseweb="select"] > div{
  background-color: #0E1117 !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
}
/* Selected value text */
div[data-baseweb="select"] span,
div[data-baseweb="select"] input{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}
/* Text inputs / textareas */
input, textarea{
  background-color: #0E1117 !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}
textarea::placeholder, input::placeholder{
  color: var(--muted2) !important;
  -webkit-text-fill-color: var(--muted2) !important;
}

/* Dropdown listbox (opened menu) */
div[role="listbox"]{
  background: #0E1117 !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  box-shadow: 0 18px 30px rgba(0,0,0,.45) !important;
}
div[role="listbox"] span{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}

/* ===== FileUploader (Browse files) + Selected file card ===== */
[data-testid="stFileUploader"]{
  background: #0E1117 !important;
  border: 1px dashed rgba(214,178,94,.35) !important;
  border-radius: 14px !important;
  padding: 12px !important;
}
[data-testid="stFileUploader"] *{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] label{
  color: var(--muted) !important;
  -webkit-text-fill-color: var(--muted) !important;
}
[data-testid="stFileUploader"] button{
  border-radius: 12px !important;
  border: 1px solid rgba(214,178,94,.45) !important;
}

/* Selected file row/card */
div[data-testid="stFileUploaderFile"]{
  background: #0E1117 !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
}
div[data-testid="stFileUploaderFile"] *,
div[data-testid="stFileUploaderFileName"] *{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}
div[data-testid="stFileUploaderFile"] svg{
  fill: var(--muted) !important;
}

/* ===== Buttons / download ===== */
.stDownloadButton button, .stButton button{
  border-radius: 12px !important;
  border: 1px solid rgba(214,178,94,.45) !important;
}
.stDownloadButton button:hover, .stButton button:hover{
  border: 1px solid rgba(214,178,94,.75) !important;
}

/* ===== Spacing (Streamlit default padding tweak) ===== */
.block-container{ padding-top: 18px !important; }
</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# 3) 카드 래퍼(Panel) 헬퍼
# =========================================================
def panel_open(title: str, subtitle: str | None = None):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<p class="panel-title">{title}</p>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="panel-sub">{subtitle}</p>', unsafe_allow_html=True)

def panel_close():
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 4) 감사 로직 엔진
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
# 5) HERO
# =========================================================
st.markdown(
    """
<div class="hero">
  <div class="hero-top">
    <div class="badge">🛡️</div>
    <div class="hero-title">2026 AUDIT AI PORTAL</div>
  </div>
  <div class="hero-sub">통합 감사 데이터 분석 시스템 · Dignified UI Edition (일관된 다크톤/패널 구조/가독성 강화)</div>
</div>
""",
    unsafe_allow_html=True
)


# =========================================================
# 6) Sidebar (정돈된 구성)
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ 감사 기준 설정")
    night_range = st.slider("심야 시간 설정", 0, 23, (23, 6))
    high_amount_limit = st.number_input("고액 기준(원)", value=500000, step=50000, min_value=0)

    st.divider()

    st.markdown("## 🔍 위장 의심 키워드")
    keywords_text = st.text_area(
        "쉼표(,)로 구분해서 입력",
        value="유통, 기획, 네트웍스, 컨설팅, 종합",
        height=90,
        placeholder="예: 유통, 컨설팅, 네트웍스"
    )
    suspicious_keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]

    st.divider()

    st.markdown("## 🧮 점수 가중치")
    w_night = st.number_input("심야 가중치", value=40, step=5, min_value=0, max_value=100)
    w_high = st.number_input("고액 가중치", value=30, step=5, min_value=0, max_value=100)
    w_susp = st.number_input("위장의심(키워드) 가중치", value=30, step=5, min_value=0, max_value=100)

    st.divider()

    st.markdown("## 🧰 출력/필터")
    min_score = st.slider("표시 최소 위험점수", 0, 100, 40, step=5)

    st.info(
        "필수 컬럼: **가맹점(상호/거래처)**, **금액**, **일시**\n\n"
        "※ 사용자 컬럼이 없으면 **미지정**으로 표시됩니다."
    )


# =========================================================
# 7) 업로드 Panel
# =========================================================
panel_open("① 데이터 업로드", "XLSX 또는 CSV 업로드 후 자동으로 시트 선택/분석이 진행됩니다.")
uploaded_file = st.file_uploader("가공된 파일을 업로드하세요.", type=["csv", "xlsx"])
panel_close()

if not uploaded_file:
    panel_open("가이드", "업로드 전 단계입니다.")
    st.info("파일을 업로드하면 분석이 시작됩니다. (선택값/파일명은 화면에 또렷하게 표시되도록 이미 보정되어 있습니다.)")
    panel_close()
    st.stop()


# =========================================================
# 8) 파일 로드 + 분석
# =========================================================
try:
    if uploaded_file.name.lower().endswith(".xlsx"):
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names

        panel_open("② 시트 선택", "데이터가 포함된 시트를 선택하세요. 선택값이 흐리게 보이지 않도록 UI가 보정되어 있습니다.")
        selected_sheet = sheet_names[0] if len(sheet_names) == 1 else st.selectbox("📝 데이터가 있는 시트를 선택하세요", sheet_names)
        panel_close()

        df_raw = excel_file.parse(selected_sheet)
    else:
        df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")

    if df_raw is None or df_raw.empty:
        panel_open("오류", "파일이 비어 있거나 읽을 수 없습니다.")
        st.error("업로드된 파일이 비어있거나 읽을 수 없습니다.")
        panel_close()
        st.stop()

    audit = AuditSystem()
    mapping = audit.get_standard_mapping(df_raw)

    missing = [k for k in ["가맹점", "금액", "일시"] if k not in mapping]
    if missing:
        panel_open("필수 컬럼 확인", "현재 파일은 분석에 필요한 컬럼 매핑이 되지 않습니다.")
        st.error("필수 컬럼을 찾을 수 없습니다.")
        st.write("누락:", ", ".join(missing))
        st.write("현재 컬럼 목록:", list(df_raw.columns))
        panel_close()
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
    panel_open("처리 오류", "데이터 처리 중 예외가 발생했습니다.")
    st.error(f"⚠️ 처리 중 오류: {e}")
    panel_close()
    st.stop()


# =========================================================
# 9) 요약 Panel
# =========================================================
panel_open("③ 감사 요약 대시보드", "핵심 지표를 한 눈에 확인합니다.")
total_cnt = len(df_analyzed)
high_cnt = int((df_analyzed["risk_score"] >= 70).sum())
mid_cnt = int((df_analyzed["risk_score"] >= 40).sum())
night_cnt = int(df_analyzed["F_NIGHT"].sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("총 분석", f"{total_cnt:,}건")
with c2:
    st.metric("고위험(≥70)", f"{high_cnt:,}건")
with c3:
    st.metric("주의(≥40)", f"{mid_cnt:,}건")
with c4:
    st.metric("심야(룰)", f"{night_cnt:,}건")
panel_close()


# =========================================================
# 10) 리스트 Panel (탭)
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

def render_table(df: pd.DataFrame):
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

panel_open("④ 정밀 검토 리스트", "전체/심야/고액/키워드 의심을 탭으로 분리하여 검토 효율을 높입니다.")
tab_all, tab_night, tab_high, tab_susp = st.tabs(["전체", "🌙 심야", "💰 고액", "🔍 키워드 의심"])
with tab_all:
    render_table(filtered_view(df_analyzed, "all"))
with tab_night:
    render_table(filtered_view(df_analyzed, "night"))
with tab_high:
    render_table(filtered_view(df_analyzed, "high"))
with tab_susp:
    render_table(filtered_view(df_analyzed, "suspicious"))
panel_close()


# =========================================================
# 11) 차트 Panel (설치 없이 Streamlit 기본 차트)
# =========================================================
panel_open("⑤ 시각화", "분포/시간대/룰 적발을 시각적으로 제공합니다.")
chart_df = df_analyzed[df_analyzed["P_DT"].notna()].copy()

colA, colB = st.columns(2)
with colA:
    st.markdown("**위험점수 분포**")
    if chart_df.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
    else:
        bins = pd.cut(chart_df["risk_score"], bins=list(range(0, 105, 5)), right=False)
        hist = bins.value_counts().sort_index()
        hist_df = hist.reset_index()
        hist_df.columns = ["score_bin", "count"]
        hist_df["score_bin"] = hist_df["score_bin"].astype(str)
        st.bar_chart(hist_df.set_index("score_bin"))

with colB:
    st.markdown("**시간대별 거래 건수**")
    if chart_df.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
    else:
        hour_counts = chart_df["P_HOUR"].dropna().astype(int).value_counts().sort_index()
        st.bar_chart(hour_counts)

r1, r2, r3 = st.columns(3)
with r1:
    st.metric("🌙 심야", f"{int(df_analyzed['F_NIGHT'].sum()):,}건")
with r2:
    st.metric("💰 고액", f"{int(df_analyzed['F_HIGH'].sum()):,}건")
with r3:
    st.metric("🔍 키워드 의심", f"{int(df_analyzed['F_SUSPICIOUS'].sum()):,}건")
panel_close()


# =========================================================
# 12) 다운로드 Panel
# =========================================================
panel_open("⑥ 보고서 다운로드", "필터 적용/미적용 범위를 선택하여 CSV로 내려받습니다.")
download_mode = st.selectbox(
    "다운로드 범위 선택",
    ["현재(전체 기준)", "심야만", "고액만", "키워드 의심만", "원본+분석 전체(필터 미적용)"],
)

if download_mode == "현재(전체 기준)":
    out_df = filtered_view(df_analyzed, "all")
elif download_mode == "심야만":
    out_df = filtered_view(df_analyzed, "night")
elif download_mode == "고액만":
    out_df = filtered_view(df_analyzed, "high")
elif download_mode == "키워드 의심만":
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
st.caption("※ 모든 UI 컴포넌트(선택값/입력값/파일명)는 다크톤에서 선명하게 표시되도록 통일 보정되어 있습니다.")
panel_close()
