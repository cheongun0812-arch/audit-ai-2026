import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
import io
import plotly.express as px
from io import BytesIO

# =========================================================
# 1) 페이지 설정 및 기존 고급 디자인 CSS
# =========================================================
st.set_page_config(page_title="Executive & Shared Card Audit", layout="wide")

st.markdown("""
<style>
    :root {
        --bg: #0B0D10;
        --panel: #12151B;
        --gold: #D6B25E;
        --text: #EDEFF4;
        --border: #232836;
    }
    .stApp { 
        background: radial-gradient(1200px 600px at 20% 0%, rgba(214,178,94,.08), transparent 60%), var(--bg); 
        color: var(--text); 
    }
    .hero { 
        background: linear-gradient(135deg, rgba(214,178,94,.15) 0%, rgba(214,178,94,.06) 30%); 
        border: 1px solid var(--border); 
        border-radius: 18px; padding: 25px; margin-bottom: 25px; 
    }
    .panel { 
        background: var(--panel); border: 1px solid var(--border); 
        border-radius: 16px; padding: 20px; margin-bottom: 20px; 
    }
    h1, h2, h3 { color: var(--gold) !important; font-weight: 900 !important; }
    /* 메트릭 박스 스타일 */
    [data-testid="stMetric"] { 
        background: #1A1E26; border: 1px solid #2D3446; 
        border-radius: 12px; padding: 15px; 
    }
    /* 탭 스타일 조정 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1A1E26; border-radius: 8px 8px 0 0;
        padding: 10px 20px; color: #8791A6;
    }
    .stTabs [aria-selected="true"] { background-color: var(--gold) !important; color: #000 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2) 임원·직책자·공용카드 특화 분석 엔진
# =========================================================
class ComplianceEngine:
    MAP_RULES = {
        "사용자": ["사용자", "성명", "이용자", "User", "성함"],
        "가맹점": ["가맹점명", "상호", "Merchant", "가맹점", "지점"],
        "금액": ["이용금액", "금액", "Amount", "결제금액", "승인금액"],
        "일시": ["승인일시", "결제일시", "일시", "Date", "거래일시"]
    }

    @staticmethod
    def auto_mapping(df):
        mapping = {}
        cols = df.columns
        for key, aliases in ComplianceEngine.MAP_RULES.items():
            for c in cols:
                if any(alias in str(c) for alias in aliases):
                    mapping[key] = c
                    break
        return mapping

    @staticmethod
    def run_analysis(df, mapping, keywords):
        df = df.copy()
        u_col = mapping.get("사용자", "사용자")
        m_col = mapping["가맹점"]
        a_col = mapping["금액"]
        t_col = mapping["일시"]

        # 전처리
        df['P_AMT'] = pd.to_numeric(df[a_col].astype(str).str.replace('[^0-9]', '', regex=True), errors='coerce').fillna(0)
        df['P_DT'] = pd.to_datetime(df[t_col], errors='coerce')
        df['P_HOUR'] = df['P_DT'].dt.hour
        
        # [고도화 필터 1] 심야 위반 (23시-06시)
        df['F_NIGHT'] = df['P_HOUR'].apply(lambda x: x >= 23 or x <= 6)
        
        # [고도화 필터 2] 휴일 위반 (토/일)
        df['F_WEEKEND'] = df['P_DT'].dt.weekday >= 5
        
        # [고도화 필터 3] 제한업종 (키워드 매칭)
        pattern = "|".join([re.escape(k.strip()) for k in keywords if k.strip()])
        df['F_RESTRICT'] = df[m_col].astype(str).str.contains(pattern, case=False, na=False)
        
        # [고도화 필터 4] 분할 결제(쪼개기) 탐지 - 30분 이내 동일가맹점 재결제
        df = df.sort_values(by=[u_col, m_col, 'P_DT'])
        df['time_diff'] = df.groupby([u_col, m_col])['P_DT'].diff().dt.total_seconds() / 60
        df['F_SPLIT'] = (df['time_diff'] > 0) & (df['time_diff'] <= 30)

        # 종합 판정 및 사유 작성
        df['IS_VIOLATION'] = df[['F_NIGHT', 'F_WEEKEND', 'F_RESTRICT', 'F_SPLIT']].any(axis=1)
        
        def get_reason(row):
            reasons = []
            if row['F_NIGHT']: reasons.append("🌙심야")
            if row['F_WEEKEND']: reasons.append("📅휴일")
            if row['F_RESTRICT']: reasons.append("🚫제한업종")
            if row['F_SPLIT']: reasons.append("✂️분할의심")
            return " / ".join(reasons)
            
        df['비고(위반사유)'] = df.apply(get_reason, axis=1)
        return df

# =========================================================
# 3) 메인 레이아웃 및 UI
# =========================================================
st.markdown("""
<div class="hero">
    <div style="display:flex; align-items:center; gap:15px;">
        <span style="font-size:40px;">🛡️</span>
        <div>
            <h1 style="margin:0; font-size:28px;">Executive & Shared Card Audit Portal</h1>
            <p style="margin:5px 0 0 0; color:#8791A6; font-size:14px;">임원·직책자·공용카드 준법 감시 고도화 시스템 v4.6</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 사이드바 관리자 설정
with st.sidebar:
    st.markdown("### 🔐 Admin Control")
    admin_pw = st.text_input("관리자 인증", type="password", placeholder="비밀번호 입력")
    
    st.divider()
    st.markdown("### 🚫 위반 키워드 관리")
    kw_text = st.text_area("쉼표로 구분하여 입력", "노래방, 주점, 유흥, 마사지, 골프장, 사우나, 백화점, 면세점, 단란주점", height=150)
    keywords = [k.strip() for k in kw_text.split(",")]
    
    st.divider()
    st.caption("ktMOS북부 Audit AI Solution © 2026")

# 비밀번호 확인 (사용자 설정값: ktmos0402!)
if admin_pw != "ktmos0402!":
    st.info("💡 사이드바에서 관리자 비밀번호를 입력하면 분석 메뉴가 활성화됩니다.")
    st.stop()

# 파일 업로드 패널
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("#### ① 데이터 소스 업로드")
uploaded_file = st.file_uploader("법인카드 사용이력 RAW 데이터 (Excel / CSV)", type=['xlsx', 'csv'], label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    try:
        # 데이터 읽기
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
        
        engine = ComplianceEngine()
        mapping = engine.auto_mapping(df_raw)
        
        # 필수 컬럼 체크
        if not all(k in mapping for k in ["가맹점", "금액", "일시"]):
            st.error("❌ 필수 데이터(가맹점, 금액, 일시)를 자동으로 찾을 수 없습니다. 파일의 컬럼명을 확인해 주세요.")
            st.stop()

        # 분석 실행
        df_final = engine.run_analysis(df_raw, mapping, keywords)
        
        # --- 결과 대시보드 (Metrics) ---
        viol_df = df_final[df_final['IS_VIOLATION']]
        split_count = df_final['F_SPLIT'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔍 총 검토 내역", f"{len(df_final):,}건")
        c2.metric("🚨 위반 의심 총계", f"{len(viol_df):,}건")
        c3.metric("✂️ 분할결제 의심", f"{split_count:,}건")
        c4.metric("💰 위반 의심 금액", f"{viol_df['P_AMT'].sum():,.0f}원")

        st.markdown("---")

        # --- 상세 분석 탭 ---
        tab1, tab2, tab3, tab4 = st.tabs(["📋 위반 리스트", "✂️ 분할결제 정밀진단", "👤 사용자별 통계", "📥 결과 다운로드"])

        with tab1:
            st.markdown("#### 🚩 위반 의심 상세 리스트")
            st.dataframe(viol_df, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("#### ✂️ 분할 결제(쪼개기) 의심 사례")
            st.warning("동일 가맹점에서 30분 이내에 연속 결제된 내역입니다. 직책자 인당 한도 회피 여부를 중점 확인하십시오.")
            split_df = df_final[df_final['F_SPLIT'] == True]
            if not split_df.empty:
                st.dataframe(split_df, use_container_width=True, hide_index=True)
            else:
                st.success("✅ 탐지된 분할 결제 의심 사례가 없습니다.")

        with tab3:
            st.markdown("#### 👤 임원/직책자/공용별 위반 비중")
            u_col = mapping.get("사용자", "사용자")
            # 시각화 데이터 준비
            user_stats = viol_df.groupby(u_col).size().reset_index(name='위반건수').sort_values('위반건수', ascending=False)
            
            if not user_stats.empty:
                fig = px.bar(user_stats.head(20), x=u_col, y='위반건수', color='위반건수', 
                             title="상위 위반 의심자 분포 (Top 20)",
                             color_continuous_scale="OrRd", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("데이터가 없습니다.")

        with tab4:
            st.markdown("#### 📥 분석 결과 내보내기")
            st.write("위반 의심 내역 및 분석 결과가 포함된 전체 데이터를 다운로드할 수 있습니다.")
            
            col_dl1, col_dl2 = st.columns(2)
            
            # CSV 다운로드
            csv_bytes = df_final.to_csv(index=False).encode('utf-8-sig')
            col_dl1.download_button("CSV 형식으로 저장", csv_bytes, "Audit_Executive_Result.csv", "text/csv", use_container_width=True)
            
            # Excel 다운로드
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Audit_Summary')
            col_dl2.download_button("Excel 형식으로 저장", output.getvalue(), "Audit_Executive_Result.xlsx", use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ 분석 엔진 가동 중 오류가 발생했습니다: {e}")
else:
    st.info("🏢 법인카드 사용이력 RAW 데이터를 업로드하면 임원·직책자·공용카드 모니터링이 시작됩니다.")
