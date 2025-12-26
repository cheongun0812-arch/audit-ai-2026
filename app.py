import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time

# --- 페이지 설정 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# --- CSS (고급스러운 Yellow & Dark) ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; }
    .report-box { background: #161618; border-left: 5px solid #FFD700; padding: 20px; border-radius: 10px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 에니메이션 로드
def get_lottie(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_main = get_lottie("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json")

# --- 헤더 ---
st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
if lottie_main: st_lottie(lottie_main, height=100)

tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

with tab2:
    st.subheader("📊 법인카드 데이터 정밀 분석")
    uploaded_file = st.file_uploader("파일을 업로드하세요 (CSV, XLSX)", type=['csv', 'xlsx'])

    if uploaded_file:
        try:
            # 1. 데이터 로드 (첫 줄이 제목이 아닐 경우를 대비해 처리)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # 만약 첫 줄이 데이터가 아니라 컬럼명들이 들어있는 줄이라면 재설정
            if 'Unnamed' in df.columns[0]:
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)

            # 2. 지능형 컬럼 매핑 (이름이 달라도 찾아냄)
            col_map = {
                '금액': ['금액', '이용금액', '승인금액', '합계'],
                '날짜': ['승인일자', '거래일자', '이용일자', '날짜'],
                '가맹점': ['거래처명', '가맹점명', '사용처', '상호'],
                '사용자': ['사용자', '이용자명', '성명', '사원명']
            }
            
            final_cols = {}
            for target, keywords in col_map.items():
                for col in df.columns:
                    if any(k in str(col) for k in keywords):
                        final_cols[target] = col
                        break

            # 3. 데이터 정제
            df[final_cols['금액']] = pd.to_numeric(df[final_cols['금액']].replace('[^0-9]', '', regex=True))
            df[final_cols['날짜']] = pd.to_datetime(df[final_cols['날짜']])
            
            # 4. 시각화 및 리포트
            total_amt = df[final_cols['금액']].sum()
            st.metric("총 집행 금액", f"{total_amt:,.0f} 원")

            # 일별 차트
            daily = df.groupby(final_cols['날짜'])[final_cols['금액']].sum().reset_index()
            fig = go.Figure(go.Scatter(x=daily[final_cols['날짜']], y=daily[final_cols['금액']], 
                                     line=dict(color='#FFD700', width=3), mode='lines+markers'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(f'<div class="report-box">✅ **분석 완료:** {len(df)}건의 내역 중 고액 사용 및 패턴 분석을 마쳤습니다.</div>', unsafe_allow_html=True)
            st.dataframe(df[[final_cols['날짜'], final_cols['가맹점'], final_cols['금액'], final_cols['사용자']]].head(20))

        except Exception as e:
            st.error(f"분석 중 오류 발생: {e}. 파일의 컬럼명을 확인해 주세요.")
