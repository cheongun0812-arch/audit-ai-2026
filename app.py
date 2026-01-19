import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 보색 대비 완결 디자인 (High-Contrast Dark Mode)
# =========================================================
st.set_page_config(page_title="2026 Audit System", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2 {
        color: #111111 !important;
        font-weight: 800 !important;
    }
    .main-white-text {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.1rem;
        margin-bottom: 10px;
    }
    h1, h2, h3, .stMarkdown p, .stTabs [data-baseweb="tab"] {
        color: #FFFFFF !important;
    }
    .hero {
        background: #1A1E26;
        border-left: 5px solid #FFD700;
        padding: 20px;
        margin-bottom: 25px;
    }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 15px;
    }
    [data-testid="stMetricLabel"] { color: #111111 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #D62728 !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 실무 맞춤형 분석 엔진 (오탐지 방지 로직 강화)
# =========================================================
class AuditEngineV5_2:
    @staticmethod
    def run_analysis(df, keywords):
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # 1. 심야 사용 (23시 ~ 06시)
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        
        # 2. 휴무일/공휴일 사용
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 3. 금지업종 (오탐지 방지 필터 적용)
        def check_restricted(merchant):
            merchant = str(merchant)
            # ✅ "~~주점"은 잡되, "~~원주점", "~~나주점" 처럼 지역명+점 형태는 제외
            # 정규표현식: 상호명에 '주점'이라는 단어가 독립적으로 존재하거나 특정 유흥 키워드가 있을 때만 매칭
            for kw in keywords:
                if kw in merchant:
                    # '주점' 키워드일 경우 '원주점', '청주점', '충주점' 등 지점명 패턴인지 재검증
                    if kw == "주점":
                        if re.search(r"[가-힣]{1}주점$", merchant): # '원주점' 등 지점명 패턴
                            continue
                    return True
            return False

        df['F_RESTRICT'] = df[m_col].apply(check_restricted)

        # 종합 판정 (30분 연속결제 제외)
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

# =========================================================
# 3) 메인 화면 구성
# =========================================================
st.markdown("""
<div class="hero">
    <h1 style="margin:0;">🛡️ Corporate Card Audit AI</h1>
    <p style="color:#FFD700; margin:5px 0 0 0;">실무 최적화 준법 감시 시스템 v5.2 (오탐지 정교화 반영)</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ 검증 설정")
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    st.divider()
    st.markdown("## 🚫 집중 모니터링 업종")
    # ✅ '주점' 키워드를 포함하되 로직에서 '~~주점' 지역명은 거르도록 설정
    kw_input = st.text_area("쉼표 구분", "주점, 노래방, 유흥, 마사지, 골프장, 사우나, 귀금속, 백화점, 면세점", height=150)
    keywords = [k.strip() for k in kw_input.split(",")]

if admin_pw != "ktmos0402!":
    st.warning("인증이 필요합니다.")
    st.stop()

uploaded_file = st.file_uploader("법인카드 내역 파일 업로드", type=['xlsx', 'csv'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    engine = AuditEngineV5_2()
    df_final = engine.run_analysis(df_raw, keywords)
    viol_df = df_final[df_final['IS_VIOLATION']]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("🔍 총 검토 내역", f"{len(df_final):,}건")
    c2.metric("🚨 검토 필요 건", f"{len(viol_df):,}건")
    c3.metric("💰 검토 금액 합계", f"{viol_df['P_AMT'].sum():,.0f}원")

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
    st.download_button("📥 전체 분석 결과 다운로드 (CSV)", csv_out, "Audit_Result_v5.2.csv", use_container_width=True)
