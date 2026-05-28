import streamlit as st
import google.generativeai as genai

# ---------------------------------------------------
# 페이지 설정 및 상태 초기화
# ---------------------------------------------------
st.set_page_config(
    page_title="My Messenger AI",
    page_icon="💬",
    layout="wide"
)

# 시뮬레이션 대화 기록을 저장할 세션 상태
if 'sim_history' not in st.session_state:
    st.session_state.sim_history = []

# 대화 분석 결과를 저장할 세션 상태
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

st.title("💬 My Messenger AI (다자간 대화 & 시뮬레이션 지원)")
st.caption("보안 정책에 따라 분석에 사용된 데이터는 저장되지 않고 즉시 휘발됩니다.")

# ---------------------------------------------------
# 🤖 [핵심 해결 로직] 확실히 작동하는 AI 모델 자동 탐색
# ---------------------------------------------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # 1. 현재 API 키로 사용 가능한 모든 AI 모델 목록을 불러옵니다.
    available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    if not available_models:
        st.error("현재 API 키로 사용할 수 있는 AI 모델이 없습니다. API 키를 확인해주세요.")
        st.stop()

    # 2. 가장 성능이 좋은 모델부터 순서대로 매칭하여 무조건 하나를 선택합니다.
    if 'gemini-1.5-flash' in available_models:
        target_model_name = 'gemini-1.5-flash'
    elif 'gemini-1.5-pro' in available_models:
        target_model_name = 'gemini-1.5-pro'
    elif 'gemini-pro' in available_models:
        target_model_name = 'gemini-pro'
    else:
        target_model_name = available_models[0] # 위 3개가 없으면 구글이 허용한 첫 번째 모델 강제 선택
        
    model = genai.GenerativeModel(target_model_name)
    
except Exception as e:
    st.error(f"AI 초기 설정 중 오류가 발생했습니다: {e}")
    st.stop()

# ---------------------------------------------------
# 사용자 및 대화 참여자 설정 입력
# ---------------------------------------------------
st.subheader("👤 대화 참여자 설정")

col_me, col_others = st.columns([1, 2.5])

with col_me:
    st.markdown("#### 🔴 내 정보")
    my_name = st.text_input("내 이름 (본인)", value="나", help="대화 내용에 표시되는 본인의 이름을 적어주세요.")
    st.info("💡 팁: 대화 내용에 쓰인 본인의 이름/초성을 입력하면 AI가 상황을 더 잘 이해합니다.")

with col_others:
    st.markdown("#### 🔵 대화 상대방 목록")
    
    if 'num_participants' not in st.session_state:
        st.session_state.num_participants = 1
        
    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
    with btn_col1:
        if st.button("➕ 상대방 추가"):
            st.session_state.num_participants += 1
            st.rerun()
    with btn_col2:
        if st.button("➖ 상대방 제거") and st.session_state.num_participants > 1:
            st.session_state.num_participants -= 1
            st.rerun()
            
    other_participants = []
    mbti_options = ["모름/상관없음", "ISTJ", "ISFJ", "INFJ", "INTJ", "ISTP", "ISFP", "INFP", "INTP", "ESTP", "ESFP", "ENFP", "ENTP", "ESTJ", "ESFJ", "ENFJ", "ENTJ"]
    
    for i in range(st.session_state.num_participants):
        st.markdown(f"**👤 상대방 {i+1}**")
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            p_name = st.text_input("이름", value=f"상대방{i+1}", key=f"p_name_{i}")
        with row1_col2:
            p_rel = st.text_input("나와의 관계", placeholder="예: 직장 동료, 썸남/썸녀", key=f"p_rel_{i}")
            
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            p_mbti = st.selectbox("MBTI", mbti_options, key=f"p_mbti_{i}")
        with row2_col2:
            p_age = st.text_input("나이/연령대", placeholder="예: 20대 후반, 28세", key=f"p_age_{i}")
        
        st.divider()
        other_participants.append({"name": p_name, "relation": p_rel, "mbti": p_mbti, "age": p_age})

# ---------------------------------------------------
# 텍스트 및 이미지 직접 입력/업로드
# ---------------------------------------------------
st.subheader("📝 대화 내용 입력")

text_data = st.text_area(
    "메신저 대화 내용 (분석할 텍스트)",
    placeholder="여기에 기존 대화 내용을 붙여넣으세요.\n\n[입력 예시]\n나: 주말에 뭐해?\n상대방1: 난 집에서 쉴 듯ㅋㅋ\n상대방2: 난 약속 있어!",
    height=200
)

uploaded_files = st.file_uploader(
    "대화 캡쳐 이미지 업로드 (선택사항)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

def get_participants_info_str():
    info_str = ""
    for p in other_participants:
        mbti_info = f", MBTI: {p['mbti']}" if p['mbti'] != "모름/상관없음" else ""
        age_info = f", 나이/연령대: {p['age']}" if p['age'] else ""
        info_str += f"- 이름: {p['name']} (관계: {p['relation']}{mbti_info}{age_info})\n"
    return info_str

# ---------------------------------------------------
# Gemini 분석
# ---------------------------------------------------
st.subheader(f"🤖 AI 대화 분석 (사용 중인 모델: {target_model_name})")

if st.button("분석 시작"):
    if not text_data and not uploaded_files:
        st.error("텍스트를 입력하거나 이미지를 업로드해 주세요.")
        st.stop()

    with st.spinner("AI가 대화 상대방의 성향을 바탕으로 심리를 분석 중입니다..."):
        try:
            participants_info = get_participants_info_str()
            prompt = f"""
다음 정보를 바탕으로 메신저 대화 내용을 분석해줘.

[내 정보 (분석 요청자)]
- 이름: {my_name}

[대화 상대방 정보]
{participants_info}

[대화 텍스트 내용]
{text_data}

가능하다면 다음 항목들을 상세히 분석해줘:
1. 참여자별 심리 상태 분석 (MBTI, 관계, 대화 뉘앙스 기반)
2. 현재 대화방의 분위기
3. '{my_name}'(나)이 보낼 만한 추천 답장 3개 (각각의 이유 포함)
4. 강력 추천 답장 1개
"""
            contents = [prompt]
            
            if uploaded_files:
                # 구버전 모델(gemini-pro)이 선택되었을 경우 이미지 처리 제외 (에러 방지)
                if '1.5' in target_model_name or 'vision' in target_model_name:
                    for uploaded_file in uploaded_files:
                        contents.append({
                            "mime_type": uploaded_file.type,
                            "data": uploaded_file.getvalue()
                        })
                else:
                    st.warning("⚠️ 현재 자동 선택된 AI 모델이 이미지를 지원하지 않아 텍스트 내용만 분석합니다.")

            # 분석 실행
            response = model.generate_content(contents)
            st.session_state.analysis_result = response.text
            st.success("분석 완료!")

        except Exception as e:
            st.error(f"분석 시스템 오류 발생: {e}")

# 세션 상태에 분석 결과가 있으면 화면에 렌더링
if st.session_state.analysis_result:
    st.markdown(st.session_state.analysis_result)

st.divider()

# ---------------------------------------------------
# 대화 시뮬레이션 기능
# ---------------------------------------------------
st.subheader("🎭 답장 시뮬레이션")
st.caption("메시지를 전송하기 전에 테스트해 보세요! AI가 입력된 MBTI와 말투를 모방하여 가상의 답장을 보냅니다.")

if st.button("🔄 시뮬레이션 대화 초기화"):
    st.session_state.sim_history = []
    st.rerun()

for msg in st.session_state.sim_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_msg := st.chat_input("테스트해 볼 메시지를 입력하세요..."):
    
    if not text_data:
        st.warning("먼저 위쪽에 '대화 내용 입력' 칸에 기존 대화 내역을 조금이라도 적어주셔야 더 정확한 시뮬레이션이 가능합니다!")
    
    st.session_state.sim_history.append({"role": "user", "content": f"**{my_name}**: {user_msg}"})
    
    with st.chat_message("user"):
        st.markdown(f"**{my_name}**: {user_msg}")
        
    with st.spinner("상대방이 타이핑 중입니다..."):
        try:
            participants_info = get_participants_info_str()
            history_str = "\n".join([msg["content"] for msg in st.session_state.sim_history])
            
            sim_prompt = f"""
당신은 메신저 대화 시뮬레이터입니다. 절대로 AI나 어시스턴트처럼 행동하지 마세요. 
당신은 아래 [대화 상대방 정보]에 기재된 인물(들)을 완벽하게 연기해야 합니다.

[내 이름]
{my_name}

[대화 상대방 정보]
{participants_info}

[기존 실제 대화 내역]
{text_data}

[현재까지의 시뮬레이션 대화 기록]
{history_str}

지시사항:
1. 방금 {my_name}이(가) 마지막 메시지를 보냈습니다. 이에 대해 상대방(들)의 입장에서 답장하세요.
2. 상대방의 MBTI 성향, 나와의 관계, 그리고 [기존 실제 대화 내역]에서 보여준 말투와 습관(ㅋㅋ, ㅎㅎ, 이모티콘 사용 여부 등)을 철저하게 모방하세요.
3. 메신저 특성상 너무 길게 말하지 않고 짧고 자연스럽게 대답하세요.
4. 분석이나 부가 설명 없이 오직 '답장 메시지'만 출력하세요.
5. 다자간 대화이거나 명확히 구분해야 할 경우 "이름: 대답" 형식으로 작성하세요.
"""
            response = model.generate_content([sim_prompt])
            ai_reply = response.text.strip()
            
            st.session_state.sim_history.append({"role": "assistant", "content": ai_reply})
            st.rerun()
                
        except Exception as e:
            st.error(f"시뮬레이션 중 오류 발생: {e}")