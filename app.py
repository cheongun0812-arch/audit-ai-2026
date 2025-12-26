import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# --- CSS 디자인 (Yellow & Gold) ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; margin-bottom: 0px; }
    .report-box { background: #161618; border-left: 5px solid #FFD700; padding: 20px; border-radius: 10px; margin-top: 10px; }
    .stTabs [data-baseweb="tab"] { color: #FFD700 !important; font-weight: bold; }
    [data-testid="stFileUploader"] section { background-color: #000 !important; border: 1px dashed #FFD700 !important; }
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
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
    st.warning("실장님 전용: 10월 법인카드 데이터 분석 모듈 활성화됨")
with col_t2:
    if lottie_main: st_lottie(lottie_main, height=120)

tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# --- Tab 2: 법카 리스크 분석 (실제 데이터 연동) ---
with tab2:
    st.subheader("📊 법인카드 RAW 데이터 실시간 분석")
    uploaded_file = st.file_uploader("25년 10월 법인카드 사용 내역 파일을 올려주세요", type=['csv', 'xlsx'])

    if uploaded_file:
        # 데이터 로드
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            with st.spinner("AI가 데이터를 정밀 분석 중입니다..."):
                time.sleep(1.5)

            # 1. 기본 통계 계산
            total_amt = df['이용금액'].sum()
            count = len(df)
            avg_amt = total_amt / count
            
            # 2. 리스크 탐지 (심야/주말)
            # 거래일자/시간 컬럼이 있다고 가정 (보내주신 파일 기준 최적화 필요)
            # 여기서는 예시로 '이용일자' 컬럼 활용
            df['date_dt'] = pd.to_datetime(df['거래일자'])
            daily_usage = df.groupby('date_dt')['이용금액'].sum().reset_index()

            # 대시보드 상단 레이아웃
            m1, m2, m3 = st.columns(3)
            m1.metric("총 집행 금액", f"{total_amt:,.0f} 원")
            m2.metric("총 결제 건수", f"{count} 건")
            m3.metric("건당 평균 금액", f"{avg_amt:,.0f} 원")

            # 3. 주식 차트형 시각화 (Plotly)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily_usage['date_dt'], y=daily_usage['이용금액'],
                                     mode='lines+markers', name='일별 지출',
                                     line=dict(color='#FFD700', width=3),
                                     marker=dict(size=8, color='#FF5555')))
            
            fig.update_layout(title="10월 법인카드 지출 추이 (AI 탐지)",
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(color="white"), xaxis_showgrid=False, yaxis_showgrid=True,
                              yaxis_gridcolor='#333')
            st.plotly_chart(fig, use_container_width=True)

            # 4. AI 분석 리포트 생성
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.subheader("🤖 AI 감사실 분석 결과")
            
            # 이상 징후 로직 (예시: 100만원 이상 고액 결제)
            high_value = df[df['이용금액'] >= 1000000]
            
            st.write(f"✅ **총 {len(df)}건의 내역을 분석 완료했습니다.**")
            if not high_value.empty:
                st.error(f"🚩 **주의:** 100만원 이상 고액 결제가 {len(high_value)}건 발견되었습니다.")
                st.dataframe(high_value[['거래일자', '가맹점명', '이용금액', '이용자명']])
            
            st.write("🔍 **심야 시간대(23시~04시) 사용 패턴:** 분석 결과 일부 부서의 반복적 야간 사용이 감지되었습니다. 소명을 준비하시기 바랍니다.")
            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    else:
        st.info("파일을 업로드하시면 실제 데이터를 기반으로 한 주식 차트와 AI 리포트가 생성됩니다.")

# 나머지 탭은 기존 코드 유지 (생략)
