import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import json

# 1. 임시 저장소 및 메모장 설정
if 'book_list' not in st.session_state:
    st.session_state['book_list'] = []

# 중복 호출 방지를 위한 메모장 변수들
if 'last_pic_hash' not in st.session_state:
    st.session_state['last_pic_hash'] = None  # 마지막 사진 데이터 기억
if 'temp_title' not in st.session_state:
    st.session_state['temp_title'] = ""
if 'temp_year' not in st.session_state:
    st.session_state['temp_year'] = ""

# API 키 설정
MY_API_KEY = "AIzaSyDPAnMLtsdYt4p4KSB5abOALQj7U3n22zk"
genai.configure(api_key=MY_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("📱 내 책장 스캐너 (최종 수정판)")
st.write("스마트폰 카메라로 책 표지를 촬영해 주세요.")

picture = st.camera_input("📸 사진 찍기")

if picture:
    st.write("---")
    
    # 💡 해결책: 사진 파일의 실제 데이터(바이트)를 가져와서 비교합니다.
    current_pic_bytes = picture.getvalue()
    
    # 사진이 새로 찍혔거나, 이전 사진과 데이터가 다를 때만 제미나이 호출!
    if st.session_state['last_pic_hash'] != current_pic_bytes:
        image = Image.open(picture)
        image.thumbnail((1000, 1000))

        with st.spinner('제미나이가 문맥을 분석 중입니다... 🧠'):
            try:
                prompt = """
                당신은 책 표지에서 핵심 정보를 추출하는 전문가입니다. 
                이미지를 분석하여 다음 규칙에 따라 정보를 추출해 주세요.
                1. 책의 '가장 핵심이 되는 메인 제목'만 추출하세요.
                2. 제목이 두 줄이거나 영문인 경우 자연스럽게 하나로 이으세요.
                3. 출판 년도가 있다면 4자리 숫자만 추출하세요. 없으면 비워두세요.
                4. 시각적인 오타가 있다면 문맥에 맞게 교정하세요.
                결과는 반드시 아래 JSON 형식으로만 대답해 주세요.
                {"title": "추출한 책 제목", "year": "추출한 년도"}
                """
                
                response = model.generate_content([prompt, image])
                result_text = response.text.strip().replace('```json', '').replace('```', '')
                result_json = json.loads(result_text)
                
                # 메모장에 결과 저장
                st.session_state['temp_title'] = result_json.get("title", "")
                st.session_state['temp_year'] = result_json.get("year", "")
                st.session_state['last_pic_hash'] = current_pic_bytes # 지금 사진 데이터 저장
                
                st.success("✨ 분석 완료!")

            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")

    # 5. 사용자 확인 및 저장 폼
    with st.form(key="mobile_form"):
        title_input = st.text_input("책 제목 확인", value=st.session_state['temp_title'])
        year_input = st.text_input("출판 년도 확인", value=st.session_state['temp_year'])
        
        submitted = st.form_submit_button("목록에 저장하기")
        
        if submitted:
            st.session_state['book_list'].append({
                "책 제목": title_input,
                "출판 년도": year_input
            })
            st.info("✅ 목록에 저장되었습니다!")

st.divider() 

# 6. 저장된 목록 조회 및 엑셀 다운로드
st.subheader("📝 저장된 책 목록")
if len(st.session_state['book_list']) > 0:
    df = pd.DataFrame(st.session_state['book_list'])
    st.dataframe(df, use_container_width=True)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 엑셀로 다운로드",
        data=excel_buffer.getvalue(),
        file_name="my_books.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
