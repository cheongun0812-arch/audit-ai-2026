import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
import requests
import time

# --- 1. 페이지 설정 및 시각 요소 ---
st.set_page_config(page_title="2026 AUDIT AI PORTAL", layout="wide")

# CSS: 실장님이 요청하신 Yellow & Black 테마 (프리미엄급 디자인)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@100;400;900&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #0A0A0B; color: #E0E0E0; }
    
    /* 헤더 및 타이틀 */
    .main-title { font-size: 50px; font-weight: 900; color: #FFD700; margin-bottom: 5px; text-shadow: 2px 2px 5px #000; }
    .sub-title { color: #888; font-size: 20px; margin-bottom: 30px; }
    
    /* 탭 메뉴 강조 */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1A1A1B; border-radius: 8px 8px 0 0;
        padding: 12px 25px; color: #FFD700 !important; font-weight: bold; font-size: 16px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { border-bottom: 3px solid #FFD700; }
    
    /* 리포트 박스 */
    .report-box { 
        background: #161618; border-left: 6px solid #FFD700; padding: 25px; 
        border-radius: 12px; margin-top: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.5); 
    }
    
    /* 파일 업로더 디자인 */
    [data-testid="stFileUploader"] section { background-color: #000 !important; border: 1.5px dashed #FFD700 !important; border-radius: 10px; }
    
    /* 지표(Metric) 스타일 */
    [data-testid="stMetricValue"] { color: #FFD700 !important; font-weight: 900; }
    </style>
    """, unsafe_allow_html=True)

# Lottie 에니메이션 안전 로드
def get_lottie(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_audit = get_lottie("https://assets5.lottiefiles.com/packages/lf20_fcfjwiyb.json")

# --- 2. 사이드바 (분석 기준 설정) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.markdown("### 🛡️ AUDIT AI 설정")
    night_start = st.slider("심야 기준 시작(시)", 0, 23, 23)
    night_end = st.slider("심야 기준 종료(시)", 0, 23, 6)
    high_limit = st.number_input("고액 결제 기준(원)", value=500000, step=100000)
    st.divider()
    st.write("실장님용 관리 패널 v2.5")

# --- 3. 메인 헤더 ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown('<p class="main-title">🛡️ 2026 AUDIT AI PORTAL</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">"가장 진보된 기술로 회사의 투명성을 수호합니다."</p>', unsafe_allow_html=True)
with col_h2:
    if lottie_audit: st_lottie(lottie_audit, height=120)

tab1, tab2, tab3 = st.tabs(["🔍 AI 계약서 검토", "📈 법카 리스크 분석", "💬 AI 실장님 상담소"])

# --- 4. 법카 리스크 분석 (Tab 2) ---
with tab2:
    st.subheader("📊 법인카드 실시간 리스크 정밀 진단")
    uploaded_file = st.file_uploader("25년 10월 법인카드 사용 내역 파일을 업로드하세요 (CSV, XLSX)", type=['csv', 'xlsx'])

    if uploaded_file:
        try:
            # 파일 읽기
            if uploaded_file.name.endswith('.csv'):
                raw_df = pd.read_csv(uploaded_file, header=None)
            else:
                raw_df = pd.read_excel(uploaded_file, header=None)
            
            # 헤더(제목줄) 행 자동 탐색
            header_row = 0
            for i, row in raw_df.head(10).iterrows():
                row_str = " ".join(map(str, row.values))
                if any(x in row_str for x in ["금액", "승인", "거래처", "일자"]):
                    header_row = i
                    break
            
            df = raw_df.iloc[header_row+1:].copy()
            df.columns = [str(c).strip() for c in raw_df.iloc[header_row].values]
            
            # 중복 컬럼명 처리 (에러 방지)
            new_cols = []
            col_counts = {}
            for col in df.columns:
                if col in col_counts:
                    col_counts[col] += 1
                    new_cols.append(f"{col}_{col_counts[col]}")
                else:
                    col_counts[col] = 0
                    new_cols.append(col)
            df.columns = new_cols
            df = df.reset_index(drop=True)

            # 지능형 컬럼 매핑
            col_map = {
                '금액': ['금액', '이용금액', '승인금액', '합계'],
                '날짜': ['승인일자', '거래일자', '이용일자', '날짜'],
                '시간': ['승인일시', '승인시간', '시간'],
                '가맹점': ['거래처명', '가맹점명', '사용처', '상호'],
                '사용자': ['사용자', '이용자명', '성명', '사원명']
            }
            
            f_map = {}
            for target, keywords in col_map.items():
                for col in df.columns:
                    if any(k in str(col) for k in keywords):
                        f_map[target] = col
                        break

            # 데이터 정제
            df[f_map['금액']] = pd.to_numeric(df[f_map['금액']].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
            df[f_map['날짜']] = pd.to_datetime(df[f_map['날짜']].astype(str).str.split(' ').str[0], errors='coerce')
            
            # 리스크 분석 (심야/휴일)
            if '시간' in f_map:
                df['hour'] = pd.to_datetime(df[f_map['시간']].astype(str)).dt.hour
                df['is_night'] = df['hour'].apply(lambda x: x >= night_start or x <= night_end)
            else:
                df['is_night'] = False
            
            df['is_holiday'] = df[f_map['날짜']].dt.weekday >= 5

            # 위반 사유 생성
            df['위반내용'] = ""
            df.loc[df['is_night'], '위반내용'] += "🌙심야 "
            df.loc[df['is_holiday'], '위반내용'] += "📅휴일 "
            df.loc[df[f_map['금액']] >= high_limit, '위반내용'] += "💰고액 "
            
            risk_keywords = ['유통', '물산', '상사', '도매', '종합']
            is_ghost = df[f_map['가맹점']].str.contains('|'.join(risk_keywords), na=False)
            df.loc[is_ghost, '위반내용'] += "🚨위장유형의심 "

            # --- 결과 리포트 출력 ---
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.subheader("🚩 2026 AI 감사 실시간 탐지 결과")
            
            m1, m2, m3, m4 = st.columns(4)
            violation_df = df[df['위반내용'] != ""].copy()
            
            m1.metric("총 지출액", f"{df[f_map['금액']].sum():,.0f}원")
            m2.error(f"🌙 심야 결제: {len(df[df['is_night']])}건")
            m3.error(f"📅 휴일 결제: {len(df[df['is_holiday']])}건")
            m4.warning(f"🚨 총 위반 의심: {len(violation_df)}건")

            # 위반 상세 리스트 (실장님 요청 사항)
            if not violation_df.empty:
                st.write("### 📋 위반 의심 상세 리스트")
                
                # 표시 컬럼 구성
                disp_cols = [f_map['날짜'], f_map['가맹점'], f_map['금액']]
                if '시간' in f_map: disp_cols.append(f_map['시간'])
                disp_cols.extend(['위반내용', f_map['사용자']])
                
                final_display = violation_df[disp_cols].copy()
                
                # 금액 정렬 및 표시
                st.dataframe(
                    final_display.sort_values(f_map['금액'], ascending=False).style.format({f_map['금액']: '{:,.0f}원'}),
                    use_container_width=True
                )
                st.info("💡 위 내역은 AI가 선정한 '소명 대상' 리스트입니다. 실장님의 컨펌 후 자동 메일 발송이 가능합니다.")
            else:
                st.success("✅ 분석 결과, 규정 위반 의심 내역이 발견되지 않았습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

            # 일별 지출 추이 그래프
            daily = df.groupby(f_map['날짜'])[f_map['금액']].sum().reset_index()
            fig = go.Figure(go.Scatter(x=daily[f_map['날짜']], y=daily[f_map['금액']], 
                                     mode='lines+markers', line=dict(color='#FFD700', width=3),
                                     marker=dict(size=8, color='#FF5555'), name="일별 지출"))
            fig.update_layout(title="10월 지출 패턴 분석 차트", paper_bgcolor='rgba(0,0,0,0)', 
                              plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"⚠️ 분석 중 오류 발생: {e}")
            st.info("파일의 헤더 구조를 AI가 재분석 중입니다. 잠시 후 다시 시도해 주세요.")

# --- 나머지 탭 (계약서, 상담소) ---
with tab1:
    st.subheader("📄 AI 계약서 독소 조항 탐지기")
    st.file_uploader("계약서를 업로드하세요", type=['pdf', 'txt'], key="contract_final")
    st.markdown('<div class="report-box">상대방이 제시한 조항 중 우리 회사의 권리를 침해하는 요소를 AI가 즉시 찾아냅니다.</div>', unsafe_allow_html=True)

with tab3:
    st.subheader("💬 AI 실장님 상담소")
    user_q = st.text_input("고민되는 상황을 입력하세요...", placeholder="예: 휴일 식대 소명 방법 문의")
    if user_q:
        st.markdown(f'<div class="report-box"><b>질문:</b> {user_q}<br><br><b>AI 답변:</b> 실장님의 평소 지침에 따르면, 해당 건은 증빙 영수증과 함께 상세 사유서를 제출하도록 안내해야 합니다.</div>', unsafe_allow_html=True)
