import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from io import BytesIO

# =========================================================
# 0) BUILD INFO
# =========================================================
BUILD = "v4.0-compliance-tabs-download-board"

# =========================================================
# Optional: KR holidays (공휴일 계산)
#   - 설치 권장: pip install holidays
# =========================================================
HAS_HOLIDAYS_LIB = True
try:
    import holidays  # type: ignore
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
# 4) Compliance Audit Engine (운영기준 위반만)
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
            return set(kr.keys())  # datetime.date
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

        user_col = mapping.get("사용자")
        merchant_col = mapping["가맹점"]
        amt_col = mapping["금액"]
        dt_col = mapping["일시"]

        # Normalize
        df["P_AMT"] = ComplianceAudit._parse_amount(df[amt_col])
        df["P_DT"] = pd.to_datetime(df[dt_col], errors="coerce")
        df["P_DATE"] = df["P_DT"].dt.date
        df["P_HOUR"] = df["P_DT"].dt.hour
        df["P_MONTH"] = df["P_DT"].dt.to_period("M").astype(str)

        if user_col is None:
            df["_P_USER"] = "미지정"
            user_col = "_P_USER"

        # Late night
        df["F_NIGHT"] = df["P_HOUR"].apply(lambda h: ComplianceAudit._is_hour_in_range(h, night_start, night_end))

        # Weekend
        if include_weekend:
            df["F_WEEKEND"] = pd.to_datetime(df["P_DT"], errors="coerce").dt.weekday >= 5
        else:
            df["F_WEEKEND"] = False

        # Public holiday
        if include_public_holiday and HAS_HOLIDAYS_LIB:
            years = sorted({d.year for d in df["P_DATE"].dropna().tolist() if isinstance(d, date)})
            hset = ComplianceAudit._build_holiday_set_kr(years)
            df["F_PUBHOL"] = df["P_DATE"].isin(hset)
        else:
            df["F_PUBHOL"] = False

        # Restricted / focus-review industries (merchant keyword)
        kw = [k.strip() for k in restricted_keywords if str(k).strip()]
        if not kw:
            df["F_RESTRICTED"] = False
        else:
            pattern = "|".join([re.escape(k) for k in kw])
            df["F_RESTRICTED"] = df[merchant_col].astype(str).str.contains(pattern, case=False, na=False)

        # Reasons + violation
        def build_reasons(row):
            reasons = []
            if row["F_NIGHT"]:
                reasons.append("🌙 Late night (23~06)")
            if row["F_WEEKEND"]:
                reasons.append("📅 Closed days (weekend)")
            if row["F_PUBHOL"]:
                reasons.append("🎌 Public holiday")
            if row["F_RESTRICTED"]:
                reasons.append("🚫 Limited/Focused industries")
            return " / ".join(reasons)

        df["violation_reason"] = df.apply(build_reasons, axis=1)
        df["IS_VIOLATION"] = df["violation_reason"].astype(str).str.len() > 0

        features = {
            "user_col": user_col,
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
        <div class="hero-sub">운영기준 위반만 선별 · Tabs + Download + Violation Board</div>
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
DEFAULT_RESTRICTED = [
    "노래방", "단란주점", "유흥주점", "나이트", "클럽", "캬바레", "유흥",
    "마사지", "안마", "안마시술소", "사우나", "찜질방", "목욕탕", "피부", "미용", "이용",
    "카지노", "성인용품", "상품권", "면세점",
]

with st.sidebar:
    st.markdown("## ⚙️ Compliance Rules")
    night_range = st.slider("Late night window (hour)", 0, 23, (23, 6))

    include_weekend = st.checkbox("Treat weekends as violation", value=True)
    include_public_holiday = st.checkbox("Treat public holidays as violation (KR)", value=True)

    if include_public_holiday and not HAS_HOLIDAYS_LIB:
        st.warning("Public holiday detection needs `holidays` package. (Rule will be OFF without it)")

    st.divider()
    st.markdown("## 🚫 Limited/Focused industries (keyword)")
    restricted_text = st.text_area(
        "Comma-separated. If merchant name contains keyword → violation.",
        value=", ".join(DEFAULT_RESTRICTED),
        height=120,
    )
    restricted_keywords = [k.strip() for k in restricted_text.split(",") if k.strip()]

    st.divider()
    show_only_violations = st.checkbox("Show violations only (recommended)", value=True)

    st.info("Required: Merchant, Amount, Datetime. (User optional)")

# =========================================================
# 7) MAIN: Upload + Sheet
# =========================================================
colL, colR = st.columns([1, 1], gap="large")

with colL:
    panel_open("① Upload data", "Upload XLSX / CSV")
    uploaded_file = st.file_uploader("Upload corporate card history", type=["csv", "xlsx"])
    panel_close()

with colR:
    if not uploaded_file:
        panel_open("② Sheet select", "After upload, select the sheet")
        st.info("Upload a file on the left.")
        panel_close()

if not uploaded_file:
    soft_divider()
    panel_open("Guide", "Upload a file to start analysis.")
    st.info("After upload, violations will be detected by tabs and downloadable per tab.")
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
            panel_open("② Sheet select", "Pick the sheet that contains data")
            selected_sheet = sheet_names[0] if len(sheet_names) == 1 else st.selectbox("Sheet", sheet_names)
            panel_close()

        df_raw = excel_file.parse(selected_sheet)
    else:
        with colR:
            panel_open("② Sheet select", "CSV does not need sheet selection")
            st.success("CSV uploaded")
            panel_close()

        try:
            df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except Exception:
            df_raw = pd.read_csv(uploaded_file)

    if df_raw is None or df_raw.empty:
        panel_open("Error", "Empty / unreadable file")
        st.error("Uploaded file is empty or unreadable.")
        panel_close()
        st.stop()

    audit = ComplianceAudit()
    mapping = audit.get_standard_mapping(df_raw)

    missing = [k for k in ["가맹점", "금액", "일시"] if k not in mapping]
    if missing:
        soft_divider()
        panel_open("Missing required columns", "Could not map required columns automatically.")
        st.error(f"Missing: {', '.join(missing)}")
        st.write("Columns:", list(df_raw.columns))
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
    panel_open("Processing error", "Exception while processing data")
    st.error(f"⚠️ Error: {e}")
    panel_close()
    st.stop()

soft_divider()

# =========================================================
# 9) Dashboard summary
# =========================================================
panel_open("③ Summary", "Current file violation overview")

total_cnt = len(df_analyzed)
viol_cnt = int(df_analyzed["IS_VIOLATION"].sum())
night_cnt = int(df_analyzed["F_NIGHT"].sum())
weekend_cnt = int(df_analyzed["F_WEEKEND"].sum())
pubhol_cnt = int(df_analyzed["F_PUBHOL"].sum())
rest_cnt = int(df_analyzed["F_RESTRICTED"].sum())

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total rows", f"{total_cnt:,}")
c2.metric("🚨 Violations", f"{viol_cnt:,}")
c3.metric("🌙 Late night", f"{night_cnt:,}")
c4.metric("📅 Closed days", f"{weekend_cnt:,}")
c5.metric("🎌 Holidays", f"{pubhol_cnt:,}")
c6.metric("🚫 Restricted", f"{rest_cnt:,}")

panel_close()

soft_divider()

# =========================================================
# 10) Tabs + Tables (+ Download box + Violation Board)
# =========================================================
rule_cols = features["rule_cols"]
user_col = features["user_col"]
merchant_col = features["merchant_col"]
dt_col = features["dt_col"]

# Display columns (필요 최소 정보 + 위반사유)
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

    df = df.sort_values("P_DT", ascending=False, na_position="last")
    return df

def render_table(df: pd.DataFrame, table_key: str):
    # ✅ Download box (right above table)
    st.markdown("#### ⬇️ Download (current tab)")

    export_df = df[display_cols].copy() if not df.empty else pd.DataFrame(columns=display_cols)
    dl1, dl2 = st.columns([1, 1])

    with dl1:
        st.download_button(
            label="Download CSV (current view)",
            data=export_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"violations_{table_key}.csv",
            mime="text/csv",
            key=f"dl_csv_{table_key}",  # ✅ unique
            use_container_width=True,
        )

    with dl2:
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="data")
        st.download_button(
            label="Download Excel (current view)",
            data=out.getvalue(),
            file_name=f"violations_{table_key}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_xlsx_{table_key}",  # ✅ unique
            use_container_width=True,
        )

    st.caption("※ 현재 탭에 표시된 결과만 다운로드됩니다.")

    if df.empty:
        st.info("No rows for this tab/filter.")
        return

    st.data_editor(
        df[display_cols],
        column_config={
            "P_AMT": st.column_config.NumberColumn("Amount", format="%d"),
            "violation_reason": st.column_config.TextColumn("Reason for violation"),
        },
        use_container_width=True,
        hide_index=True,
        disabled=True,
        key=f"data_editor_{table_key}",  # ✅ unique
    )

panel_open(
    "④ Violation of operating standards list",
    "View violation types separately by tab. Download is available per tab. Violation board is on the right."
)

left, right = st.columns([3.2, 1.2], gap="large")

with right:
    st.markdown("### 📟 Violation Board")
    st.caption("Instant counts for the uploaded file")
    st.metric("🚨 Total Violations", f"{viol_cnt:,}")
    st.metric("🌙 Late Night", f"{night_cnt:,}")
    st.metric("📅 Closed (Weekend)", f"{weekend_cnt:,}")
    st.metric("🎌 Holidays", f"{pubhol_cnt:,}")
    st.metric("🚫 Limited/Focused", f"{rest_cnt:,}")

with left:
    tab_all, tab_night, tab_weekend, tab_pubhol, tab_rest = st.tabs(
        ["All (violations)", "🌙 Late night", "📅Closed days (weekends)", "🎌Holidays", "🚫 Limited/Focused Industries"]
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
# 11) Monthly Summary (optional but useful monthly operation)
# =========================================================
panel_open("⑤ Monthly summary", "Total vs Violations by month")
tmp = df_analyzed.copy()
tmp = tmp[tmp["P_DT"].notna()].copy()

if tmp.empty:
    st.info("No datetime rows for monthly summary.")
else:
    tmp["P_MONTH"] = tmp["P_DT"].dt.to_period("M").astype(str)

    monthly_all = tmp.groupby("P_MONTH", as_index=False)["P_AMT"].sum().rename(columns={"P_AMT": "Monthly total"})
    monthly_viol = tmp[tmp["IS_VIOLATION"] == True].groupby("P_MONTH", as_index=False)["P_AMT"].sum().rename(columns={"P_AMT": "Monthly violations"})
    monthly = monthly_all.merge(monthly_viol, on="P_MONTH", how="left").fillna(0).sort_values("P_MONTH", ascending=False)

    st.dataframe(monthly, use_container_width=True, height=260)

panel_close()

soft_divider()

# =========================================================
# Footer
# =========================================================
st.caption(
    "Note: Public holiday detection requires the `holidays` package in your deployment environment. "
    "Excel download requires `openpyxl`."
)
