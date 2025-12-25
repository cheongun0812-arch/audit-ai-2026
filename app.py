import streamlit as st
import pandas as pd
import time
from streamlit_lottie import st_lottie
import requests
import base64 # 파일 다운로드 링크 생성을 위함

# --- 페이지 설정 ---
st.set_page_config(page_title="2026 감사실 AI 혁신 포털", page_icon="🛡️", layout="wide")

# --- Lottie 애니메이션 로드 함수 ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

lottie_ai_robot = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json") # AI 로봇
lottie_financial_chart = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_nysj264u.json") # 금융 차트

# --- 커스텀 CSS (색상 및 스타일 조정) ---
st.markdown("""
    <style>
    .stApp { 
        background: linear-gradient(to right, #0f0c29, #302b63, #24243e); 
        color: white; 
    }
    .report-card { 
        background-color: rgba(255, 255, 255, 0.1); 
        padding: 25px; 
        border-radius: 20px; 
        border: 1px solid #FFD700; /* 노란색 테두리 */
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); 
    }
    h1 { 
        font-size: 3rem; 
        font-weight: 800; 
        background: -webkit-linear-gradient(#FFD700, #FFEA00); /* 노란색 그라데이션 */
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        color: #FFD700; /* 탭 글씨 노란색 */
    }
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #333333; /* 탭 배경 어둡게 */
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom: 2px solid #FFD700; /* 선택된 탭 하단 노란색 */
    }
    .stTextInput>div>div>input {
        background-color: #222222; /* 입력창 배경 어둡게 */
        color: #FFD700; /* 입력 텍스트 노란색 */
        border: 1px solid #FFD700; /* 테두리 노란색 */
    }
    .stFileUploader>div>div>button {
        background-color: #000000 !important; /* 파일 업로더 버튼 배경 검정색 */
        color: #ffffff !important; /* 파일 업로더 버튼 글씨 흰색 */
        border: 1px solid #FFD700 !important; /* 파일 업로더 버튼 테두리 노란색 */
    }
    .stFileUploader>div>div>label {
        color: #FFD700 !important; /* 파일 업로더 레이블 글씨 노란색 */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 메인 헤더 ---
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🛡️ 2026 AUDIT AI")
    st.write("### '당신의 열정을 보호하고, 회사의 미래를 설계합니다.'")
    st.info("실장님 메시지: “우리는 감시자가 아닙니다. 당신의 성공을 돕는 AI 가디언입니다.”")
with col2:
    st_lottie(lottie_ai_robot, height=200, key="ai_robot_anim")

st.divider()

# --- 탭 구성 ---
tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# --- Tab 1: AI 계약서 독소 조항 탐지 ---
with tab1:
    st.header("📄 AI 계약서 독소 조항 탐지기")
    st.write("계약서 파일을 업로드하세요. AI가 우리 회사를 '노비'로 만드는 조항을 찾아냅니다.")
    
    uploaded_file = st.file_uploader("검토할 계약서를 업로드하세요", type=['pdf', 'txt'], key="contract_uploader")
    
    if uploaded_file:
        with st.status("AI가 법률 조항을 초고속 스캔 중입니다...", expanded=True) as status:
            time.sleep(1.5); st.write("조항별 리스크 매핑 중...")
            time.sleep(1.2); st.write("유사 판례 데이터베이스 대조 중...")
            status.update(label="분석 완료! 위험 요소를 발견했습니다.", state="complete")
        
        st.markdown("""
        <div class="report-card">
            <h3 style="color: #ff4b4b;">⚠️ 주의 필요 조항 발견 (노란색으로 강조)</h3>
            <p style="color: #FFD700;"><b>제 15조 (손해배상):</b> "을의 과실이 없는 경우에도 갑의 손해를 전액 보상한다."</p>
            <hr style="border-color: #FFD700;">
            <p><b>🤖 AI 분석:</b> 이 조항은 공정거래법 위반 소지가 다분합니다. <b>'독소 조항'</b>으로 분류되었습니다. 
            감사실이 이미 수정안을 준비해 두었으니, 법무팀 전달 전 상담을 요청하세요!</p>
        </div>
        """, unsafe_allow_html=True)

# --- Tab 2: 법카 리스크 분석 (주식 차트 스타일) ---
with tab2:
    st.header("📊 AI 법인카드 투명성 대시보드")
    st.write("2026년 1월 현재, 전사 준법 지수는 **'매우 맑음(98%)'** 입니다.")

    # Lottie 애니메이션 - 금융 차트
    st_lottie(lottie_financial_chart, height=200, key="financial_chart_anim")

    st.subheader("💡 법인카드 사용 내역 파일을 업로드하여 AI 분석을 시작하세요.")
    uploaded_excel_file = st.file_uploader("법인카드 사용 내역 (Excel 파일)", type=['xlsx', 'xls'], key="card_uploader")

    # 가상의 주식 차트 데이터 (실제 데이터와 연동될 경우 대체)
    if uploaded_excel_file:
        df_card = pd.read_excel(uploaded_excel_file) # 실제 엑셀 파일 읽기
        
        # 실제 데이터에서 '날짜', '금액' 컬럼이 있다고 가정하고 주식 차트 데이터 생성
        # 여기서는 예시를 위해 가상 데이터를 만듭니다.
        df_chart = pd.DataFrame({
            'Date': pd.to_datetime(['2025-12-01', '2025-12-05', '2025-12-10', '2025-12-15', '2025-12-20', '2025-12-25', '2025-12-30']),
            'Open': [100, 105, 110, 108, 115, 112, 120],
            'High': [108, 112, 115, 112, 120, 118, 125],
            'Low': [98, 103, 108, 105, 110, 108, 115],
            'Close': [105, 110, 108, 115, 112, 120, 118]
        }).set_index('Date')

        st.line_chart(df_chart[['Open', 'High', 'Low', 'Close']]) # 주식 차트처럼 라인 그래프 사용
        st.success("✨ AI가 법인카드 사용 패턴을 분석했습니다. 이상 징후 없음! (가상)")

        # 문제되는 부분 추출 (가상 로직)
        st.subheader("⚠️ AI 분석 보고서: 이상 징후 감지 (샘플)")
        st.markdown(
            """
            - **[주의]** 특정 부서의 주말/야간 유흥비 지출이 전월 대비 15% 증가했습니다. (익명 처리)
            - **[권고]** 개인 용도 사용으로 오해될 수 있는 소액 반복 결제가 일부 확인됩니다.
            """
        )
        # 보고서 다운로드 기능 (PDF 또는 TEXT 파일로)
        st.markdown(
            get_binary_file_downloader_html('AI_Card_Analysis_Report_202601.txt', '상세 분석 보고서 다운로드'), 
            unsafe_allow_html=True
        )

    else:
        st.info("⬆️ Excel 파일을 업로드하시면 AI가 사용 패턴을 분석하고 리스크를 시각화합니다.")

# --- Tab 3: AI 실장님 상담소 ---
with tab3:
    st.header("💬 AI 실장님 준법 상담소")
    user_input = st.text_input("고민되는 상황을 입력해 보세요. (예: 협력사에서 선물을 주겠다고 합니다.)", 
                                key="ai_chat_input") # 입력창 key 추가
    
    if user_input:
        with st.spinner("AI 실장님이 답변을 고민 중입니다..."):
            time.sleep(1.5) # AI가 생각하는 시간
        st.chat_message("assistant").write(f"'{user_input}'에 대한 실장님의 AI 가이드:")
        st.markdown("""
        <div class="report-card" style="border-left: 5px solid #FFD700;">
            <p>“그 마음은 감사하지만, 우리 회사의 윤리 강령 제 3조에 위배될 수 있습니다. 
            정중히 거절하는 법을 AI가 메일 초안으로 써드릴까요? 
            <b>당신의 커리어는 감사실이 지켜드립니다.</b>”</p>
        </div>
        """, unsafe_allow_html=True)

# --- 파일 다운로드 함수 ---
def get_binary_file_downloader_html(bin_file, link_text, file_type='text/plain'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:{file_type};base64,{bin_str}" download="{bin_file}" style="color: #FFD700; text-decoration: none;">{link_text}</a>'
    return href
