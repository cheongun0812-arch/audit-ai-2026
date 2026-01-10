import streamlit as st
import pandas as pd
import re
from datetime import datetime

# =========================================================
# 0) BUILD INFO
# =========================================================
BUILD = "v2.2"

# =========================================================
# 1) PAGE CONFIG
# =========================================================
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")


# =========================================================
# 2) CSS (핵심 수정)
#   - ❌ stToolbar/stHeader display:none 제거 (사이드바 토글 버튼이 여기서 렌더링됨)
#   - ✅ 사이드바 토글 버튼은 강제로 항상 보이게 + 클릭 가능
#   - ✅ FileUploader/Selectbox 텍스트 흐림(blur/opacity) 강제 해제
#   - ✅ 빌드번호 타이틀 오른쪽 박스 표시
# =========================================================
st.markdown(
    f"""
<style>
:root{{
  --bg:#0B0D10;
  --panel:#12151B;
  --panel2:#0E1117;
  --border:#232836;
  --border2:#2D3446;
  --text:#EDEFF4;
  --muted:#B9C2D6;
  --muted2:#8791A6;
  --gold:#D6B25E;
  --shadow: 0 10px 24px rgba(0,0,0,.35);
}}

.stApp{{
  background:
    radial-gradient(1200px 600px at 20% 0%, rgba(214,178,94,.08), transparent 60%),
    radial-gradient(1000px 600px at 90% 10%, rgba(90,132,255,.08), transparent 55%),
    var(--bg);
  color: var(--text);
}}
h1,h2,h3,h4{{ color: var(--text) !important; }}

/* ✅ 상단 여백만 줄이고, toolbar/header는 숨기지 않음 (토글 버튼 살리기 핵심) */
div.block-container{{ padding-top: 10px !important; }}

/* =========================================================
   ✅ 사이드바 토글 버튼(<< / >>) 무조건 표시 + 클릭 가능
   - display/visibility/opacity/pointer-events 강제
   ========================================================= */
[data-testid="collapsedControl"],
button[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"]{{
  position: fixed !important;
  top: 12px !important;
  left: 12px !important;
  z-index: 999999 !important;
  opacity: 1 !important;
  visibility: visible !important;
  display: flex !important;
  pointer-events: auto !important;
}}

[data-testid="collapsedControl"] button,
button[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"]{{
  background: rgba(214,178,94,.18) !important;
  border: 1px solid rgba(214,178,94,.55) !important;
  border-radius: 12px !important;
  width: 38px !important;
  height: 38px !important;
  box-shadow: 0 8px 18px rgba(0,0,0,.35) !important;
}}

[data-testid="collapsedControl"] svg,
button[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] svg,
button[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarCollapseButton"] svg{{
  fill: var(--text) !important;
  stroke: var(--text) !important;
  opacity: 1 !important;
}}

/* ===== Sidebar ===== */
[data-testid="stSidebar"]{{
  background: linear-gradient(180deg, #0E1116 0%, #0A0C10 100%) !important;
  border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] *{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}}
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] .stMarkdown p{{
  color: var(--muted) !important;
  -webkit-text-fill-color: var(--muted) !important;
}}

/* ===== Hero ===== */
.hero{{
  background: linear-gradient(135deg, rgba(214,178,94,.15) 0%, rgba(214,178,94,.06) 30%, rgba(255,255,255,.03) 100%);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px 22px;
  box-shadow: var(--shadow);
  margin-bottom: 12px;
}}
.hero-row{{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 14px;
}}
.hero-left{{ display:flex; align-items:center; gap:10px; }}
.badge{{
  display:inline-flex; align-items:center; justify-content:center;
  width: 36px; height: 36px; border-radius: 12px;
  background: rgba(214,178,94,.18);
  border: 1px solid rgba(214,178,94,.35);
  color: var(--gold);
  font-weight: 900;
}}
.hero-title{{ font-size: 26px; font-weight: 900; letter-spacing: .3px; margin: 0; }}
.hero-sub{{ margin-top: 6px; color: var(--muted); font-size: 13px; }}
.build-box{{
  padding: 8px 12px;
  border-radius: 12px;
  background: rgba(214,178,94,.14);
  border: 1px solid rgba(214,178,94,.45);
  color: var(--gold);
  font-weight: 900;
  font-size: 12px;
  letter-spacing: .2px;
  white-space: nowrap;
}}

/* ===== Panels / Divider ===== */
.panel{{
  background: linear-gradient(180deg, rgba(255,255,255,.03) 0%, rgba(255,255,255,.015) 100%), var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--shadow);
  margin-bottom: 10px;
}}
.panel-title{{ font-weight: 900; margin: 0 0 10px 0; font-size: 14px; letter-spacing: .2px; }}
.panel-sub{{ color: var(--muted2); font-size: 12px; margin: -6px 0 10px 0; }}

.soft-line{{
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(214,178,94,.35), transparent);
  margin: 14px 0;
}}

/* =========================================================
   ✅ 흐림(blur) / 투명(opacity) 강제 제거: 업로더/셀렉트/버튼 전체 커버
   ========================================================= */
[data-testid="stFileUploader"] *,
div[data-baseweb="select"] *,
div[role="listbox"] *,
button * {{
  filter: none !important;
  backdrop-filter: none !important;
  opacity: 1 !important;
  text-shadow: none !important;
}}

/* ===== Selectbox 선명화 (선택값/placeholder 포함) ===== */
div[data-baseweb="select"] > div{{
  background-color: var(--panel2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
}}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  opacity: 1 !important;
}}
/* placeholder가 흐리게 보이는 케이스 방지 */
div[data-baseweb="select"] [data-testid="stMarkdownContainer"] *{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  opacity: 1 !important;
}}

div[role="listbox"]{{
  background: var(--panel2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  box-shadow: 0 18px 30px rgba(0,0,0,.45) !important;
}}
div[role="listbox"] span{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  opacity: 1 !important;
}}

/* ===== FileUploader 선명화 (dropzone/버튼/파일카드) ===== */
[data-testid="stFileUploader"]{{
  background: var(--panel2) !important;
  border: 1px dashed rgba(214,178,94,.55) !important;
  border-radius: 14px !important;
  padding: 12px !important;
}}
[data-testid="stFileUploader"] *{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  opacity: 1 !important;
}}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] label{{
  color: var(--muted) !important;
  -webkit-text-fill-color: var(--muted) !important;
  opacity: 1 !important;
}}

/* Browse files 버튼 대비/텍스트 선명 */
[data-testid="stFileUploader"] button{{
  border-radius: 12px !important;
  border: 1px solid rgba(214,178,94,.75) !important;
  background: rgba(214,178,94,.22) !important;
}}
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] button *{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  opacity: 1 !important;
}}

/* 업로드된 파일 정보(파일명/용량) 선명 */
div[data-testid="stFileUploaderFile"],
div[data-testid="stFileUploaderFile"] *,
div[data-testid="stFileUploaderFileName"],
div[data-testid="stFileUploaderFileName"] *{{
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  opacity: 1 !important;
  filter: none !important;
}}
div[data-testid="stFileUploaderFile"]{{
  background: var(--panel2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
}}

/* ===== Data ===== */
[data-testid="stDataFrame"], [data-testid="stDataEditor"]{{
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  box-shadow: 0 8px 18px rgba(0,0,0,.25);
}}
</style>

<!-- ✅ CSS 반영 확인 배지 -->
<div style="
 position:fixed; top:10px; left:10px; z-index:999999;
 padding:6px 10px; border-radius:10px;
 font-size:12px; font-weight:900; letter-spacing:.2px;
 background:rgba(214,178,94,.18);
 border:1px solid rgba(214,178,94,.55);
 color:#D6B25E;">
 CSS LOADED • UI FIX {BUILD}
</div>
""",
    unsafe_allow_html=True
)


# =========================================================
# 3) UI helpers
# =========================================================
def panel_open(title: str, subtitle: str | None = None):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="panel-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="panel-sub">{subtitle}</div>', unsafe_allow_html=True)

def panel_close():
    st.markdown("</div>", unsafe_allow_html=True)

def soft_divider():
    st.markdown('<div class="soft-line"></div>', unsafe_allow_html=True)


# =========================================================
# 4) Audit Engine
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
            .str.replace(r"[^0-9\\-]", "", regex=True)
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
        df["P_HOUR"] = df["P_DT"].dt.hour

        if "사용자" not in mapping:
            df["_P_USER"] = "미지정"
            mapping["사용자"] = "_P_USER"

        df["F_NIGHT"] = df["P_HOUR"].apply(lambda h: AuditSystem._is_hour_in_range(h, night_start, night_end))
        df["F_HIGH"] = df["P_AMT"] >= int(high_amount_limit)

        kw = [k.strip() for k in suspicious_keywords if str(k).strip()]
        if not kw:
            df["F_SUSPICIOUS"] = False
        else:
            pattern = "|".join([re.escape(k) for k in kw])
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
                reasons.append("🔍키워드의심")
            return ", ".join(reasons)

        df["violation"] = df.apply(build_reasons, axis=1)

        features = {
            "user_col": mapping["사용자"],
            "merchant_col": merchant_col,
            "dt_col": dt_col,
            "rule_cols": {"night": "F_NIGHT", "high": "F_HIGH", "suspicious": "F_SUSPICIOUS"},
        }
        return df, features


# =========================================================
# 5) HERO
# =========================================================
st.markdown(
    f"""
<div class="hero">
  <div class="hero-row">
    <div class="hero-left">
      <div class="badge">🛡️</div>
      <div>
        <div class="hero-title">2026 AUDIT AI PORTAL</div>
        <div class="hero-sub">통합 감사 데이터 분석 시스템 · Dignified UI Edition (다크톤/패널 구조/가독성 강화)</div>
      </div>
    </div>
    <div class="build-box">BUILD {BUILD}</div>
  </div>
</div>
""",
    unsafe_allow_html=True
)

soft_divider()


# =========================================================
# 6) SIDEBAR
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
    w_susp = st.number_input("키워드 의심 가중치", value=30, step=5, min_value=0, max_value=100)

    st.divider()

    st.markdown("## 🧰 출력/필터")
    min_score = st.slider("표시 최소 위험점수", 0, 100, 40, step=5)

    st.info("필수 컬럼: **가맹점(상호/거래처)**, **금액**, **일시**\n\n※ 사용자 컬럼이 없으면 **미지정**으로 표시됩니다.")


# =========================================================
# 7) Upload
# =========================================================
panel_open("① 데이터 업로드", "XLSX 또는 CSV 업로드 후 자동으로 시트 선택/분석이 진행됩니다.")
uploaded_file = st.file_uploader("가공된 파일을 업로드하세요.", type=["csv", "xlsx"])
panel_close()

if not uploaded_file:
    panel_open("가이드", "업로드 전 단계입니다.")
    st.info("파일 업로드 후 분석이 시작됩니다. (업로더/시트 선택 텍스트는 기본 선명 표시)")
    panel_close()
    st.stop()

soft_divider()


# =========================================================
# 8) Load + Analyze
# =========================================================
try:
    if uploaded_file.name.lower().endswith(".xlsx"):
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names

        panel_open("② 시트 선택", "데이터가 포함된 시트를 선택하세요.")
        selected_sheet = sheet_names[0] if len(sheet_names) == 1 else st.selectbox("📝 데이터가 있는 시트를 선택하세요", sheet_names)
        panel_close()

        df_raw = excel_file.parse(selected_sheet)
    else:
        try:
            df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except Exception:
            df_raw = pd.read_csv(uploaded_file)

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

soft_divider()


# =========================================================
# 9) Dashboard
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
