import streamlit as st
import google.generativeai as genai
from PIL import Image  # 💡 이미지 처리를 위해 추가된 라이브러리

# ---------------------------------------------------
# 페이지 설정 및 상태 초기화
# ---------------------------------------------------
st.set_page_config(
    page_title="TalkInsight",
    page_icon="💬",
    layout="wide"
)

# 모바일 환경에서 당겨서 새로고침(Pull-to-refresh) 방지
st.markdown(
    """
    <style>
    body { overscroll-behavior-y: none; }
    </style>
    """,
    unsafe_allow_html=True
)

if 'sim_history' not in st.session_state:
    st.session_state.sim_history = []
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

st.title("💬 TalkInsight")
st.caption("(다자간 대화 & 시뮬레이션 지원)")
st.caption("보안 정책에 따라 분석에 사용된 데이터는 저장되지 않고 즉시 휘발됩니다.")

# ---------------------------------------------------
# AI 모델 자동 탐색
# ---------------------------------------------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    if not available_models:
        st.error("현재 API 키로 사용할 수 있는 AI 모델이 없습니다.")
        st.stop()

    if 'gemini-1.5-flash' in available_models: target_model_name = 'gemini-1.5-flash'
    elif 'gemini-1.5-pro' in available_models: target_model_name = 'gemini-1.5-pro'
    elif 'gemini-pro' in available_models: target_model_name = 'gemini-pro'
    else: target_model_name = available_models[0]
        
    model = genai.GenerativeModel(target_model_name)
except Exception as e:
    st.error(f"AI 초기 설정 중 오류가 발생했습니다: {e}")
    st.stop()

# ---------------------------------------------------
# 사용자 및 대화 참여자 설정
# ---------------------------------------------------
st.subheader("👤 대화 참여자 설정")

col_me, col_others = st.columns([1, 2.5])

with col_me:
    st.markdown("#### 🔴 내 정보")
    my_name = st.text_input("내 이름 (본인)", value="나")

with col_others:
    st.markdown("#### 🔵 대화 상대방 목록")
    if 'num_participants' not in st.session_state: st.session_state.num_participants = 1
        
    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
    with btn_col1:
        if st.button("➕ 추가"): st.session_state.num_participants += 1; st.rerun()
    with btn_col2:
        if st.button("➖ 제거") and st.session_state.num_participants > 1:
            st.session_state.num_participants -= 1; st.rerun()
            
    other_participants = []
    mbti_options = ["모름/상관없음", "ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP", "ESTP", "ESFP", "ENFP", "ENTP", "ESTJ", "ESFJ", "ENFJ", "ENTJ"]
    
    for i in range(st.session_state.num_participants):
        st.markdown(f"**👤 상대방 {i+1}**")
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1: p_name = st.text_input("이름", value=f"상대방{i+1}", key=f"p_name_{i}")
        with row1_col2: p_rel = st.text_input("나와의 관계", key=f"p_rel_{i}")
            
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1: p_mbti = st.selectbox("MBTI", mbti_options, key=f"p_mbti_{i}")
        with row2_col2: p_age = st.text_input("나이/연령대", key=f"p_age_{i}")
        
        st.divider()
        other_participants.append({"name": p_name, "relation": p_rel, "mbti": p_mbti, "age": p_age})

def get_participants_info_str():
    info_str = ""
    for p in other_participants:
        info_str += f"- 이름: {p['name']} (관계: {p['relation']}, MBTI: {p['mbti']}, 나이: {p['age']})\n"
    return info_str

# ---------------------------------------------------
# 내용 입력
# ---------------------------------------------------
st.subheader("📝 대화 내용 입력")

text_data = st.text_area("메신저 대화 내용 (텍스트)", height=150)
uploaded_files = st.file_uploader("대화 캡쳐 이미지 업로드", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# ---------------------------------------------------
# AI 분석 로직
# ---------------------------------------------------
st.subheader(f"🤖 AI 대화 분석 (모델: {target_model_name})")

if st.button("분석 시작"):
    if not text_data and not uploaded_files:
        st.error("텍스트를 입력하거나 이미지를 업로드해 주세요.")
        st.stop()

    with st.spinner("제공된 텍스트와 카카오톡 이미지를 정밀 분석 중입니다..."):
        try:
            participants_info = get_participants_info_str()
            prompt = f"""
다음 정보를 바탕으로 메신저 대화 내용을 분석해줘.

[내 정보]
- 이름: {my_name}

[대화 상대방 정보]
{participants_info}

[입력된 대화 텍스트]
{text_data}

[🚨 절대 준수해야 할 핵심 지시사항 🚨]
1. 첨부된 사진이 있다면, **절대로 대화 내용을 스스로 상상하거나 지어내지 마세요.** 사진에 찍힌 카카오톡/메신저 말풍선 속 글자들만 100% 그대로 읽어내야 합니다.
2. 사진 속 텍스트와 [입력된 대화 텍스트]를 모두 합쳐서 대화의 흐름을 파악하세요.
3. 참여자별 심리 상태 분석 (MBTI, 관계, 대화 뉘앙스 기반)
4. 현재 대화방의 분위기
5. '{my_name}'이(가) 보낼 만한 추천 답장 3개 (각각의 이유 포함)
6. 강력 추천 답장 1개
"""
            contents = [prompt]
            # 💡 PIL Image 객체로 변환하여 구글 AI에 직접 전달 (인식률 100% 상향)
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    img = Image.open(uploaded_file)
                    contents.append(img)

            response = model.generate_content(contents)
            st.session_state.analysis_result = response.text
            st.success("분석 완료!")
        except Exception as e:
            st.error(f"분석 중 오류 발생: {e}")

if st.session_state.analysis_result:
    st.markdown(st.session_state.analysis_result)

st.divider()

# ---------------------------------------------------
# 시뮬레이션 로직
# ---------------------------------------------------
st.subheader("🎭 답장 시뮬레이션")

if st.button("🔄 시뮬레이션 초기화"):
    st.session_state.sim_history = []
    st.rerun()

for msg in st.session_state.sim_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_msg := st.chat_input("테스트해 볼 메시지를 입력하세요..."):
    st.session_state.sim_history.append({"role": "user", "content": f"**{my_name}**: {user_msg}"})
    
    with st.chat_message("user"):
        st.markdown(f"**{my_name}**: {user_msg}")
        
    with st.spinner("상대방이 타이핑 중입니다..."):
        try:
            participants_info = get_participants_info_str()
            history_str = "\n".join([msg["content"] for msg in st.session_state.sim_history])
            
            sim_prompt = f"""
당신은 메신저 대화 시뮬레이터입니다. AI처럼 행동하지 마세요.

[내 이름]
{my_name}

[대화 상대방 정보]
{participants_info}

[입력된 대화 텍스트]
{text_data}

[현재까지의 시뮬레이션 대화 기록]
{history_str}

[🚨 절대 준수해야 할 핵심 지시사항 🚨]
1. 첨부된 사진이 있다면, **절대로 기존 대화를 상상하거나 지어내지 마세요.** 사진에 실제로 적혀 있는 말풍선 내용만 참고하십시오.
2. 입력된 텍스트와 첨부된 캡처 사진을 모두 참고하여 상대방(들)의 입장에서 방금 {my_name}이 보낸 메시지에 답장하세요.
3. 사진 속 대화의 말투와 뉘앙스를 철저하게 모방하세요.
4. 메신저 특성상 너무 길게 말하지 않고 짧고 자연스럽게 대답하세요.
5. 분석이나 부가 설명 없이 오직 '답장 메시지'만 출력하세요.
6. 다자간 대화일 경우 "이름: 대답" 형식으로 작성하세요.
"""
            sim_contents = [sim_prompt]
            # 💡 시뮬레이션에서도 PIL Image 객체 활용
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    img = Image.open(uploaded_file)
                    sim_contents.append(img)

            response = model.generate_content(sim_contents)
            st.session_state.sim_history.append({"role": "assistant", "content": response.text.strip()})
            st.rerun()
                
        except Exception as e:
            st.error(f"시뮬레이션 중 오류 발생: {e}")
