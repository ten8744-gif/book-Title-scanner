import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import json

# 1. 임시 저장소 만들기
if 'book_list' not in st.session_state:
    st.session_state['book_list'] = []

# 2. 제미나이 API 키 자동 설정 (코드에 직접 입력)
# 주의: 따옴표(" ") 안에 네 API 키를 붙여넣어 줘!
MY_API_KEY = "AIzaSyDPAnMLtsdYt4p4KSB5abOALQj7U3n22zk"
genai.configure(api_key=MY_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 모바일 앱 화면 구성
st.title("📱 내 책장 스캐너 (모바일)")
st.write("스마트폰 카메라로 책 표지를 촬영해 주세요.")

# 4. 모바일 전용 카메라 켜기
picture = st.camera_input("📸 사진 찍기")

if picture:
    st.write("---")
    
    # 사진 압축 (속도 향상 및 데이터 절약)
    image = Image.open(picture)
    image.thumbnail((1000, 1000))

    with st.spinner('제미나이가 문맥을 분석 중입니다... 🧠'):
        try:
            prompt = """
            당신은 책 표지에서 핵심 정보를 추출하는 전문가입니다. 
            이미지를 분석하여 다음 규칙에 따라 정보를 추출해 주세요.

            1. 책의 '가장 핵심이 되는 메인 제목'만 추출하세요. (저자, 출판사, 홍보 문구 무시)
            2. 제목이 두 줄이거나 영문인 경우 문맥에 맞게 자연스럽게 하나로 이으세요.
            3. 출판 년도(예: 1998, 2014)가 있다면 4자리 숫자만 추출하세요. 없으면 비워두세요.
            4. 시각적인 오타(예: MSDS를 MS Dog로 인식)가 있다면 문맥에 맞게 교정하세요.
            
            결과는 반드시 아래 JSON 형식으로만 대답해 주세요. 다른 말은 절대 금지합니다.
            {"title": "추출한 책 제목", "year": "추출한 년도"}
            """
            
            response = model.generate_content([prompt, image])
            
            # 텍스트 정제 및 JSON 변환
            result_text = response.text.strip().replace('```json', '').replace('```', '')
            result_json = json.loads(result_text)
            
            extracted_title = result_json.get("title", "")
            extracted_year = result_json.get("year", "")
            
            st.success("✨ 분석 완료!")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            extracted_title = ""
            extracted_year = ""
    
    # 5. 사용자 확인 및 저장 폼
    with st.form(key="mobile_form"):
        title_input = st.text_input("책 제목 확인", value=extracted_title)
        year_input = st.text_input("출판 년도 확인", value=extracted_year)
        
        submitted = st.form_submit_button("목록에 저장하기")
        
        if submitted:
            st.session_state['book_list'].append({
                "책 제목": title_input,
                "출판 년도": year_input
            })
            st.info("✅ 목록에 저장되었습니다! (아래 표를 확인하세요)")

st.divider() 

# 6. 저장된 목록 조회 및 엑셀 다운로드
st.subheader("📝 저장된 책 목록")

if len(st.session_state['book_list']) > 0:
    df = pd.DataFrame(st.session_state['book_list'])
    
    # 모바일 화면에 맞게 표 꽉 차게 그리기
    st.dataframe(df, use_container_width=True)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='책 목록')
    
    st.download_button(
        label="📥 엑셀로 다운로드",
        data=excel_buffer.getvalue(),
        file_name="my_books_mobile.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("아직 저장된 책이 없습니다.")