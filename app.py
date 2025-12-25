import streamlit as st
import pandas as pd
import time
from streamlit_lottie import st_lottie
import requests

# 페이지 설정
st.set_page_config(page_title="2026 감사실 AI 혁신 포털", page_icon="🛡️", layout="wide")

# 애니메이션 로드 함수
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

lottie_ai = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json") # AI 애니메이션

# 커스텀 CSS
st.markdown("""
    <style>
    .stApp { background: linear-gradient(to right, #0f0c29, #302b63, #24243e); color: white; }
    .report-card { background-color: rgba(255, 255, 255, 0.1); padding: 25px; border-radius: 20px; border: 1px solid #4facfe; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    h1 { font-size: 3rem; font-weight: 800; background: -webkit-linear-gradient(#eee, #333); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
    """, unsafe_allow_html=True)

# 메인 헤더
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🛡️ 2026 AUDIT AI")
    st.write("### '당신의 열정을 보호하고, 회사의 미래를 설계합니다.'")
    st.info("실장님 메시지: “우리는 감시자가 아닙니다. 당신의 성공을 돕는 AI 가디언입니다.”")
with col2:
    st_lottie(lottie_ai, height=200, key="ai_anim")

st.divider()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

with tab1:
    st.header("📄 AI 계약서 독소 조항 탐지기")
    uploaded_file = st.file_uploader("검토할 계약서를 업로드하세요", type=['pdf', 'txt'])
    if uploaded_file:
        with st.status("AI가 법률 조항을 초고속 스캔 중입니다...", expanded=True) as status:
            time.sleep(1.5); st.write("조항별 리스크 매핑 중...")
            time.sleep(1.2); st.write("유사 판례 데이터베이스 대조 중...")
            status.update(label="분석 완료! 위험 요소를 발견했습니다.", state="complete")
        
        st.markdown("""
        <div class="report-card">
            <h3 style="color: #ff4b4b;">⚠️ 주의 필요 조항 발견</h3>
            <p><b>제 15조 (손해배상):</b> "을의 과실이 없는 경우에도 갑의 손해를 전액 보상한다."</p>
            <hr>
            <p><b>🤖 AI 분석:</b> 이 조항은 공정거래법 위반 소지가 다분합니다. <b>'독소 조항'</b>으로 분류되었습니다. 
            감사실이 이미 수정안을 준비해 두었으니, 법무팀 전달 전 상담을 요청하세요!</p>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.header("📊 AI 법인카드 투명성 대시보드")
    st.write("2026년 1월 현재, 전사 준법 지수는 **'매우 맑음(98%)'** 입니다.")
    col_a, col_b = st.columns(2)
    with col_a:
        df = pd.DataFrame({'부서': ['영업', '마케팅', 'R&D', '관리'], '안전지수': [85, 92, 98, 95]})
        st.bar_chart(df, x='부서', y='안전지수')
    with col_b:
        st.success("✨ 이번 달 '클린 카드' 부서: R&D팀 (축하합니다!)")
        st.warning("⚠️ 주의: 야간 택시비 증빙 누락 건이 증가하고 있습니다. AI가 자동 안내문을 발송할 예정입니다.")

with tab3:
    st.header("💬 AI 실장님 준법 상담소")
    user_input = st.text_input("고민되는 상황을 입력해 보세요. (예: 협력사에서 선물을 주겠다고 합니다.)")
    if user_input:
        st.chat_message("assistant").write(f"'{user_input}'에 대한 실장님의 AI 가이드:")
        st.write("“그 마음은 감사하지만, 우리 회사의 윤리 강령 제 3조에 위배될 수 있습니다. 정중히 거절하는 법을 AI가 메일 초안으로 써드릴까요?”")
