import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 보색 대비 및 시인성 극대화 디자인 (High-Contrast Dark Mode)
# =========================================================
st.set_page_config(page_title="2026 Audit System", layout="wide")

st.markdown("""
<style>
    /* [메인 화면] 배경: 짙은 네이비 / 텍스트: 밝은 흰색 */
    .stApp { background-color: #0E1117; }
    
    /* 사이드바 가독성 (밝은 배경 + 아주 어두운 텍스트) */
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2 {
        color: #111111 !important;
        font-weight: 800 !important;
    }
    
    /* [메인 화면 텍스트] 모든 헤더, 라벨, 텍스트를 흰색으로 강제 */
    h1, h2, h3, .stMarkdown p, .stTabs [data-baseweb="tab"], label {
        color: #FFFFFF !important;
    }
    .main-white-text {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1.1rem;
    }

    /* 파일 업로드 관련 모든 텍스트 흰색 처리 */
    [data-testid="stFileUploaderLabel"] p { color: #FFFFFF !important; font-weight: 700 !important; }
    [data-testid="stFileUploaderFileName"] { color: #FFFFFF !important; }
    [data-testid="stFileUploaderFileData"] > div { color: #FFFFFF !important; }
    div[data-testid="stFileUploader"] small { color: #FFFFFF !important; }

    /* 영웅 섹션 (헤더) */
    .hero {
        background: #1A1E26;
        border-left: 5px solid #FFD700;
        padding: 20px;
        margin-bottom: 25px;
    }
    
    /* 지표(Metric) 박스: 배경 흰색 + 글씨 어두운색 */
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
# 2) 실무 맞춤형 분석 엔진 (차량운전비 완전 제거 로직)
# =========================================================
class AuditEngineV5_6:
    @staticmethod
    def run_analysis(df, keywords):
        # 업로드 데이터 컬럼 기준 매핑
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # 1. 심야 사용 (23시 ~ 06시)
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        
        # 2. 휴무일/공휴일 사용
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 3. 금지업종 및 화이트리스트 (최우선 순위 적용)
        def check_compliance(row):
            user_val = str(row[u_col])
            merchant_val = str(row[m_col])
            
            # 🚨 [최우선 처리] 차량운전비 완전 제외
            # 사용자명에 "차량운전비"가 들어있으면 어떠한 조건도 검사하지 않고 통과
            if "차량운전비" in user_val:
                return False
            
            # [유지] 업무용 서비스 예외
            if "카카오업무택시" in merchant_val or "카카오T비즈" in merchant_val:
                return False
            
            # [유지] 금지업종 키워드 검사 (지점명 오탐지 방지 포함)
            for kw in keywords:
                if kw in merchant_val:
                    if kw == "주점" and re.search(r"[가-힣]주점$", merchant_val):
                        continue
                    return True
            return False

        df['F_RESTRICT'] = df.apply(check_compliance, axis=1)

        # 종합 판정 (심야, 휴일, 금지업종 중 하나라도 해당 시 추출)
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT']].any(axis=1)
        
        # 🚨 [최종 필터링] 다시 한번 사용자 컬럼에서 차량운전비를 검색하여 불필요한 행 제거
        # IS_VIOLATION이 True더라도 사용자가 차량운전비면 무조건 False로 바꿈
        df.loc[df[u_col].astype(str).str.contains("차량운전비", na=False), 'IS_VIOLATION'] = False
        
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
    <p style="color:#FFD700; margin:5px 0 0 0;">실무 최적화 준법 감시 시스템 v5.6 (차량운전비 예외 고도화)</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ 검증 설정")
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    st.divider()
    st.markdown("## 🚫 집중 모니터링 업종")
    kw_input = st.text_area("쉼표 구분", "주점, 노래방, 유흥, 마사지, 골프장, 사우나, 귀금속, 백화점, 면세점", height=150)
    keywords = [k.strip() for k in kw_input.split(",")]

if admin_pw != "ktmos0402!":
    st.warning("인증이 필요합니다.")
    st.stop()

uploaded_file = st.file_uploader("법인카드 내역 파일 업로드", type=['xlsx', 'csv'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    engine = AuditEngineV5_6()
    df_final = engine.run_analysis(df_raw, keywords)
    
    # IS_VIOLATION이 True인 데이터만 추출하여 대시보드 구성
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
    st.download_button("📥 전체 분석 결과 다운로드 (CSV)", csv_out, "Audit_Result_Final.csv", use_container_width=True)
