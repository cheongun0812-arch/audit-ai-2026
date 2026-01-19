import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px

# 1. 시인성 극대화 디자인 (High-Contrast Dark Mode)
st.set_page_config(page_title="2026 Integrated Audit", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] * { color: #111111 !important; font-weight: 800 !important; }
    h1, h2, h3, p, label, .stMarkdown { color: #FFFFFF !important; }
    .hero { background: #1A1E26; border-left: 5px solid #FFD700; padding: 20px; margin-bottom: 25px; }
    [data-testid="stMetric"] { background: #FFFFFF; border-radius: 10px; padding: 15px; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #D62728 !important; font-weight: 900 !important; }
    .integrated-card { background: #FFFFFF; border-radius: 12px; padding: 20px; display: flex; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .sub-item { text-align: center; padding: 0 20px; border-left: 1px solid #EEE; }
    [data-testid="stFileUploaderLabel"] p, [data-testid="stFileUploaderFileName"], div[data-testid="stFileUploader"] small { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# 2. 분석 엔진 (일반 법인카드 & 차량 주유비)
class IntegratedAuditEngine:
    # [임시 DB] 내일 자료 업로드 전까지 사용할 주요 차종 제원
    FUEL_CAPACITY_DB = {
        "그랜저": 60, "아반떼": 47, "쏘나타": 60, "G80": 73, "GV80": 80,
        "카니발": 72, "스타리아": 75, "싼타페": 67, "투싼": 54, "아이오닉": 0, # 전기차 예외
        "K5": 60, "K8": 60, "EV6": 0, "봉고": 65, "포터": 65
    }

    @staticmethod
    def run_card_audit(df, keywords):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        def check(row):
            user, merchant = str(row[u_col]), str(row[m_col])
            if "차량운전비" in user or "카카오" in merchant: return False
            for kw in keywords:
                if kw in merchant:
                    if kw == "주점" and re.search(r"[가-힣]주점$", merchant): continue
                    return True
            return False
        
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        df['F_RESTRICT'] = df.apply(check, axis=1)
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫업종")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

    @staticmethod
    def run_fuel_audit(df, avg_price=1650):
        # 주유비 전용 분석: 역산을 통한 유량 검증
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        
        # 1. 주유량 역산 (금액 / 평균단가)
        df['EST_LITER'] = df['P_AMT'] / avg_price
        
        # 2. 용량 초과 검증 (차종별 DB 대조 - 임시로 75L 초과 시 의심)
        # 내일 차량 리스트 업로드 시 이 부분이 차종별로 정밀하게 변합니다.
        df['F_OVER_CAP'] = df['EST_LITER'] > 75 
        
        # 3. 휴일 주유 검증
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        df['IS_VIOLATION'] = df[['F_OVER_CAP', 'F_WEEKEND']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_OVER_CAP']: r.append("⛽용량초과의심")
            if row['F_WEEKEND']: r.append("📅휴일주유")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

# 3. 화면 구성
st.markdown('<div class="hero"><h1>🛡️ Integrated Audit AI</h1><p style="color:#FFD700;">법인카드 & 주유비 통합 모니터링 시스템 v6.0</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ 설정")
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    st.divider()
    menu = st.radio("검증 메뉴 선택", ["💳 일반 법인카드", "⛽ 차량주유카드"])
    st.divider()
    kw_input = st.text_area("🚫 금지 키워드", "주점,노래방,유흥,마사지,골프장,사우나,귀금속,백화점,면세점", height=100)
    keywords = [k.strip() for k in kw_input.split(",")]
    fuel_price = st.number_input("⛽ 현재 평균 유가(원)", value=1650)

if admin_pw == "ktmos0402!" and (uploaded_file := st.file_uploader("검증할 엑셀/CSV 파일 업로드", type=['xlsx', 'csv'])):
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if menu == "💳 일반 법인카드":
        df_final = IntegratedAuditEngine.run_card_audit(df_raw, keywords)
    else:
        df_final = IntegratedAuditEngine.run_fuel_audit(df_raw, fuel_price)
        
    viol_df = df_final[df_final['IS_VIOLATION']]
    
    # 상단 지표
    c1, c2, c3 = st.columns([1, 3, 1.5])
    c1.metric("🔍 전체 내역", f"{len(df_final):,}건")
    with c2:
        st.markdown(f"""<div class="integrated-card">
            <div style="padding-right:20px;">
                <div style="color:#333; font-weight:700;">🚨 검토 필요</div>
                <div style="color:#D62728; font-size:2rem; font-weight:900;">{len(viol_df):,}건</div>
            </div>
            <div class="sub-item"><div style="color:#666; font-size:0.8rem;">사유 1</div><div style="color:#111; font-weight:800;">{df_final.iloc[:, -4].sum()}건</div></div>
            <div class="sub-item"><div style="color:#666; font-size:0.8rem;">사유 2</div><div style="color:#111; font-weight:800;">{df_final.iloc[:, -3].sum()}건</div></div>
        </div>""", unsafe_allow_html=True)
    c3.metric("💰 의심 금액", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.divider()
    tab1, tab2 = st.tabs(["📋 위반 리스트", "📊 통계 분석"])
    with tab1: st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)
    with tab2:
        stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
        fig = px.bar(stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    
    st.download_button("📥 분석 결과 다운로드", df_final.to_csv(index=False).encode('utf-8-sig'), "Audit_Result.csv", use_container_width=True)
else:
    st.info("💡 검증하려는 파일을 업로드하면 분석이 시작됩니다.")
