import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 가독성 극대화 및 보색 대비 설정 (UI/UX)
# =========================================================
st.set_page_config(page_title="2026 Audit System", layout="wide")

st.markdown("""
<style>
    /* 전체 배경: 짙은 네이비 */
    .stApp { background-color: #0E1117; }
    
    /* 사이드바 가독성 강화: 밝은 배경에는 아주 어두운 텍스트 */
    [data-testid="stSidebar"] {
        background-color: #F0F2F6 !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: #111111 !important;
        font-weight: 600 !important;
    }
    
    /* 메인 화면 텍스트: 어두운 배경에는 밝은 흰색 */
    h1, h2, h3, .stMarkdown p, .stTabs [data-baseweb="tab"] {
        color: #FFFFFF !important;
    }
    
    /* 영웅 섹션 (헤더) */
    .hero {
        background: #1A1E26;
        border-left: 5px solid #FFD700;
        padding: 20px;
        margin-bottom: 25px;
    }
    
    /* 지표(Metric) 박스 */
    [data-testid="stMetric"] {
        background: #FFFFFF; /* 밝은 배경 */
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] { color: #333333 !important; }
    [data-testid="stMetricValue"] { color: #D62728 !important; } /* 포인트 컬러 */

    /* 데이터프레임 가독성 */
    .stDataFrame {
        background-color: #FFFFFF;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 실무 맞춤형 분석 엔진 (김영란법 제외, 30분 규칙 적용)
# =========================================================
class AuditEngineV2:
    @staticmethod
    def run_analysis(df, keywords):
        # 컬럼 자동 매핑 (사용자 업로드 파일 기준)
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # 1. 심야 사용 (23시 ~ 06시)
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        
        # 2. 휴무일/공휴일 사용
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # 3. 금지업종 (재원기준 반영)
        pattern = "|".join([re.escape(k.strip()) for k in keywords if k.strip()])
        df['F_RESTRICT'] = df[m_col].astype(str).str.contains(pattern, case=False, na=False)
        
        # 4. 동일가맹점 30분 이내 결제 (요청하신 기준)
        df = df.sort_values(by=[u_col, m_col, 'P_DT'])
        df['time_diff'] = df.groupby([u_col, m_col])['P_DT'].diff().dt.total_seconds() / 60
        df['F_SPLIT'] = (df['time_diff'] > 0) & (df['time_diff'] <= 30)

        # 종합 판정 (김영란법 관련 가액 기준은 로직에서 완전 제외)
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT', 'F_SPLIT']].any(axis=1)
        
        reasons = []
        for _, row in df.iterrows():
            r = []
            if row['F_NIGHT']: r.append("🌙심야")
            if row['F_WEEKEND']: r.append("📅휴일")
            if row['F_RESTRICT']: r.append("🚫금지업종")
            if row['F_SPLIT']: r.append("🕒30분내연속")
            reasons.append(" / ".join(r))
        df['검토사유'] = reasons
        return df

# =========================================================
# 3) 메인 화면 구성
# =========================================================
st.markdown("""
<div class="hero">
    <h1 style="margin:0;">🛡️ Corporate Card Audit AI</h1>
    <p style="color:#FFD700; margin:5px 0 0 0;">실무자 맞춤형 법인카드 모니터링 시스템 (재원기준 최적화)</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ 검증 설정")
    admin_pw = st.text_input("관리자 비밀번호", type="password", value="ktmos0402!")
    
    st.divider()
    st.markdown("### 🚫 집중 모니터링 업종")
    kw_input = st.text_area("쉼표로 구분", "노래방, 주점, 유흥, 마사지, 골프장, 사우나, 귀금속", height=150)
    keywords = [k.strip() for k in kw_input.split(",")]

if admin_pw != "ktmos0402!":
    st.warning("비밀번호가 올바르지 않습니다.")
    st.stop()

uploaded_file = st.file_uploader("법인카드 내역 파일을 업로드하세요 (Excel/CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    engine = AuditEngineV2()
    df_final = engine.run_analysis(df_raw, keywords)
    viol_df = df_final[df_final['IS_VIOLATION']]
    
    # 상단 요약 지표
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 검토", f"{len(df_final):,}건")
    c2.metric("검토 필요", f"{len(viol_df):,}건")
    c3.metric("연속 결제(30분)", f"{df_final['F_SPLIT'].sum():,}건")
    c4.metric("검토 대상 금액", f"{viol_df['P_AMT'].sum():,.0f}원")

    st.markdown("---")
    
    # 결과 표시
    tab1, tab2 = st.tabs(["📋 검토 필요 리스트", "📊 사용자별 통계"])
    
    with tab1:
        st.markdown("#### 🔎 조건에 부합하는 추출 데이터")
        st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### 👤 사용자별 추출 건수 (그래프 클릭 시 하단 상세 표시)")
        user_stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
        fig = px.bar(user_stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
        sel = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
        
        if sel and sel.get("selection") and sel["selection"]["points"]:
            user = sel["selection"]["points"][0]["x"]
            st.markdown(f"#### 📄 {user} 님의 상세 내역")
            st.dataframe(viol_df[viol_df['사용자'] == user], use_container_width=True)

    # 데이터 다운로드
    csv_out = df_final.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 분석 결과 다운로드 (CSV)", csv_out, "Audit_Result.csv", use_container_width=True)
