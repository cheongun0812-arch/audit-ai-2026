import streamlit as st
import pandas as pd
import re
from datetime import datetime, date

# =========================================================
# 0) BUILD INFO
# =========================================================
BUILD = "v3.0-compliance-only"

# =========================================================
# Optional: KR holidays (공휴일 계산)
#   - 설치 권장: pip install holidays
# =========================================================
HAS_HOLIDAYS_LIB = True
try:
    import holidays
except Exception:
    HAS_HOLIDAYS_LIB = False


# =========================================================
# 1) PAGE CONFIG
# =========================================================
st.set_page_config(page_title="2026 AUDIT (corporate card compliance) AI PORTAL", layout="wide")

# =========================================================
# 2) CSS (기존 디자인 유지)
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

  --mainInputBg: #F4F6FB;
  --mainInputText: #111827;
  --mainInputSub: #374151;

  --sideInputBg: #0E1117;
  --sideInputText: #EDEFF4;
  --sideInputSub: #B9C2D6;

  --spinBg: #2563EB;
  --spinBgHover: #1D4ED8;
  --spinText: #FFFFFF;
}}

.stApp{{
  background:
    radial-gradient(1200px 600px at 20% 0%, rgba(214,178,94,.08), transparent 60%),
    radial-gradient(1000px 600px at 90% 10%, rgba(90,132,255,.08), transparent 55%),
    var(--bg);
  color: var(--text);
}}
h1,h2,h3,h4{{ color: var(--text) !important; }}

div.block-container{{
  padding-top: 88px !important;
  padding-bottom: 26px !important;
}}

[data-testid="collapsedControl"],
button[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"]{{
  position: fixed !important;
  top: 22px !important;
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

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea{{
  background: var(--sideInputBg) !important;
  color: var(--sideInputText) !important;
  -webkit-text-fill-color: var(--sideInputText) !important;
  border: 1px solid var(--border2) !important;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption{{
  color: var(--sideInputSub) !important;
  -webkit-text-fill-color: var(--sideInputSub) !important;
}}

[data-testid="stSidebar"] div[data-baseweb="select"] > div{{
  background: var(--sideInputBg) !important;
  border: 1px solid var(--border2) !important;
}}
[data-testid="stSidebar"] div[data-baseweb="select"] span,
[data-testid="stSidebar"] div[data-baseweb="select"] input{{
  color: var(--sideInputText) !important;
  -webkit-text-fill-color: var(--sideInputText) !important;
  font-weight: 700 !important;
}}

[data-testid="stSidebar"] div[data-baseweb="input"] button{{
  background: var(--spinBg) !important;
  border: 1px solid rgba(255,255,255,.15) !important;
  border-radius: 10px !important;
  opacity: 1 !important;
}}
[data-testid="stSidebar"] div[data-baseweb="input"] button:hover{{
  background: var(--spinBgHover) !important;
}}
[data-testid="stSidebar"] div[data-baseweb="input"] button svg{{
  fill: var(--spinText) !important;
  stroke: var(--spinText) !important;
  opacity: 1 !important;
}}
[data-testid="stSidebar"] div[data-baseweb="input"] button{{
  min-width: 32px !important;
  min-height: 32px !important;
}}

.hero{{
  background: linear-gradient(135deg, rgba(214,178,94,.15) 0%, rgba(214,178,94,.06) 30%, rgba(255,255,255,.03) 100%);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px 22px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
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

div[data-baseweb="select"] > div{{
  background-color: var(--mainInputBg) !important;
  border: 1px solid rgba(214,178,94,.55) !important;
  border-radius: 12px !important;
}}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input{{
  color: var(--mainInputText) !important;
  -webkit-text-fill-color: var(--mainInputText) !important;
  opacity: 1 !important;
  font-weight: 800 !important;
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
  font-weight: 650 !important;
}}

[data-testid="stFileUploader"]{{
  background: var(--mainInputBg) !important;
  border: 1px dashed rgba(214,178,94,.75) !important;
  border-radius: 14px !important;
  padding: 12px !important;
}}
[data-testid="stFileUploader"] *{{
  color: var(--mainInputText) !important;
  -webkit-text-fill-color: var(--mainInputText) !important;
  opacity: 1 !important;
}}

[data-testid="stDataFrame"], [data-testid="stDataEditor"]{{
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  box-shadow: 0 8px 18px rgba(0,0,0,.25);
}}
</style>
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
# 4) Compliance Audit Engine
#    - "운영기준 위반만" 식별 (심야/휴일/공휴일/제한·중점검토 업종)
# =========================================================
class ComplianceAudit:
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
        for key, aliases in ComplianceAudit.STANDARD_COLS.items():
            for c in cols:
                if c in aliases:
                    mapping[key] = c
                    break
        return mapping

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
    def _is_hour_in_range(hour: float, start: int, end: int) -> bool:
        if pd.isna(hour):
            return False
        h = int(hour)
        if start <= end:
            return start <= h <= end
        return (h >= start) or (h <= end)

    @staticmethod
    def _build_holiday_set_kr(years: list[int]) -> set[date]:
        if not HAS_HOLIDAYS_LIB:
            return set()
        try:
            kr = holidays.KR(years=years)
            # keys are datetime.date
            return set(kr.keys())
        except Exception:
            return set()

    @staticmethod
    def analyze(
        df: pd.DataFrame,
        mapping: dict,
        night_start: int,
        night_end: int,
        include_weekend: bool,
        include_public_holiday: bool,
        restricted_keywords: list[str],
    ):
        df = df.copy()
        merchant_col = mapping["가맹점"]
        amt_col = mapping["금액"]
        dt_col = mapping["일시"]

        # Normalize
        df["P_AMT"] = ComplianceAudit._parse_amount(df[amt_col])
        df["P_DT"] = pd.to_datetime(df[dt_col], errors="coerce")
        df["P_DATE"] = df["P_DT"].dt.date
        df["P_HOUR"] = df["P_DT"].dt.hour
        df["P_MONTH"] = df["P_DT"].dt.to_period("M").astype(str)

        # User missing -> "미지정"
        if "사용자" not in mapping:
            df["_P_USER"] = "미지정"
            mapping["사용자"] = "_P_USER"

        # Night rule (23~06 default per standard)
        df["F_NIGHT"] = df["P_HOUR"].apply(lambda h: ComplianceAudit._is_hour_in_range(h, night_start, night_end))

        # Weekend rule
        if include_weekend:
            # weekday: Mon=0..Sun=6
            df["F_WEEKEND"] = pd.to_datetime(df["P_DT"], errors="coerce").dt.weekday >= 5
        else:
            df["F_WEEKEND"] = False

        # Public holiday rule
        if include_public_holiday and HAS_HOLIDAYS_LIB:
            years = sorted({d.year for d in df["P_DATE"].dropna().tolist() if isinstance(d, date)})
            hset = ComplianceAudit._build_holiday_set_kr(years)
            df["F_PUBHOL"] = df["P_DATE"].isin(hset)
        else:
            df["F_PUBHOL"] = False

        # Restricted / focus-review industries (merchant-name keyword match)
        kw = [k.strip() for k in restricted_keywords if str(k).strip()]
        if not kw:
            df["F_RESTRICTED"] = False
        else:
            pattern = "|".join([re.escape(k) for k in kw])
            df["F_RESTRICTED"] = df[merchant_col].astype(str).str.contains(pattern, case=False, na=False)

        # Build violation reasons (운영기준 위반만)
        def build_reasons(row):
            reasons = []
            if row["F_NIGHT"]:
                reasons.append("🌙 심야(23~06)")
            if row["F_WEEKEND"]:
                reasons.append("📅 휴무일(주말)")
            if row["F_PUBHOL"]:
                reasons.append("🎌 공휴일")
            if row["F_RESTRICTED"]:
                reasons.append("🚫 제한/중점 업종(가맹점 키워드)")
            return " / ".join(reasons)

        df["violation_reason"] = df.apply(build_reasons, axis=1)
        df["IS_VIOLATION"] = df["violation_reason"].astype(str).str.len() > 0

        features = {
            "user_col": mapping["사용자"],
            "merchant_col": merchant_col,
            "amt_col": amt_col,
            "dt_col": dt_col,
            "rule_cols": {
                "night": "F_NIGHT",
                "weekend": "F_WEEKEND",
                "pubhol": "F_PUBHOL",
                "restricted": "F_RESTRICTED",
                "any": "IS_VIOLATION",
            },
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
        <div class="hero-title">2026 AUDIT (corporate card compliance) AI PORTAL</div>
        <div class="hero-sub">재원운영기준 기반 · 운영기준 위반(심야/휴무일/공휴일/제한·중점 업종)만 선별</div>
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
# 6) SIDEBAR (운영기준 중심)
# =========================================================
# 기본 제한 업종 키워드(문서의 업종명 그대로 반영)
DEFAULT_RESTRICTED = [
    # 유흥업종
    "노래방", "단란주점", "유흥주점", "나이트클럽", "요정", "캬바레", "유흥",
    # 위생업종(대인서비스 포함)
    "찜질방", "목욕탕", "사우나", "안마", "안마시술소", "발마사지", "피부미용", "미용", "이용원",
    "한의원", "한약방", "유사의료",
    # 레저업종
    "카지노", "헬스클럽", "총포",
    # 상품권/면세점
    "상품권", "면세점", "전자상거래상품권", "PG상품권", "오픈마켓상품권",
    # 기타업종(예시들)
    "귀금속", "시계", "자동차판매", "중고자동차", "오토바이", "성인용품", "동물병원",
    "등록금", "학원", "보험", "관리비", "결혼서비스", "장의서비스", "독서실", "유학원", "담배자판기",
    # 유통/쇼핑(예시)
    "인터넷PG", "전자상거래PG", "인터넷종합", "종합Mall", "골프대행",
]

with st.sidebar:
    st.markdown("## ⚙️ 운영기준(Compliance) 룰")
    st.caption("사용 주의 시간(기준): 23시~06시 / 휴무일·공휴일 사용 주의(사후 모니터링)")

    # 문서 기준(23~06) 기본값
    night_range = st.slider("심야 시간(주요 점검)", 0, 23, (23, 6))

    include_weekend = st.checkbox("휴무일(주말) 위반으로 분류", value=True)
    include_public_holiday = st.checkbox("공휴일 위반으로 분류(대한민국)", value=True)

    if include_public_holiday and not HAS_HOLIDAYS_LIB:
        st.warning("공휴일 자동판정: `pip install holidays` 설치 시 활성화됩니다. (미설치 시 공휴일 룰은 꺼집니다)")

    st.divider()
    st.markdown("## 🚫 제한/중점검토 업종 키워드")
    restricted_text = st.text_area(
        "쉼표(,)로 구분해서 입력 (가맹점명에 포함되면 적발)",
        value=", ".join(DEFAULT_RESTRICTED),
        height=150,
    )
    restricted_keywords = [k.strip() for k in restricted_text.split(",") if k.strip()]

    st.divider()
    st.markdown("## 🧰 보기 옵션")
    show_only_violations = st.checkbox("위반만 표시(추천)", value=True)

    st.info(
        "필수 컬럼: **가맹점**, **금액**, **일시**\n\n"
        "※ 사용자 컬럼이 없으면 **미지정**으로 표시됩니다."
    )

# =========================================================
# 7) MAIN: 업로드/시트선택 50:50
# =========================================================
colL, colR = st.columns([1, 1], gap="large")

with colL:
    panel_open("① 데이터 업로드", "XLSX 또는 CSV 업로드 후 운영기준 위반만 선별합니다.")
    uploaded_file = st.file_uploader("카드 사용내역 파일을 업로드하세요.", type=["csv", "xlsx"])
    panel_close()

with colR:
    if not uploaded_file:
        panel_open("② 시트 선택", "파일 업로드 후, 시트를 선택할 수 있습니다.")
        st.info("좌측에서 파일을 업로드하세요.")
        panel_close()

if not uploaded_file:
    soft_divider()
    panel_open("가이드", "업로드 전 단계입니다.")
    st.info("파일을 업로드하면 운영기준 위반 선별이 시작됩니다.")
    panel_close()
    st.stop()

# =========================================================
# 8) Load + Analyze
# =========================================================
try:
    selected_sheet = None

    if uploaded_file.name.lower().endswith(".xlsx"):
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names

        with colR:
            panel_open("② 시트 선택", "데이터가 포함된 시트를 선택하세요.")
            selected_sheet = sheet_names[0] if len(sheet_names) == 1 else st.selectbox(
                "📝 데이터가 있는 시트를 선택하세요",
                sheet_names
            )
            panel_close()

        df_raw = excel_file.parse(selected_sheet)

    else:
        with colR:
            panel_open("② 시트 선택", "CSV 파일은 시트 선택이 필요 없습니다.")
            st.success("CSV 업로드 완료: 시트 선택 단계 생략")
            panel_close()

        try:
            df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except Exception:
            df_raw = pd.read_csv(uploaded_file)

    if df_raw is None or df_raw.empty:
        panel_open("오류", "파일이 비어 있거나 읽을 수 없습니다.")
        st.error("업로드된 파일이 비어있거나 읽을 수 없습니다.")
        panel_close()
        st.stop()

    audit = ComplianceAudit()
    mapping = audit.get_standard_mapping(df_raw)

    missing = [k for k in ["가맹점", "금액", "일시"] if k not in mapping]
    if missing:
        soft_divider()
        panel_open("필수 컬럼 확인", "현재 파일은 분석에 필요한 컬럼 매핑이 되지 않습니다.")
        st.error("필수 컬럼을 찾을 수 없습니다.")
        st.write("누락:", ", ".join(missing))
        st.write("현재 컬럼 목록:", list(df_raw.columns))
        panel_close()
        st.stop()

    df_analyzed, features = audit.analyze(
        df_raw,
        mapping=mapping,
        night_start=night_range[0],
        night_end=night_range[1],
        include_weekend=include_weekend,
        include_public_holiday=include_public_holiday,
        restricted_keywords=restricted_keywords,
    )

except Exception as e:
    soft_divider()
    panel_open("처리 오류", "데이터 처리 중 예외가 발생했습니다.")
    st.error(f"⚠️ 처리 중 오류: {e}")
    panel_close()
    st.stop()

soft_divider()

# =========================================================
# 9) Dashboard (운영기준 위반 중심)
# =========================================================
panel_open("③ 운영기준 위반 요약 대시보드", "심야/휴무일/공휴일/제한업종 위반만 집계합니다.")
total_cnt = len(df_analyzed)
viol_cnt = int(df_analyzed["IS_VIOLATION"].sum())
night_cnt = int(df_analyzed["F_NIGHT"].sum())
weekend_cnt = int(df_analyzed["F_WEEKEND"].sum())
pubhol_cnt = int(df_analyzed["F_PUBHOL"].sum())
rest_cnt = int(df_analyzed["F_RESTRICTED"].sum())

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("총 건수", f"{total_cnt:,}건")
with c2:
    st.metric("위반(전체)", f"{viol_cnt:,}건")
with c3:
    st.metric("🌙 심야", f"{night_cnt:,}건")
with c4:
    st.metric("📅 휴무일(주말)", f"{weekend_cnt:,}건")
with c5:
    st.metric("🎌 공휴일", f"{pubhol_cnt:,}건")
with c6:
    st.metric("🚫 제한/중점 업종", f"{rest_cnt:,}건")
panel_close()

soft_divider()

# =========================================================
# 10) Tables
# =========================================================
rule_cols = features["rule_cols"]
user_col = features["user_col"]
merchant_col = features["merchant_col"]
dt_col = features["dt_col"]

# 표시 컬럼: 운영기준 위반 확인에 필요한 최소 정보
display_cols = [user_col, merchant_col, "P_AMT", dt_col, "P_MONTH", "violation_reason"]

def filtered_view(base: pd.DataFrame, mode: str) -> pd.DataFrame:
    df = base.copy()

    if show_only_violations:
        df = df[df["IS_VIOLATION"] == True]

    if mode == "all":
        pass
    elif mode == "night":
        df = df[df[rule_cols["night"]] == True]
    elif mode == "weekend":
        df = df[df[rule_cols["weekend"]] == True]
    elif mode == "pubhol":
        df = df[df[rule_cols["pubhol"]] == True]
    elif mode == "restricted":
        df = df[df[rule_cols["restricted"]] == True]

    # 최신순 정렬
    df = df.sort_values("P_DT", ascending=False, na_position="last")
    return df

def render_table(df: pd.DataFrame, table_key: str):
    if df.empty:
        st.info("조건에 해당하는 데이터가 없습니다.")
        return

    st.data_editor(
        df[display_cols],
        column_config={
            "P_AMT": st.column_config.NumberColumn("결제금액", format="%d원"),
            "violation_reason": st.column_config.TextColumn("위반 사유"),
        },
        use_container_width=True,
        hide_index=True,
        disabled=True,
        key=f"data_editor_{table_key}",  # ✅ DuplicateElementId 방지
    )

panel_open("④ 운영기준 위반 리스트", "탭별로 위반 유형을 분리하여 확인합니다.")
tab_all, tab_night, tab_weekend, tab_pubhol, tab_rest = st.tabs(
    ["전체(위반)", "🌙 심야", "📅 휴무일(주말)", "🎌 공휴일", "🚫 제한/중점 업종"]
)

with tab_all:
    render_table(filtered_view(df_analyzed, "all"), "all")
with tab_night:
    render_table(filtered_view(df_analyzed, "night"), "night")
with tab_weekend:
    render_table(filtered_view(df_analyzed, "weekend"), "weekend")
with tab_pubhol:
    render_table(filtered_view(df_analyzed, "pubhol"), "pubhol")
with tab_rest:
    render_table(filtered_view(df_analyzed, "restricted"), "restricted")
panel_close()

soft_divider()

# =========================================================
# 11) Monthly Summary (월별 합계/월별 위반 합계)
# =========================================================
panel_open("⑤ 월별 집계", "매월 반복 감사 운영을 위해 월별 집계(전체/위반)를 제공합니다.")
tmp = df_analyzed.copy()
tmp["P_MONTH"] = tmp["P_DT"].dt.to_period("M").astype(str)

monthly_all = tmp.groupby("P_MONTH", as_index=False)["P_AMT"].sum().rename(columns={"P_AMT": "월합계(전체)"})
monthly_viol = tmp[tmp["IS_VIOLATION"] == True].groupby("P_MONTH", as_index=False)["P_AMT"].sum().rename(columns={"P_AMT": "월합계(위반)"})
monthly_cnt_all = tmp.groupby("P_MONTH", as_index=False).size().rename(columns={"size": "월건수(전체)"})
monthly_cnt_viol = tmp[tmp["IS_VIOLATION"] == True].groupby("P_MONTH", as_index=False).size().rename(columns={"size": "월건수(위반)"})

monthly = monthly_all.merge(monthly_viol, on="P_MONTH", how="left")
monthly = monthly.merge(monthly_cnt_all, on="P_MONTH", how="left")
monthly = monthly.merge(monthly_cnt_viol, on="P_MONTH", how="left")
monthly = monthly.fillna(0)
monthly = monthly.sort_values("P_MONTH", ascending=False)

st.dataframe(monthly, use_container_width=True, height=280)

panel_close()

soft_divider()

# =========================================================
# 12) Download (운영기준 위반만 기본)
# =========================================================
panel_open("⑥ 다운로드", "운영기준 위반 내역 및 월별 집계를 내려받습니다.")

download_mode = st.selectbox(
    "다운로드 범위 선택",
    ["위반만(전체)", "심야만", "휴무일(주말)만", "공휴일만", "제한/중점 업종만", "원본+분석 전체"],
)

if download_mode == "위반만(전체)":
    out_df = filtered_view(df_analyzed, "all")
elif download_mode == "심야만":
    out_df = filtered_view(df_analyzed, "night")
elif download_mode == "휴무일(주말)만":
    out_df = filtered_view(df_analyzed, "weekend")
elif download_mode == "공휴일만":
    out_df = filtered_view(df_analyzed, "pubhol")
elif download_mode == "제한/중점 업종만":
    out_df = filtered_view(df_analyzed, "restricted")
else:
    out_df = df_analyzed.copy()

remove_temp = st.checkbox("임시 컬럼(_P_*) 제거 후 다운로드", value=True)
final_out = out_df.drop(columns=[c for c in out_df.columns if c.startswith("_P_")], errors="ignore") if remove_temp else out_df

csv_bytes = final_out.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ CSV 다운로드",
    data=csv_bytes,
    file_name=f"Compliance_Violations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)

# 월별 집계도 함께 내려받기(별도 버튼)
monthly_csv = monthly.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ 월별 집계 CSV 다운로드",
    data=monthly_csv,
    file_name=f"Compliance_Monthly_Summary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)

panel_close()

# =========================================================
# Footer note (기준 출처 표시)
# =========================================================
st.caption(
    "※ 점검 기준: 재원운영기준(Compliance) 문서의 '사용 주의 시간(23~06), 휴무일/공휴일, 제한·중점 업종' 항목을 기반으로 자동 분류합니다."
)
