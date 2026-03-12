import streamlit as st
import pandas as pd
from PIL import Image, ExifTags  # 💡 폰의 사진 메모(EXIF)를 읽기 위해 추가
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

# 💡 [새로 추가] 사진의 숨겨진 메모(EXIF)를 읽어 똑바로 세워주는 함수
def correct_orientation(image):
    try:
        # EXIF 정보 가져오기
        exif = image._getexif()
        
        # '회전 정보'에 해당하는 태그 ID 찾기
        orientation_tag = next(k for k, v in ExifTags.TAGS.items() if v == 'Orientation')
        
        if exif and orientation_tag in exif:
            orientation = exif[orientation_tag]
            
            # 회전 정보에 따라 사진을 돌려줍니다.
            if orientation == 3: # 180도 회전
                image = image.rotate(180, expand=True)
            elif orientation == 6: # 시계 방향 90도 회전 -> 원상복구
                image = image.rotate(270, expand=True)
            elif orientation == 8: # 반시계 방향 90도 회전 -> 원상복구
                image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError, StopIteration):
        # 정보가 없거나 꼬이면 그냥 둡니다.
        pass
    return image

# --- 1. 화면 설정 및 초기화 ---
st.set_page_config(page_title="무제한 책 스캐너 (OCR)", layout="centered")

if 'user_db' not in st.session_state:
    st.session_state['user_db'] = load_db()
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

st.title("📚 무제한 책 스캐너 (OCR 버전)")
st.info("💡 폰을 세워서 찍어도 앱이 알아서 똑바로 세워 인식합니다!")

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
    raw_image = Image.open(picture)
    
    # 💡 폰의 세로 촬영 메모를 읽어 사진을 똑바로 세우기!
    image = correct_orientation(raw_image)
    
    # 똑바로 선 사진을 화면에 보여주기
    st.image(image, caption="현재 촬영된 사진", use_container_width=True)
    
    try:
        with st.spinner('🔍 돋보기로 글자를 찾는 중...'):
            # OCR 인식률을 높이기 위한 이미지 흑백 변환
            gray_image = image.convert('L')
            
            extracted_text = pytesseract.image_to_string(gray_image, lang='kor+eng')
            clean_text = extracted_text.strip()
            
            year_match = re.search(r'(19|20)\d{2}', clean_text)
            guessed_year = year_match.group() if year_match else ""
            
            lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            guessed_title = lines[0] if lines else ""

        with st.form(key="confirm_form"):
            st.write("### 📝 추출된 전체 글자 (참고용)")
            st.caption("우측 상단의 복사 버튼(📋)을 누르면 한 번에 복사됩니다.")
            
            # 원클릭 복사 기능
            if clean_text:
                st.code(clean_text, language="text")
            else:
                st.info("글자를 인식하지 못했습니다. 밝은 곳에서 다시 찍어주세요.")
            
            st.write("### 🎯 데이터 입력 (직접 수정)")
            title_input = st.text_input("책 제목", value=guessed_title)
            year_input = st.text_input("출판 년도", value=guessed_year)
            
            if st.form_submit_button("내 목록에 저장", use_container_width=True):
                st.session_state['user_db'][user_id].append({
                    "책 제목": title_input,
                    "출판 년도": year_input
                })
                save_db(st.session_state['user_db']) 
                
                st.session_state['uploader_key'] += 1
                st.success("✅ 저장 완료!")
                st.rerun()
                
    except Exception as e:
        st.error("앗! 글자를 읽어오는 데 실패했습니다.")
        st.write(e)

# ... (목록 표시 및 삭제 기능은 동일) ...
# (코드가 너무 길어져 중간 생략: 기존 코드와 동일합니다)
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
