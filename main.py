import io
import zipfile
import urllib.request
import pandas as pd
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

# 따뜻한 메인 타이틀 및 안내문
st.title("👨‍👩‍👧‍👦 우리 동네 인구 피라미드")
st.write("궁금한 지역을 선택하시면 가장 최신 연도 기준의 남녀 인구 구조를 피라미드 그래프로 보여드립니다.")

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
            
    # 가장 최신 연도 데이터만 추출 (예: 2026년 또는 존재하는 가장 최근 연도)
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

# 2) 시·군·구 선택 (선택한 시·도 내부 데이터로 필터링)
filtered_sido = df[df['시도'] == selected_sido]
sigungu_list = sorted(filtered_sido['시군구'].dropna().unique())
selected_sigungu = st.selectbox("시·군·구를 선택하세요", sigungu_list)

# 3) 읍·면·동 선택 (선택한 시·군·구 내부 데이터로 필터링)
filtered_sigungu = filtered_sido[filtered_sido['시군구'] == selected_sigungu]
dong_list = sorted(filtered_sigungu['동'].dropna().unique())
selected_dong = st.selectbox("읍·면·동을 선택하세요", dong_list)

# -----------------------------------------------------------------------------
# 4. 선택한 동네 데이터 정리 및 나이대 열(Column) 구성
# -----------------------------------------------------------------------------
# 최종 선택된 1개 행(동네 데이터) 추출
target_row = filtered_sigungu[filtered_sigungu['동'] == selected_dong].iloc[0]

# 0세부터 99세까지 + 100세 이상 라벨 순서 생성 (0세가 맨 앞, 100세 이상이 맨 뒤)
age_categories = [f"{i}세" for i in range(101)]
age_categories[-1] = "100세 이상"  # 100세 -> 100세 이상으로 이름 변경

# 남자/여자 각 나이별 인구수 데이터 모으기
male_counts = []
female_counts = []

for age in age_categories:
    male_col = f"남_{age}"
    female_col = f"여_{age}"
    
    # 열이 존재하는지 확인 후 데이터 추가
    male_val = target_row[male_col] if male_col in target_row else 0
    female_val = target_row[female_col] if female_col in target_row else 0
    
    male_counts.append(male_val)
    female_counts.append(female_val)

# 남성 인구수는 피라미드 왼쪽 표시를 위해 음수로 전환
male_counts_negative = [-val for val in male_counts]

# -----------------------------------------------------------------------------
# 5. Plotly 가로 막대 그래프 (인구 피라미드) 작성
# -----------------------------------------------------------------------------
fig = go.Figure()

# (1) 남성 인구 (왼쪽 방향 / 코랄 핑크 톤의 따뜻한 톤)
fig.add_trace(go.Bar(
    y=age_categories,
    x=male_counts_negative,
    name='남성',
    orientation='h',
    marker_color='#5B8FF9',  # 부드러운 블루
    hoverinfo='text',
    hovertext=[f"<b>{age} 남성</b>: {count:,}명" for age, count in zip(age_categories, male_counts)]
))

# (2) 여성 인구 (오른쪽 방향 / 로즈 코랄 톤)
fig.add_trace(go.Bar(
    y=age_categories,
    x=female_counts,
    name='여성',
    orientation='h',
    marker_color='#F68484',  # 따뜻한 로즈 코랄
    hoverinfo='text',
    hovertext=[f"<b>{age} 여성</b>: {count:,}명" for age, count in zip(age_categories, female_counts)]
))

# (3) 레이아웃 및 Y축 순서 고정 설정
# y축 카테고리 순서를 0세(아래) -> 100세 이상(위) 배열 순서 그대로 강제 지정합니다.
fig.update_layout(
    title=dict(
        text=f"<b>[{selected_sido} {selected_sigungu} {selected_dong}] 인구 피라미드</b>",
        font=dict(size=18)
    ),
    barmode='overlay',      # 양쪽 배치 형태
    bargap=0.1,             # 막대 사이 간격
    height=800,             # 피라미드 높이
    xaxis=dict(
        title="인구수 (명)",
        tickformat=",d",    # 천 단위 쉼표 표기
        # 음수로 표시된 x축 눈금을 보기 좋게 양수로 재표기
        tickvals=[-x for x in range(0, max(male_counts + female_counts) + 1, max(1, max(male_counts + female_counts) // 4))] + 
                 [x for x in range(0, max(male_counts + female_counts) + 1, max(1, max(male_counts + female_counts) // 4))],
        ticktext=[f"{abs(x):,}" for x in range(0, max(male_counts + female_counts) + 1, max(1, max(male_counts + female_counts) // 4))] + 
                 [f"{x:,}" for x in range(0, max(male_counts + female_counts) + 1, max(1, max(male_counts + female_counts) // 4))]
    ),
    yaxis=dict(
        title="연령",
        type='category',               # 범주형 축으로 설정
        categoryorder='array',          # 지정한 리스트 순서대로 축 배치
        categoryarray=age_categories,  # 맨 아래가 0세, 맨 위가 100세 이상
        dtick=5                         # Y축 눈금을 5세 단위로 표시하여 깔끔하게 보임
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

# -----------------------------------------------------------------------------
# 6. Streamlit 화면 출력 및 총인구 요약
# -----------------------------------------------------------------------------
# 시각화 출력
st.plotly_chart(fig, use_container_width=True)

# 주요 통계 요약 카드
total_male = sum(male_counts)
total_female = sum(female_counts)
total_pop = total_male + total_female

st.markdown("---")
st.markdown(f"#### 📊 **{selected_dong}** 인구 요약")
col1, col2, col3 = st.columns(3)
col1.metric("총인구", f"{total_pop:,} 명")
col2.metric("남성 인구", f"{total_male:,} 명")
col3.metric("여성 인구", f"{total_female:,} 명")
