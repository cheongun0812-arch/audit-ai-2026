import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) UI/UX 디자인 (v5.8 고대비 다크모드 유지)
# =========================================================
st.set_page_config(page_title="2026 Integrated Audit System", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; }
    [data-testid="stSidebar"] * { color: #111111 !important; font-weight: 800 !important; }
    h1, h2, h3, .stMarkdown p, .stTabs [data-baseweb="tab"], label { color: #FFFFFF !important; }
    .main-white-text { color: #FFFFFF !important; font-weight: 700 !important; }
    [data-testid="stFileUploaderLabel"] p, [data-testid="stFileUploaderFileName"], 
    [data-testid="stFileUploaderFileData"] > div, div[data-testid="stFileUploader"] small { color: #FFFFFF !important; }
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
    .sub-label { color: #666666; font-size: 0.9rem; font-weight: 700; margin-bottom: 3px; }
    .sub-value { color: #111111; font-size: 1.3rem; font-weight: 800; }
    [data-testid="stMetric"] { background: #FFFFFF; border-radius: 10px; padding: 15px; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { color: #111111 !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 통합 분석 엔진 (법인카드 & 연간 차량비)
# =========================================================
class AuditEngineV6_5:
    @staticmethod
    def run_card_audit(df, keywords):
        # 법인카드 분석 로직 (기존 유지)
        u_col, m_col, a_col, t_col = "사용자", "가맹점", "금액.1", "일시"
        df = df.copy()
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        def check_rest(row):
            user, merchant = str(row[u_col]), str(row[m_col])
            if "차량운전비" in user or "카카오" in merchant: return False
            for kw in keywords:
                if kw in merchant:
                    if kw == "주점" and re.search(r"[가-힣]주점$", merchant): continue
                    return True
            return False
        df['F_RESTRICT'] = df.apply(check_rest, axis=1)
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
    def process_fuel_files(files):
        # 1년치 차량비 파일 통합 및 전처리
        all_data = []
        for file in files:
            try:
                # 헤더 자동 감지 (본부/관리자 키워드 기준)
                raw = pd.read_csv(file, header=None) if file.name.endswith('.csv') else pd.read_excel(file, header=None)
                header_idx = next(i for i, row in raw.iterrows() if '본부' in str(row.values) and '관리자' in str(row.values))
                df = pd.read_csv(file, skiprows=header_idx) if file.name.endswith('.csv') else pd.read_excel(file, skiprows=header_idx)
                df.columns = [c.strip() for c in df.columns]
                
                # 유종 및 날짜 추출
                engine_type = '전기' if '전기' in file.name else '내연기관'
                date_match = re.search(r'\d+년\d+월', file.name)
                month_val = date_match.group() if date_match else "기타"
                
                # 컬럼 표준화 및 정제
                df = df.rename(columns={'(신)카드번호': '카드번호', '주유 외': '금액', '주유금액': '금액'})
                df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df['하이패스비'] = pd.to_numeric(df['하이패스비'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                
                cols = ['본부', '부서', '관리자', '차종', '차량번호', '금액', '하이패스비']
                df = df[df['관리자'].notna() & ~df['관리자'].astype(str).str.contains('소계|합계|관리자')][cols]
                df['월정보'] = month_val
                df['엔진유형'] = engine_type
                all_data.append(df)
            except: continue
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# =========================================================
# 3) 메인 화면 구성 및 메뉴 분리
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ Audit Menu")
    menu = st.radio("검증 대상 선택", ["💳 법인카드 모니터링", "⛽ 차량주유 모니터링(연간)"])
    st.divider()
    admin_pw = st.text_input("Password", type="password", value="ktmos0402!")
    if menu == "💳 법인카드 모니터링":
        kw_input = st.text_area("🚫 집중 모니터링 업종", "주점, 노래방, 유흥, 마사지, 골프장, 사우나, 귀금속, 백화점, 면세점", height=150)
        keywords = [k.strip() for k in kw_input.split(",")]

if admin_pw != "ktmos0402!":
    st.warning("Password를 확인해 주세요.")
    st.stop()

# 히어로 섹션
title = "Card Audit AI" if menu == "💳 법인카드 모니터링" else "Fuel Trend AI"
st.markdown(f'<div class="hero"><h1>🛡️ {title}</h1><p style="color:#FFD700;">SIMPLE IS BEST : 통합 준법 감시 v6.5</p></div>', unsafe_allow_html=True)

if menu == "💳 법인카드 모니터링":
    uploaded_file = st.file_uploader("법인카드 내역 파일 업로드", type=['xlsx', 'csv'])
    if uploaded_file:
        df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df_final = AuditEngineV6_5.run_card_audit(df_raw, keywords)
        viol_df = df_final[df_final['IS_VIOLATION']]
        
        # 지표 레이아웃 (v5.8 복구)
        c1, c2, c3 = st.columns([1.2, 3.5, 1.5])
        c1.metric("🔍 총 검토 내역", f"{len(df_final):,}건")
        with c2:
            st.markdown(f"""
                <div class="integrated-metric-card">
                    <div class="metric-main"><div class="metric-label">🚨 검토 필요 건</div><div class="metric-value">{len(viol_df):,}건</div></div>
                    <div class="metric-sub-container">
                        <div class="sub-item"><div class="sub-label">🌙 심야</div><div class="sub-value">{df_final['F_NIGHT'].sum()}건</div></div>
                        <div class="sub-item"><div class="sub-label">📅 휴일</div><div class="sub-value">{df_final['F_WEEKEND'].sum()}건</div></div>
                        <div class="sub-item"><div class="sub-label">🚫 업종</div><div class="sub-value">{df_final['F_RESTRICT'].sum()}건</div></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        c3.metric("💰 검토 금액 합계", f"{viol_df['P_AMT'].sum():,.0f}원")
        
        st.divider()
        tab1, tab2 = st.tabs(["📋 검토 필요 내역", "📊 사용자별 분석"])
        with tab1: st.dataframe(viol_df[['사용자', '가맹점', 'P_AMT', 'P_DT', '검토사유']], use_container_width=True, hide_index=True)
        with tab2:
            stats = viol_df.groupby('사용자').size().reset_index(name='건수').sort_values('건수', ascending=False)
            fig = px.bar(stats.head(20), x='사용자', y='건수', color='건수', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

else: # ⛽ 차량주유 모니터링 (연간 추이 및 Spike 탐지)
    files = st.file_uploader("1년치 차량비 파일들을 모두 선택하세요", type=['xlsx', 'csv'], accept_multiple_files=True)
    if files:
        df_yearly = AuditEngineV6_5.process_fuel_files(files)
        if not df_yearly.empty:
            # 상단 지표
            ice_total = df_yearly[df_yearly['엔진유형']=='내연기관']['금액'].sum()
            ev_total = df_yearly[df_yearly['엔진유형']=='전기']['금액'].sum()
            
            c1, c2, c3 = st.columns([1.2, 3.5, 1.5])
            c1.metric("🔍 연간 데이터", f"{len(df_yearly):,}건")
            with c2:
                st.markdown(f"""
                    <div class="integrated-metric-card">
                        <div class="metric-main"><div class="metric-label">💰 연간 총 지출</div><div class="metric-value">{(ice_total+ev_total):,.0f}원</div></div>
                        <div class="metric-sub-container">
                            <div class="sub-item"><div class="sub-label">⛽ 내연기관</div><div class="sub-value">{ice_total:,.0f}원</div></div>
                            <div class="sub-item"><div class="sub-label">🔋 전기차</div><div class="sub-value">{ev_total:,.0f}원</div></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            c3.metric("💳 총 하이패스", f"{df_yearly['하이패스비'].sum():,.0f}원")
            
            st.divider()
            # 관리자별 연간 추이 그래프 (Spike 탐지)
            st.markdown("### 👤 관리자별 월별 지출 추이 (Spike 탐지)")
            user_list = sorted(df_yearly['관리자'].unique())
            target_user = st.selectbox("관리자를 선택하면 연간 추이가 나타납니다", user_list)
            
            user_df = df_yearly[df_yearly['관리자'] == target_user].sort_values('월정보')
            avg_val = user_df['금액'].mean()
            user_df['상태'] = user_df['금액'].apply(lambda x: '이상(평균 1.5배 초과)' if x > avg_val * 1.5 else '정상')
            
            
            fig = px.bar(user_df, x='월정보', y='금액', color='상태', text_auto=',.0f',
                         color_discrete_map={'정상': '#31333F', '이상(평균 1.5배 초과)': '#D62728'},
                         template="plotly_dark", title=f"{target_user} 님의 월별 지출 현황")
            st.plotly_chart(fig, use_container_width=True)
            
            # 이상 징후 알림
            spikes = user_df[user_df['상태'].str.contains('이상')]
            if not spikes.empty:
                st.warning(f"⚠️ {target_user} 님은 {', '.join(spikes['월정보'].tolist())}에 평소보다 지출이 크게 튀었습니다. 상세 검토를 권장합니다.")
            
            st.download_button("📥 통합 데이터 다운로드 (CSV)", df_yearly.to_csv(index=False).encode('utf-8-sig'), "Yearly_Fuel_Data.csv")
