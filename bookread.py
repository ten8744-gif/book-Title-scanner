import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import json
import hashlib

# --- 1. 설정 및 상태 관리 ---
st.set_page_config(page_title="스마트 책 스캐너", layout="centered")

if 'user_db' not in st.session_state:
    st.session_state['user_db'] = {} # {user_id: [book_list]}
if 'user_key' not in st.session_state:
    st.session_state['user_key'] = ""

# AI 호출 함수 (캐싱 적용)
@st.cache_data(show_spinner=False)
def ask_gemini_cached(image_bytes, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail((600, 600))
    
    prompt = """
    책 표지 정보를 추출하여 JSON 형식으로만 답하세요:
    {"title": "메인 제목", "year": "4자리 출판년도"}
    문맥에 맞게 오타를 교정하고 제목이 여러 줄이면 하나로 합치세요.
    """
    response = model.generate_content([prompt, image])
    result_text = response.text.strip().replace('```json', '').replace('```', '')
    return json.loads(result_text)

# --- 2. 팝업창(Dialog) 정의 ---
@st.dialog("🔑 API 설정 및 로그인")
def open_api_settings():
    st.write("서비스 이용을 위해 개인 Gemini API 키가 필요합니다.")
    st.markdown("""
    1. [Google AI Studio](https://aistudio.google.com/app/apikey)에 접속합니다.
    2. **'Create API key'**를 클릭하여 키를 발급받으세요. (무료)
    3. 아래 칸에 복사한 키를 붙여넣어 주세요.
    """)
    key_input = st.text_input("API Key 입력", value=st.session_state['user_key'], type="password")
    if st.button("설정 완료", use_container_width=True):
        st.session_state['user_key'] = key_input
        st.rerun()

# --- 3. 메인 화면 구성 ---
st.title("📚 개인 맞춤 책장 스캐너")

# 키가 없으면 팝업 열기 버튼 노출
if not st.session_state['user_key']:
    st.info("시작하려면 아래 버튼을 눌러 API 키를 설정해주세요.")
    if st.button("🔑 API 키 입력하기", use_container_width=True):
        open_api_settings()
    st.stop()
else:
    if st.sidebar.button("⚙️ API 키 변경"):
        open_api_settings()

# 사용자 ID 생성 (키 해시값)
user_id = hashlib.sha256(st.session_state['user_key'].encode()).hexdigest()
if user_id not in st.session_state['user_db']:
    st.session_state['user_db'][user_id] = []

# --- 4. 사진 촬영 및 분석 ---
picture = st.camera_input("📸 책 표지를 촬영하세요")

if picture:
    pic_bytes = picture.getvalue()
    current_hash = hashlib.md5(pic_bytes).hexdigest()
    
    try:
        with st.spinner('AI 분석 중...'):
            result = ask_gemini_cached(pic_bytes, st.session_state['user_key'])
            
        if st.session_state.get('last_hash') != current_hash:
            st.session_state['temp_title'] = result.get("title", "")
            st.session_state['temp_year'] = result.get("year", "")
            st.session_state['last_hash'] = current_hash

        with st.form(key="confirm_form"):
            title_input = st.text_input("제목 확인", value=st.session_state.get('temp_title', ""))
            year_input = st.text_input("년도 확인", value=st.session_state.get('temp_year', ""))
            
            if st.form_submit_button("내 목록에 저장", use_container_width=True):
                st.session_state['user_db'][user_id].append({
                    "책 제목": title_input,
                    "출판 년도": year_input
                })
                st.success(f"✅ 저장 완료!")
                
    except Exception as e:
        st.error(f"오류 발생: {e}\nAPI 키를 다시 확인해주세요.")

# --- 5. 목록 표시 및 삭제 기능 ---
st.divider()
st.subheader("📝 나의 저장 목록")

user_list = st.session_state['user_db'][user_id]

if user_list:
    df = pd.DataFrame(user_list)
    
    # 삭제 기능을 위한 데이터프레임 편집기 (체크박스 포함)
    edited_df = st.data_editor(
        df,
        column_config={"num": st.column_config.CheckboxColumn(default=False)},
        disabled=["책 제목", "출판 년도"],
        use_container_width=True,
        key="editor"
    )

    # 삭제 버튼 로직
    # 스트림릿의 데이터 에디터는 삭제 기능을 내장하고 있어, 
    # 사용자가 행을 선택하고 'Delete' 키를 누르거나 편집기 메뉴를 사용하도록 가이드하거나,
    # 아래처럼 직접 삭제 버튼을 구현할 수 있습니다.
    
    if st.button("🗑️ 선택 항목 삭제", type="primary", use_container_width=True):
        # 편집된 데이터가 원본과 다를 경우 갱신 (스트림릿 에디터 자체 삭제 기능 활용)
        st.session_state['user_db'][user_id] = edited_df.to_dict('records')
        st.rerun()

    # 6. 엑셀 다운로드
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 전체 목록 엑셀 다운로드", data=excel_buffer.getvalue(), file_name="my_books.xlsx", use_container_width=True)
else:
    st.info("아직 저장된 책이 없습니다.")
