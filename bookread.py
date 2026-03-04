import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import json
import hashlib

# 1. AI 호출 결과 캐싱 (중복 호출 및 비용/할당량 방지)
@st.cache_data(show_spinner=False)
def ask_gemini_cached(image_bytes, api_key):
    # 내부에서 API 설정
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # 바이트 데이터를 이미지 객체로 변환
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail((1000, 1000))
    
    prompt = """
    책 표지 정보를 추출하여 JSON 형식으로만 답하세요:
    {"title": "메인 제목", "year": "4자리 출판년도"}
    문맥에 맞게 오타를 교정하고 제목이 여러 줄이면 하나로 합치세요.
    """
    
    response = model.generate_content([prompt, image])
    # JSON 텍스트만 추출
    result_text = response.text.strip().replace('```json', '').replace('```', '')
    return json.loads(result_text)

# --- 기본 상태 설정 ---
if 'book_list' not in st.session_state:
    st.session_state['book_list'] = []

# 🚨 여기에 새로 발급받은 API 키를 넣으세요!
MY_API_KEY = "AIzaSyAWC-FSWhDesqamS6dIMbxzxiVYX1-3piA"

st.set_page_config(page_title="스마트 책장 스캐너", layout="centered")
st.title("📱 스마트 책장 스캐너 (안전 버전)")
st.info("사진이 바뀔 때만 AI가 작동하므로 안심하고 사용하세요.")

# 2. 카메라 입력
picture = st.camera_input("📸 사진 찍기")

if picture:
    st.write("---")
    # 💡 .id 대신 .getvalue()를 사용하여 AttributeError를 완벽 차단합니다.
    pic_bytes = picture.getvalue()
    
    # 사진 고유 해시값 생성 (사진이 동일한지 판단하는 기준)
    current_hash = hashlib.md5(pic_bytes).hexdigest()
    
    try:
        # 캐싱된 함수 호출: 동일 사진이면 제미나이를 호출하지 않고 즉시 반환
        with st.spinner('AI가 분석 중입니다...'):
            result = ask_gemini_cached(pic_bytes, MY_API_KEY)
            
        # 사진이 '새로' 찍혔을 때만 입력창의 초기값을 업데이트
        if st.session_state.get('last_hash') != current_hash:
            st.session_state['temp_title'] = result.get("title", "")
            st.session_state['temp_year'] = result.get("year", "")
            st.session_state['last_hash'] = current_hash

        # 3. 데이터 확인 및 수정 폼
        with st.form(key="data_confirm_form"):
            title_input = st.text_input("책 제목 확인/수정", value=st.session_state.get('temp_title', ""))
            year_input = st.text_input("출판 년도 확인/수정", value=st.session_state.get('temp_year', ""))
            
            # 저장 버튼 클릭 시 리스트에 추가
            if st.form_submit_button("목록에 저장하기"):
                st.session_state['book_list'].append({
                    "책 제목": title_input,
                    "출판 년도": year_input
                })
                st.balloons() # 축하 풍선 효과
                st.success(f"✅ '{title_input}' 저장 완료!")
                
    except Exception as e:
        st.error(f"분석 중 오류 발생: {e}")

# --- 4. 저장된 목록 및 엑셀 다운로드 ---
st.divider()
st.subheader("📝 현재 저장된 목록")

if st.session_state['book_list']:
    df = pd.DataFrame(st.session_state['book_list'])
    st.dataframe(df, use_container_width=True)
    
    # 엑셀 변환 로직
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 엑셀 파일 다운로드",
        data=excel_buffer.getvalue(),
        file_name="book_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.write("아직 저장된 항목이 없습니다.")
