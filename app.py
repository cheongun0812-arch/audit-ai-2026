import streamlit as st
import pandas as pd
import re
import plotly.express as px
from datetime import datetime

# 1. 디자인 및 레이아웃 (v5.8 고대비 유지)
st.set_page_config(page_title="2026 Integrated Audit", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] * { color: #111111 !important; font-weight: 800 !important; }
    h1, h2, h3, p, label { color: #FFFFFF !important; }
    .hero { background: #1A1E26; border-left: 5px solid #FFD700; padding: 20px; margin-bottom: 25px; }
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
    .sub-label { color: #666; font-size: 0.8rem; font-weight: 700; }
    .sub-value { color: #111; font-weight: 800; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# 2. 차량비 전용 분석 엔진 (1년치 데이터 특화)
class FuelAuditEngine:
    @staticmethod
    def clean_fuel_data(uploaded_files):
        all_dfs = []
        for file in uploaded_files:
            try:
                # 1. 원본 데이터 읽기 및 헤더 찾기 (유연한 읽기)
                raw = pd.read_csv(file, header=None) if file.name.endswith('.csv') else pd.read_excel(file, header=None)
                header_idx = -1
                for i, row in raw.iterrows():
                    row_str = " ".join(row.astype(str))
                    if '본부' in row_str and '관리자' in row_str:
                        header_idx = i; break
                
                if header_idx == -1: continue
                
                df = pd.read_csv(file, skiprows=header_idx) if file.name.endswith('.csv') else pd.read_excel(file, skiprows=header_idx)
                df.columns = [c.strip() for c in df.columns]
                
                # 2. 유종 및 시트 정보 자동 감지
                engine_type = '전기' if '전기' in file.name else '내연기관'
                
                # 3. 컬럼명 표준화
                rename_map = {'(신)카드번호': '카드번호', '카드번호(BC)': '카드번호', '주유 외': '금액', '주유금액': '금액'}
                df = df.rename(columns=rename_map)
                
                # 4. 필수 데이터 정제
                valid_cols = [c for c in ['본부', '부서', '관리자', '차종', '차량번호', '금액', '하이패스비'] if c in df.columns]
                df = df[valid_cols].copy()
                df = df[df['관리자'].notna() & ~df['관리자'].astype(str).str.contains('소계|본부|관리자|합계', na=False)]
                
                # 5. 금액 변환
                df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df['엔진유형'] = engine_type
                df['월정보'] = re.search(r'\d+년\d+월', file.name).group() if re.search(r'\d+년\d+월', file.name) else "기타"
                
                all_dfs.append(df)
            except: continue
        
        return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# 3. 메인 화면 구성
with st.sidebar:
    st.markdown("## ⚙️ Audit Menu")
    menu = st.radio("검증 대상 선택", ["💳 법인카드 모니터링", "⛽ 차량주유 모니터링"])
    st.divider()
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")

if admin_pw == "ktmos0402!":
    if menu == "💳 법인카드 모니터링":
        st.markdown('<div class="hero"><h1>🛡️ Card Audit AI</h1><p style="color:#FFD700;">SIMPLE IS BEST : 법인카드 검증 모드</p></div>', unsafe_allow_html=True)
        # (기존 v5.8 법인카드 로직 유지...)
        
    else: # ⛽ 차량주유 모니터링 (1년치 데이터 특화)
        st.markdown('<div class="hero"><h1>⛽ Vehicle Expense AI</h1><p style="color:#FFD700;">1년치 차량비 통합 분석 및 이상 탐지 모드</p></div>', unsafe_allow_html=True)
        files = st.file_uploader("월별 차량비 파일들을 모두 선택하세요 (CSV/Excel)", type=['xlsx', 'csv'], accept_multiple_files=True)
        
        if files:
            df_combined = FuelAuditEngine.clean_fuel_data(files)
            
            if not df_combined.empty:
                # 상단 통합 지표
                ice_total = df_combined[df_combined['엔진유형']=='내연기관']['금액'].sum()
                ev_total = df_combined[df_combined['엔진유형']=='전기']['금액'].sum()
                
                c1, c2, c3 = st.columns([1.2, 3.5, 1.5])
                c1.metric("🔍 총 데이터", f"{len(df_combined):,}건")
                with c2:
                    st.markdown(f"""
                        <div class="integrated-metric-card">
                            <div class="metric-main">
                                <div class="metric-label">💰 1년 총 사용액</div>
                                <div class="metric-value">{(ice_total+ev_total):,.0f}원</div>
                            </div>
                            <div class="metric-sub-container">
                                <div class="sub-item"><div class="sub-label">⛽ 내연기관</div><div class="sub-value">{ice_total:,.0f}원</div></div>
                                <div class="sub-item"><div class="sub-label">🔋 전기차</div><div class="sub-value">{ev_total:,.0f}원</div></div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                c3.metric("💳 총 하이패스", f"{df_combined['하이패스비'].sum():,.0f}원")
                
                st.divider()
                tab1, tab2, tab3 = st.tabs(["📊 월별 추이", "📋 과다지출 의심건", "👤 사용자별 통계"])
                
                with tab1:
                    trend = df_combined.groupby(['월정보', '엔진유형'])['금액'].sum().reset_index()
                    fig = px.line(trend, x='월정보', y='금액', color='엔진유형', markers=True, template="plotly_dark", title="연간 차량비 지출 추이")
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    limit = st.slider("이상치 탐지 기준 (월 사용액)", 100000, 1000000, 500000)
                    suspicious = df_combined[df_combined['금액'] > limit].sort_values('금액', ascending=False)
                    st.markdown(f"#### 🚨 월 {limit:,.0f}원 초과 지출 내역")
                    st.dataframe(suspicious, use_container_width=True, hide_index=True)
                
                with tab3:
                    user_list = df_combined['관리자'].unique()
                    target_user = st.selectbox("관리자 선택", sorted(user_list))
                    user_data = df_combined[df_combined['관리자'] == target_user].sort_values('월정보')
                    st.markdown(f"### 📄 {target_user} 님의 연간 리포트 ({user_data['차종'].iloc[0]})")
                    fig_user = px.bar(user_data, x='월정보', y='금액', text_auto=',.0f', template="plotly_dark")
                    st.plotly_chart(fig_user, use_container_width=True)
