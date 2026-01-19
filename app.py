import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 보색 대비 및 시각적 레이아웃 디자인 (v5.8 디자인 유지)
# =========================================================
st.set_page_config(page_title="2026 Audit System", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: #111111 !important; font-weight: 800 !important;
    }
    h1, h2, h3, .stMarkdown p, .stTabs [data-baseweb="tab"], label {
        color: #FFFFFF !important;
    }
    .main-white-text { color: #FFFFFF !important; font-weight: 700 !important; }
    [data-testid="stFileUploaderLabel"] p, [data-testid="stFileUploaderFileName"], 
    [data-testid="stFileUploaderFileData"] > div, div[data-testid="stFileUploader"] small { 
        color: #FFFFFF !important; 
    }
    .hero {
        background: #1A1E26; border-left: 5px solid #FFD700;
        padding: 20px; margin-bottom: 25px;
    }
    .integrated-metric-card {
        background: #FFFFFF; border-radius: 12px; padding: 20px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-main { border-right: 2px solid #EEEEEE; padding-right: 30px; }
    .metric-label { color: #333333; font-size: 1.1rem; font-weight: 700; margin-bottom: 5px; }
    .metric-value { color: #D62728; font-size: 2.2rem; font-weight: 900; line-height: 1; }
    .metric-sub-container { display: flex; gap: 35px; padding-left: 30px; flex-grow: 1; justify-content: space-around; }
    .sub-item { text-align: center; }
    .sub-label { color: #666666; font-size: 0.9rem; font-weight: 700; margin-bottom: 3px; }
    .sub-value { color: #111111; font-size: 1.3rem; font-weight: 800; }
    [data-testid="stMetric"] { background: #FFFFFF; border-radius: 10px; padding: 15px; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #111111 !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 분석 엔진 (법인카드 & 주유비 통합)
# =========================================================
class CombinedAuditEngine:
    @staticmethod
    def run_card_audit(df, keywords):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        def check_compliance(row):
            user, merchant = str(row[u_col]), str(row[m_col])
            if "차량운전비" in user: return False
            if "카카오업무택시" in merchant or "카카오T비즈" in merchant: return False
            for kw in keywords:
                if kw in merchant:
                    if kw == "주점" and re.search(r"[가-힣]주점$", merchant): continue
                    return True
            return False

        df['F_RESTRICT'] = df.apply(check_compliance, axis=1)
        is_car_fee = df[u_col].astype(str).str.contains("차량운전비", na=False)
        df.loc[is_car_fee, ['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']] = False
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫금지업종")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

    @staticmethod
    def run_fuel_audit(df, avg_price=1650):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        
        # 주유비 특화 로직: 역산 및 휴일 검증
        df['EST_LITER'] = df['P_AMT'] / avg_price
        df['F_OVER_CAP'] = df['EST_LITER'] > 75 # 임시 기준 (내일 제원 DB 연동 예정)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 주유비는 '차량운전비'를 제외하지 않고 오히려 분석 대상으로 삼음
        df['IS_VIOLATION'] = df[['F_OVER_CAP', 'F_WEEKEND']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_OVER_CAP']: r.append("⛽용량초과의심")
            if row['F_WEEKEND']: r.append("📅휴일주유")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

# =========================================================
# 3) 화면 구성 및 메뉴 분리
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ Audit Menu")
    menu = st.radio("검증 대상 선택", ["💳 법인카드 모니터링", "⛽ 차량주유 모니터링"])
    st.divider()
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    
    if menu == "💳 법인카드 모니터링":
        kw_input = st.text_area("🚫 집중 모니터링 업종", "주점, 노래방, 유흥, 마사지, 골프장, 사우나, 귀금속, 백화점, 면세점", height=150)
        keywords = [k.strip() for k in kw_input.split(",")]
    else:
        fuel_price = st.number_input("⛽ 리터당 평균 유가(원)", value=1650)

if admin_pw != "ktmos0402!":
    st.warning("인증이 필요합니다.")
    st.stop()

# 히어로 섹션 제목 동적 변경
title = "Card Audit AI" if menu == "💳 법인카드 모니터링" else "Fuel Audit AI"
subtitle = "법인카드 검증 모드" if menu == "💳 법인카드 모니터링" else "차량 주유비 검증 모드"

st.markdown(f"""
<div class="hero">
    <h1 style="margin:0;">🛡️ {title}</h1>
    <p style="color:#FFD700; margin:5px 0 0 0;">{subtitle} v6.2</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(f"{menu} 내역 파일 업로드", type=['xlsx', 'csv'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    engine = CombinedAuditEngine()
    
    if menu == "💳 법인카드 모니터링":
        df_final = engine.run_card_audit(df_raw, keywords)
        night_n, week_n, rest_n = df_final["F_NIGHT"].sum(), df_final["F_WEEKEND"].sum(), df_final["F_RESTRICT"].sum()
        sub_labels = ["🌙 심야", "📅 휴일", "🚫 업종"]
        sub_values = [night_n, week_n, rest_n]
    else:
        df_final = engine.run_fuel_audit(df_raw, fuel_price)
        over_n, week_n = df_final["F_OVER_CAP"].sum(), df_final["F_WEEKEND"].sum()
        sub_labels = ["⛽ 용량초과", "📅 휴일주유", ""]
        sub_values = [over_n, week_n, 0]

    viol_df = df_final[df_final['IS_VIOLATION']]
    
    # --- 통합 지표 레이아웃 (v5.8 디자인 100% 유지) ---
    c1, c2, c3 = st.columns([1.2, 3.5, 1.5])
    with c1: st.metric("🔍 총 검토 내역", f"{len(df_final):,}건")
    with c2:
        st.markdown(f"""
            <div class="integrated-metric-card">
                <div class="metric-main">
                    <div class="metric-label">🚨 검토 필요 건</div>
                    <div class="metric-value">{len(viol_df):,}건</div>
                </div>
                <div class="metric-sub-container">
                    <div class="sub-item"><div class="sub-label">{sub_labels[0]}</div><div class="sub-value">{sub_values[0]}건</div></div>
                    <div class="sub-item"><div class="sub-label">{sub_labels[1]}</div><div class="sub-value">{sub_values[1]}건</div></div>
                    {"<div class='sub-item'><div class='sub-label'>" + sub_labels[2] + "</div><div class='sub-value'>" + str(sub_values[2]) + "건</div></div>" if sub_labels[2] else ""}
                </div>
            </div>
        """, unsafe_allow_html=True)
    with c3: st.metric("💰 검토 금액 합계", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.markdown("---")
    tab1, tab2 = st.tabs(["📋 검토 필요 내역", "📊 사용자별 분석"])
    with tab1:
        st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)
    with tab2:
        st.markdown('<p class="main-white-text">👤 사용자별 추출 건수 (그래프 클릭 시 하단 상세 표시)</p>', unsafe_allow_html=True)
        user_stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
        fig = px.bar(user_stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
        sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        if sel and sel.get("selection") and sel["selection"]["points"]:
            user = sel["selection"]["points"][0]["x"]
            st.markdown(f'<h3 style="color:#FFD700 !important; margin-top:20px;">📄 {user} 님의 상세 내역</h3>', unsafe_allow_html=True)
            st.dataframe(viol_df[viol_df['사용자'] == user], use_container_width=True)

    csv_out = df_final.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 전체 분석 결과 다운로드 (CSV)", csv_out, "Audit_Result.csv", use_container_width=True)
