import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time

# --- 디자인 설정 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# CSS: 실장님이 요청하신 Yellow 포인트 & 고급스러운 다크 테마
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@100;400;900&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    
    /* 헤더 스타일 */
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; margin-bottom: 0px; }
    .sub-title { color: #888; font-size: 18px; margin-bottom: 30px; }
    
    /* 탭 메뉴 강조 (Yellow) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1A1A1B; border-radius: 5px 5px 0 0;
        padding: 10px 20px; color: #FFD700 !important; font-weight: bold;
    }
    
    /* 파일 업로더 검정색 배경 */
    [data-testid="stFileUploader"] section {
        background-color: #000000 !important; border: 1px dashed #FFD700 !important;
    }
    
    /* 입력창 Yellow */
    .stTextInput input { background-color: #1A1A1B !important; color: #FFD700 !important; border: 1px solid #FFD700 !important; }
    
    /* 리포트 카드 */
    .report-box { background: #161618; border-left: 5px solid #FFD700; padding: 20px; border-radius: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 에니메이션 안전 로드 함수
def get_lottie(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_main = get_lottie("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json")

# --- 메인 화면 레이아웃 ---
col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">"당신의 열정을 보호하고, 회사의 미래를 설계합니다."</p>', unsafe_allow_html=True)
    st.warning("실장님 메시지: 우리는 감시자가 아닙니다. 당신의 성공을 돕는 AI 가디언입니다.")

with col_t2:
    if lottie_main: st_lottie(lottie_main, height=150)

# --- 메뉴 구성 ---
tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# 1. AI 계약서 검토
with tab1:
    st.subheader("📄 AI 계약서 독소 조항 탐지기")
    st.write("AI가 계약 문구 속 숨겨진 불공정 독소 조항을 실시간으로 분석합니다.")
    st.file_uploader("검토할 계약서를 업로드하세요 (PDF, TXT)", type=['pdf', 'txt'])
    
    st.markdown("""
    <div class="report-box">
        <h4 style="color:#FFD700;">🚩 AI 실시간 분석 예시</h4>
        <p style="color:#FF5555;"><b>[위험] 제17조 2항:</b> "을은 어떠한 경우에도 이의를 제기할 수 없다."</p>
        <p>→ <b>해결책:</b> 해당 조항은 공정거래법상 무효 가능성이 높습니다. 수정 권고안을 확인하세요.</p>
    </div>
    """, unsafe_allow_html=True)

# 2. 법카 리스크 분석 (화려한 주식 차트 스타일)
with tab2:
    st.subheader("📊 AI 법인카드 리스크 대시보드")
    st.write("RAW 데이터를 업로드하면 AI가 이상 패턴을 감지하여 시각화합니다.")
    
    # 화려한 인터랙티브 차트 (Plotly)
    df_sample = pd.DataFrame({
        'Date': pd.date_range(start='2025-12-01', periods=20),
        'Amount': [10, 12, 11, 15, 25, 20, 18, 45, 30, 25, 22, 19, 21, 55, 40, 35, 30, 28, 26, 24]
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_sample['Date'], y=df_sample['Amount'],
                             mode='lines+markers', name='사용금액',
                             line=dict(color='#FFD700', width=3),
                             marker=dict(size=8, color='#FF5555')))
    
    fig.update_layout(title="일별 법인카드 사용 추이 (AI 탐지 포함)",
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(color="white"), xaxis_showgrid=False, yaxis_showgrid=True,
                      yaxis_gridcolor='#333')
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.error("💡 AI 감지: 12월 14일, 특정 부서의 심야 시간대 결제액이 평소보다 300% 급증했습니다.")
    st.file_uploader("법인카드 RAW 파일(Excel) 업로드", type=['xlsx'])

# 3. AI 실장님 상담소
with tab3:
    st.subheader("💬 AI 실장님 상담소")
    st.write("비공개 상담입니다. 무엇이든 물어보세요.")
    
    user_q = st.text_input("고민되는 상황을 입력하세요 (예: 협력사 식사 대접 시 대응 방법)", placeholder="여기에 입력하세요...")
    
    if user_q:
        with st.spinner("AI 실장님이 최적의 솔루션을 구상 중입니다..."):
            time.sleep(1)
            st.markdown(f"""
            <div class="report-box">
                <p style="color:#FFD700;"><b>질문: {user_q}</b></p>
                <p><b>AI 가이드:</b> "우리 회사 윤리 강령 제5조에 따르면, 사회 통념상 허용되는 범위를 넘어서는 접대는 거절하는 것이 원칙입니다. 
                상대방의 기분을 상하게 하지 않는 <b>'거절 메일 템플릿'</b>을 생성해 드릴까요?"</p>
            </div>
            """, unsafe_allow_html=True)
