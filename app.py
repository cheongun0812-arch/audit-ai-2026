import streamlit as st
import pandas as pd
import time

# 1. 페이지 설정 (화려하고 세련된 느낌)
st.set_page_config(page_title="2026 감사실 AI 혁신 포털", page_icon="🛡️", layout="wide")

# 2. 커스텀 CSS (더 '있어 보이게' 만들기)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { background-color: #007bff; color: white; border-radius: 10px; width: 100%; }
    .report-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border-left: 5px solid #007bff; }
    h1 { color: #ffca28; }
    </style>
    """, unsafe_allow_html=True)

# 3. 사이드바 (실장님의 메시지)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.title("실장님의 2026 메시지")
    st.info("“감사실은 이제 여러분의 AI 파트너입니다. 두려워 말고 즐기십시오.”")
    st.divider()
    st.write("📅 **현재 시즌:** 2026 신년 기선제압 프로젝트")

# 4. 메인 화면 - 헤더
st.title("🛡️ 2026 감사실: AI 혁신 & FUNFUN 센터")
st.subheader("경영진도 감히 엄두 못 낼, 우리 감사실만의 전용 AI 솔루션입니다.")

# 5. 탭 구성 (기능별 분리)
tab1, tab2, tab3 = st.tabs(["📄 AI 계약서 독소 탐지", "💳 법카 청정 대시보드", "🎮 FUNFUN 준법 퀴즈"])

# --- Tab 1: AI 계약서 독소 탐지 ---
with tab1:
    st.header("🔍 AI 계약서 검토 비서 (Beta)")
    st.write("계약서 파일을 업로드하세요. AI가 우리 회사를 '노비'로 만드는 조항을 찾아냅니다.")
    
    uploaded_file = st.file_uploader("계약서 업로드 (PDF/DOCX)", type=['pdf', 'docx', 'txt'])
    
    if uploaded_file:
        with st.spinner('AI가 독소 조항을 분석 중입니다...'):
            time.sleep(2) # 분석하는 척 하는 효과
            st.success("분석 완료!")
            
            # 유머러스한 가상 결과물
            st.markdown("""
            <div class="report-card">
                <h4>🚩 독소 조항 발견!</h4>
                <p><b>제 12조 3항:</b> "을(우리 회사)은 갑의 호출 시 24시간 내에 응답해야 한다."</p>
                <p style="color: #ff4b4b;"><b>[AI 의견]:</b> 이건 협력 계약이 아니라 노예 계약 아닙니까? 실장님께 보고하기 전에 당장 수정하세요!</p>
            </div>
            """, unsafe_allow_html=True)

# --- Tab 2: 법카 분석 (시각화 샘플) ---
with tab2:
    st.header("📊 나의 법인카드 안전 지수")
    # 샘플 데이터 생성
    chart_data = pd.DataFrame({
        '항목': ['식비', '교통비', '소모품', '접대비'],
        '사용금액': [120, 50, 80, 200]
    })
    st.bar_chart(data=chart_data, x='항목', y='사용금액')
    st.info("💡 Tip: 현재 실장님의 AI가 당신의 접대비 패턴을 학습 중입니다. 매우 깨끗하시네요!")

# --- Tab 3: 퀴즈 ---
with tab3:
    st.header("🎁 2026 신년 준법 퀴즈 이벤트")
    q = st.radio("Q. 다음 중 감사실 실장님이 가장 좋아하실 것 같은 행동은?", 
                 ["몰래 법카 긁기", "AI 감사실 포털에 매일 출석하기", "감사실 앞에서 도망가기"])
    if st.button("정답 확인"):
        if q == "AI 감사실 포털에 매일 출석하기":
            st.balloons()
            st.success("정답! 당신은 2026년 승진 대상자(희망사항)입니다!")