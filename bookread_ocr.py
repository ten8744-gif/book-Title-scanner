import streamlit as st
import pandas as pd
from PIL import Image
import io
import json
import os
import re
import pytesseract

# --- 데이터베이스 파일 설정 ---
DB_FILE = "ocr_user_data.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 1. 화면 설정 및 초기화 ---
st.set_page_config(page_title="무제한 책 스캐너 (OCR)", layout="centered")

if 'user_db' not in st.session_state:
    st.session_state['user_db'] = load_db()
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

st.title("📚 무제한 책 스캐너 (OCR 버전)")
st.info("💡 구글 API 없이 작동하여 횟수 제한이 없습니다. (단, 제목은 직접 다듬어주셔야 합니다.)")

# 💡 API 키 대신 '닉네임'으로 개인 목록 분리!
user_id = st.sidebar.text_input("👤 사용자 닉네임 (목록 분리용)", value="", placeholder="예: 홍길동")

if not user_id:
    st.warning("👈 왼쪽 사이드바에 닉네임을 입력해야 시작할 수 있습니다.")
    st.stop()

if user_id not in st.session_state['user_db']:
    st.session_state['user_db'][user_id] = []

# --- 2. 사진 촬영 및 텍스트 추출 ---
picture = st.file_uploader(
    "📸 버튼을 눌러 표지를 찍으세요", 
    type=['png', 'jpg', 'jpeg'],
    key=f"file_uploader_{st.session_state['uploader_key']}"
)

if picture:
    st.image(picture, caption="현재 촬영된 사진", use_container_width=True)
    
    try:
        with st.spinner('🔍 돋보기로 글자를 찾는 중... (3~5초 소요)'):
            image = Image.open(picture)
            # OCR 엔진 가동 (한국어+영어)
            extracted_text = pytesseract.image_to_string(image, lang='kor+eng')
            clean_text = extracted_text.strip()
            
            # 야매(?) AI: 정규식으로 4자리 숫자(년도) 찾기
            year_match = re.search(r'(19|20)\d{2}', clean_text)
            guessed_year = year_match.group() if year_match else ""
            
            # 제목은 보통 맨 첫 줄에 있을 확률이 높음
            lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            guessed_title = lines[0] if lines else ""

        with st.form(key="confirm_form"):
            st.write("### 📝 추출된 전체 글자 (참고용)")
            st.text_area("복사해서 아래 제목 칸에 붙여넣으세요", value=clean_text, height=120, disabled=True)
            
            st.write("### 🎯 데이터 입력 (직접 수정)")
            title_input = st.text_input("책 제목", value=guessed_title)
            year_input = st.text_input("출판 년도", value=guessed_year)
            
            if st.form_submit_button("내 목록에 저장", use_container_width=True):
                st.session_state['user_db'][user_id].append({
                    "책 제목": title_input,
                    "출판 년도": year_input
                })
                save_db(st.session_state['user_db']) 
                
                # 초기화
                st.session_state['uploader_key'] += 1
                st.success("✅ 저장 완료!")
                st.rerun()
                
    except Exception as e:
        st.error("앗! 글자를 읽어오는 데 실패했습니다. 서버 설치가 덜 되었을 수 있습니다.")
        st.write(e)

# --- 3. 목록 표시 및 삭제 기능 ---
st.divider()
st.subheader(f"📝 {user_id}님의 저장 목록")

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
    st.download_button("📥 내 목록 엑셀 다운로드", data=excel_buffer.getvalue(), file_name=f"{user_id}_books.xlsx", use_container_width=True)
else:
    st.info("아직 저장된 책이 없습니다.")
