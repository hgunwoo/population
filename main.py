import io
import zipfile
import urllib.request
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 디자인 (따뜻한 톤)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered"
)

st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.write("궁금한 지역을 선택하시면 가장 최신 연도 기준의 인구 지표와 피라미드 그래프를 보여드립니다.")

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 (캐싱 적용으로 속도 최적화)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # GitHub 저장소의 ZIP 파일 원본(Raw) 다운로드 URL
    raw_zip_url = "https://raw.githubusercontent.com/hgunwoo/population/main/population_ts_yearly_gender.zip"
    
    # URL에서 ZIP 바이너리 데이터 가져오기
    req = urllib.request.Request(raw_zip_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        zip_data = response.read()
    
    # 메모리에서 압축 해제 후 첫 번째 CSV 파일 읽기
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        csv_filename = z.namelist()[0]
        with z.open(csv_filename) as f:
            df = pd.read_csv(f)
            
    # 가장 최신 연도 데이터만 추출
    max_year = df['연도'].max()
    latest_df = df[df['연도'] == max_year].copy()
    
    return latest_df, max_year

# 데이터 로딩 실행
with st.spinner("지역별 인구 데이터를 불러오는 중입니다... 잠시만 기다려주세요 ☕"):
    df, latest_year = load_data()

st.caption(f"📌 **{latest_year}년** 최신 데이터 기준으로 조회됩니다.")

# -----------------------------------------------------------------------------
# 3. 3단계 드롭다운 메뉴 (시도 ➡️ 시군구 ➡️ 동)
# -----------------------------------------------------------------------------
st.subheader("📍 지역 선택")

# 1) 시·도 선택
sido_list = sorted(df['시도'].dropna().unique())
selected_sido = st.selectbox("시·도를 선택하세요", sido_list)

# 2) 시·군·구 선택
filtered_sido = df[df['시도'] == selected_sido]
sigungu_list = sorted(filtered_sido['시군구'].dropna().unique())
selected_sigungu = st.selectbox("시·군·구를 선택하세요", sigungu_list)

# 3) 읍·면·동 선택
filtered_sigungu = filtered_sido[filtered_sido['시군구'] == selected_sigungu]
dong_list = sorted(filtered_sigungu['동'].dropna().unique())
selected_dong = st.selectbox("읍·면·동을 선택하세요", dong_list)

# -----------------------------------------------------------------------------
# 4. 선택한 동네 데이터 정리 및 지표 계산
# -----------------------------------------------------------------------------
# 선택된 1개 행 추출
target_row = filtered_sigungu[filtered_sigungu['동'] == selected_dong].iloc[0]

# 0세부터 100세 이상까지 라벨 구성
age_categories = [f"{i}세" for i in range(101)]
age_categories[-1] = "100세 이상"

male_counts = []
female_counts = []
total_counts_by_age = []  # 각 연령별 총인구수 (남 + 여)

for age in age_categories:
    male_col = f"남_{age}"
    female_col = f"여_{age}"
    
    m_val = target_row[male_col] if male_col in target_row else 0
    f_val = target_row[female_col] if female_col in target_row else 0
    
    male_counts.append(m_val)
    female_counts.append(f_val)
    total_counts_by_age.append(m_val + f_val)

# 남성 인구수는 피라미드 왼쪽 표시를 위해 음수로 전환
male_counts_negative = [-val for val in male_counts]

# -----------------------------------------------------------------------------
# [지표 계산] 총인구, 평균연령, 고령화율, 유소년 비율
# -----------------------------------------------------------------------------
total_pop = sum(total_counts_by_age)

if total_pop > 0:
    # 각 연령의 수치값 (0세~99세는 숫자 그대로, 100세 이상은 대표값 100세로 설정)
    ages = np.array(list(range(100)) + [100])
    
    # 평균연령 = (각 나이 * 해당 나이 인구)의 총합 / 총인구
    mean_age = float(np.sum(ages * np.array(total_counts_by_age)) / total_pop)
    
    # 고령인구 (65세 이상: Index 65 ~ 100)
    senior_pop = sum(total_counts_by_age[65:])
    aging_rate = (senior_pop / total_pop) * 100
    
    # 유소년인구 (14세 이하: Index 0 ~ 14)
    child_pop = sum(total_counts_by_age[:15])
    child_rate = (child_pop / total_pop) * 100
else:
    mean_age = 0.0
    aging_rate = 0.0
    child_rate = 0.0

# -----------------------------------------------------------------------------
# 5. 상단 지표 카드 3개 표시 (그래프 위)
# -----------------------------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)

# 1) 총인구 카드
col1.metric("총인구", f"{total_pop:,} 명")

# 2) 평균연령 카드
col2.metric("평균연령", f"{mean_age:.1f} 세")

# 3) 고령화율 카드 (20% 초과 초고령사회 진입 시 🚨 주의 표시 및 delta 알림)
if aging_rate >= 20.0:
    col3.metric(
        "고령화율 🚨", 
        f"{aging_rate:.1f}%", 
        delta="초고령사회 (20% 이상)", 
        delta_color="inverse"
    )
else:
    col3.metric(
        "고령화율", 
        f"{aging_rate:.1f}%"
    )

# 고령화율 20% 이상인 경우 경고 메시지 박스 추가 표시
if aging_rate >= 20.0:
    st.warning("⚠️ **주의**: 이 지역은 고령인구(65세 이상) 비율이 20%를 넘는 **초고령사회** 지역입니다.")

# -----------------------------------------------------------------------------
# 6. Plotly 가로 막대 그래프 (인구 피라미드) 작성
# -----------------------------------------------------------------------------
fig = go.Figure()

# (1) 남성 인구 (왼쪽 방향 / 부드러운 블루)
fig.add_trace(go.Bar(
    y=age_categories,
    x=male_counts_negative,
    name='남성',
    orientation='h',
    marker_color='#5B8FF9',
    hoverinfo='text',
    hovertext=[f"<b>{age} 남성</b>: {count:,}명" for age, count in zip(age_categories, male_counts)]
))

# (2) 여성 인구 (오른쪽 방향 / 따뜻한 로즈 코랄)
fig.add_trace(go.Bar(
    y=age_categories,
    x=female_counts,
    name='여성',
    orientation='h',
    marker_color='#F68484',
    hoverinfo='text',
    hovertext=[f"<b>{age} 여성</b>: {count:,}명" for age, count in zip(age_categories, female_counts)]
))

# (3) 레이아웃 및 Y축 순서 고정 설정 (0세 맨 아래, 100세 이상 맨 위)
max_val = max(max(male_counts), max(female_counts)) if total_pop > 0 else 100
tick_step = max(1, max_val // 4)
ticks = list(range(0, max_val + 1, tick_step))

fig.update_layout(
    title=dict(
        text=f"<b>[{selected_sido} {selected_sigungu} {selected_dong}] 인구 피라미드</b>",
        font=dict(size=18)
    ),
    barmode='overlay',
    bargap=0.1,
    height=800,
    xaxis=dict(
        title="인구수 (명)",
        tickvals=[-x for x in reversed(ticks)] + ticks,
        ticktext=[f"{x:,}" for x in reversed(ticks)] + [f"{x:,}" for x in ticks]
    ),
    yaxis=dict(
        title="연령",
        type='category',
        categoryorder='array',
        categoryarray=age_categories,  # 0세가 맨 아래, 100세 이상이 맨 위로 고정
        dtick=5
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    template="plotly_white"
)

# 그래프 출력
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 7. 피라미드 하단 자동 인구 구조 한 줄 분석
# -----------------------------------------------------------------------------
# 유소년(14세 이하)과 고령(65세 이상) 비율 비교에 따른 자동 문구 생성
if child_rate > aging_rate + 5:
    analysis_text = f"👶 **{selected_dong}**은(는) 유소년(14세 이하, {child_rate:.1f}%) 비율이 고령인구({aging_rate:.1f}%)보다 높은 **아이가 상대적으로 많은 동네**입니다."
elif aging_rate > child_rate + 5:
    analysis_text = f"👵 **{selected_dong}**은(는) 고령인구(65세 이상, {aging_rate:.1f}%) 비율이 유소년({child_rate:.1f}%)보다 높은 **어르신이 상대적으로 많은 동네**입니다."
else:
    analysis_text = f"⚖️ **{selected_dong}**은(는) 유소년({child_rate:.1f}%)과 고령인구({aging_rate:.1f}%) 비율이 **비슷하게 균형을 이루는 동네**입니다."

st.info(f"💡 **이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?**\n\n{analysis_text}")
