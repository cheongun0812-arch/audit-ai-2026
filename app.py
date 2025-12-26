import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time
import io

# --- 페이지 설정 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# --- CSS (Yellow & Gold 프리미엄 테마) ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    .main-title { font-size: 45px; font-weight: 900; color: #FFD700; margin-bottom: 0px; text-shadow: 2px 2px 4px #000; }
    .report-box { background: #161618; border-left: 5px solid #FFD700; padding: 20px; border-radius: 10px; margin-top: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #FFD700 !important; font-weight: bold; }
    [data-testid="stFileUploader"] section { background-color: #000 !important; border: 1px dashed #FFD700 !important; }
    .stMetric { background-color: #1A1A1B; padding: 15px; border-radius: 10px; border: 1px solid #333; }
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
st.write("“디지털 감사 혁신, 실장님과 AI가 함께 만듭니다.”")
if lottie_main: st_lottie(lottie_main, height=100)

tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# --- Tab 2: 법카 리스크 분석 ---
with tab2:
    st.subheader("📊 법인카드 지출 패턴 분석기")
    uploaded_file = st.file_uploader("25년 10월 법인카드 사용 내역 (CSV/XLSX)", type=['csv', 'xlsx'])

    if uploaded_file:
        try:
            # 1. 파일 읽기
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file, header=None)
            else:
                raw_df = pd.read_excel(uploaded_file, header=None)
            
            # 2. 진짜 헤더(제목 줄) 찾기 로직
            header_row = 0
            for i, row in raw_df.head(10).iterrows():
                row_str = " ".join(map(str, row.values))
                if "금액" in row_str or "승인" in row_str or "거래처" in row_str:
                    header_row = i
                    break
            
            df = raw_df.iloc[header_row+1:].copy()
            df.columns = raw_df.iloc[header_row].values
            
            # 중복 컬럼 이름 처리 (에러 방지 핵심!)
            new_cols = []
            col_counts = {}
            for col in df.columns:
                c = str(col).strip()
                if c in col_counts:
                    col_counts[c] += 1
                    new_cols.append(f"{c}_{col_counts[c]}")
                else:
                    col_counts[c] = 0
                    new_cols.append(c)
            df.columns = new_cols
            df = df.reset_index(drop=True)

            # 3. 지능형 컬럼 매핑
            col_map = {
                '금액': ['금액', '이용금액', '승인금액', '합계'],
                '날짜': ['승인일자', '거래일자', '이용일자', '승인일시'],
                '가맹점': ['거래처명', '가맹점명', '사용처', '상호'],
                '사용자': ['사용자', '이용자명', '성명', '사원명']
            }
            
            final_map = {}
            for target, keywords in col_map.items():
                for col in df.columns:
                    if any(k in str(col) for k in keywords):
                        final_map[target] = col
                        break

            # 데이터 정제 (금액/날짜 변환)
            df[final_map['금액']] = pd.to_numeric(df[final_map['금액']].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
            df[final_map['날짜']] = pd.to_datetime(df[final_map['날짜']].astype(str).str.split(' ').str[0], errors='coerce')
            
            # 4. 분석 결과 출력
            with st.spinner("AI 감사 에이전트가 가동 중입니다..."):
                time.sleep(1)

            total_amt = df[final_map['금액']].sum()
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("총 집행 금액", f"{total_amt:,.0f} 원")
            with m2: st.metric("분석 대상 건수", f"{len(df)} 건")
            with m3: st.metric("고액 결제(50만↑)", f"{len(df[df[final_map['금액']] >= 500000])} 건")

            # 일별 주식 차트형 그래프
            daily = df.groupby(final_map['날짜'])[final_map['금액']].sum().reset_index()
            fig = go.Figure(go.Scatter(x=daily[final_map['날짜']], y=daily[final_map['금액']], 
                                     mode='lines+markers', line=dict(color='#FFD700', width=3),
                                     marker=dict(size=8, color='#FF5555'), name="일별 사용액"))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
                              xaxis_title="날짜", yaxis_title="금액(원)", height=400)
            st.plotly_chart(fig, use_container_width=True)

            # 세부 내역 (실장님이 보기 편하게 핵심만 추출)
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.subheader("🚩 AI 주요 감지 내역")
            display_df = df[[final_map['날짜'], final_map['가맹점'], final_map['금액'], final_map['사용자']]].copy()
            display_df.columns = ['거래일자', '가맹점명', '이용금액', '사용자'] # 보기 좋게 이름 변경
            st.dataframe(display_df.sort_values('이용금액', ascending=False).head(20), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"⚠️ 데이터 처리 중 오류 발생: {e}")
            st.info("파일의 헤더 구조가 복잡할 수 있습니다. AI가 계속 학습 중이니 다시 시도해 주세요.")

with tab3:
    st.subheader("💬 AI 실장님 상담소")
    st.info("실장님, 임직원들의 고민을 AI가 먼저 필터링하여 보고합니다.")
    user_q = st.text_input("질문 예시: 주말에 고객사와 식사해도 되나요?", key="chat_input")
    if user_q:
        st.chat_message("assistant").write(f"실장님 AI 가이드: '{user_q}' 건에 대해서는 사전에 '업무 협의서'를 작성하도록 안내하는 것이 가장 안전합니다.")
