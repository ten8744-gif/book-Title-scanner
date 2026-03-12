import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import json
import hashlib
import os

# --- 데이터베이스 파일 설정 (데이터 영구 저장용) ---
DB_FILE = "user_data.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 1. 설정 및 상태 관리 ---
st.set_page_config(page_title="스마트 책 스캐너 V2", layout="centered")

if 'user_db' not in st.session_state:
    st.session_state['user_db'] = load_db()
if 'user_key' not in st.session_state:
    st.session_state['user_key'] = ""

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
st.title("📚 개인 맞춤 책장 스캐너 (V2)")

if not st.session_state['user_key']:
    st.info("시작하려면 아래 버튼을 눌러 API 키를 설정해주세요.")
    if st.button("🔑 API 키 입력하기", use_container_width=True):
        open_api_settings()
    st.stop()
else:
    if st.sidebar.button("⚙️ API 키 변경"):
        open_api_settings()

user_id = hashlib.sha256(st.session_state['user_key'].encode()).hexdigest()
if user_id not in st.session_state['user_db']:
    st.session_state['user_db'][user_id] = []

# --- 4. 사진 촬영 및 분석 (안드로이드 호환 방식으로 변경) ---
picture = st.file_uploader("📸 버튼을 눌러 카메라로 찍거나 앨범에서 선택하세요", type=['png', 'jpg', 'jpeg'])

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
                save_db(st.session_state['user_db']) 
                st.success(f"✅ 저장 완료!")
                
    except Exception as e:
        st.error(f"오류 발생: {e}\nAPI 키를 다시 확인해주세요.")

# --- 5. 목록 표시 및 삭제 기능 ---
st.divider()
st.subheader("📝 나의 저장 목록")

user_list = st.session_state['user_db'].get(user_id, [])

if user_list:
    df = pd.DataFrame(user_list)
    
    df.index = df.index + 1
    df.reset_index(inplace=True)
    df.rename(columns={'index': '연번'}, inplace=True)
    df['삭제 선택'] = False
    
    edited_df = st.data_editor(
        df,
        column_config={
            "연번": st.column_config.NumberColumn(disabled=True),
            "책 제목": st.column_config.TextColumn(disabled=True),
            "출판 년도": st.column_config.TextColumn(disabled=True),
            "삭제 선택": st.column_config.CheckboxColumn("삭제 선택", default=False)
        },
        hide_index=True,
        use_container_width=True,
        key="data_editor"
    )

    if st.button("🗑️ 선택 항목 삭제", type="primary", use_container_width=True):
        rows_to_keep = edited_df[edited_df['삭제 선택'] == False]
        new_list = rows_to_keep[['책 제목', '출판 년도']].to_dict('records')
        
        st.session_state['user_db'][user_id] = new_list
        save_db(st.session_state['user_db']) 
        st.rerun()

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        pd.DataFrame(user_list).to_excel(writer, index=False)
    st.download_button("📥 전체 목록 엑셀 다운로드", data=excel_buffer.getvalue(), file_name="my_books.xlsx", use_container_width=True)
else:
    st.info("아직 저장된 책이 없습니다.")
