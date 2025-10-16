import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime
import zipfile
import io

# Cấu hình trang
st.set_page_config(
    page_title="Hệ Thống Thi Trắc Nghiệm",
    page_icon="📚",
    layout="wide"
)

# Khởi tạo session state
def init_session_state():
    if 'quiz_data' not in st.session_state:
        st.session_state.quiz_data = {}
    if 'current_quiz' not in st.session_state:
        st.session_state.current_quiz = None
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'quiz_finished' not in st.session_state:
        st.session_state.quiz_finished = False
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'end_time' not in st.session_state:
        st.session_state.end_time = None
    if 'show_wrong_answers' not in st.session_state:
        st.session_state.show_wrong_answers = False

def load_excel_file(uploaded_file):
    """Đọc file Excel và trả về DataFrame"""
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        required_columns = ['STT', 'CÂU HỎI', 'ĐÁP ÁN 1', 'ĐÁP ÁN 2', 'ĐÁP ÁN 3', 'ĐÁP ÁN 4', 'ĐÁP ÁN ĐÚNG']
        
        # Kiểm tra các cột bắt buộc
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Thiếu các cột: {', '.join(missing_columns)}")
            return None
        
        # Làm sạch dữ liệu
        df = df.dropna(subset=['CÂU HỎI'])
        df['STT'] = df['STT'].astype(int)
        df['ĐÁP ÁN ĐÚNG'] = df['ĐÁP ÁN ĐÚNG'].astype(int)
        
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc file: {str(e)}")
        return None

def start_quiz():
    """Bắt đầu bài thi"""
    st.session_state.quiz_started = True
    st.session_state.quiz_finished = False
    st.session_state.current_question = 0
    st.session_state.user_answers = {}
    st.session_state.start_time = time.time()
    st.session_state.show_wrong_answers = False

def next_question():
    """Chuyển đến câu hỏi tiếp theo"""
    if st.session_state.current_question < len(st.session_state.current_quiz) - 1:
        st.session_state.current_question += 1

def previous_question():
    """Quay lại câu hỏi trước"""
    if st.session_state.current_question > 0:
        st.session_state.current_question -= 1

def finish_quiz():
    """Kết thúc bài thi"""
    st.session_state.quiz_finished = True
    st.session_state.quiz_started = False
    st.session_state.end_time = time.time()

def display_question():
    """Hiển thị câu hỏi hiện tại"""
    if not st.session_state.quiz_data or st.session_state.current_quiz is None:
        st.warning("Vui lòng chọn một mục thi")
        return
    
    quiz_name = st.session_state.current_quiz
    df = st.session_state.quiz_data[quiz_name]
    current_idx = st.session_state.current_question
    
    if current_idx >= len(df):
        st.error("Không tìm thấy câu hỏi")
        return
    
    question_data = df.iloc[current_idx]
    
    st.subheader(f"Câu {current_idx + 1}: {question_data['CÂU HỎI']}")
    
    # Hiển thị các đáp án
    options = [
        question_data['ĐÁP ÁN 1'],
        question_data['ĐÁP ÁN 2'], 
        question_data['ĐÁP ÁN 3'],
        question_data['ĐÁP ÁN 4']
    ]
    
    # Tạo key duy nhất cho câu hỏi hiện tại
    answer_key = f"{quiz_name}_q{current_idx}"
    
    # Kiểm tra nếu đã có câu trả lời trước đó
    current_answer = st.session_state.user_answers.get(answer_key, None)
    
    # Hiển thị radio buttons cho các đáp án
    user_choice = st.radio(
        "Chọn đáp án:",
        options=options,
        index=current_answer,
        key=f"radio_{current_idx}"
    )
    
    # Lưu câu trả lời của người dùng
    if user_choice:
        selected_index = options.index(user_choice)
        st.session_state.user_answers[answer_key] = selected_index
        
        # Kiểm tra đúng/sai và hiển thị màu
        correct_answer = question_data['ĐÁP ÁN ĐÚNG'] - 1  # Chuyển về index 0-based
        if selected_index == correct_answer:
            st.success("✅ Đáp án đúng!")
        else:
            st.error(f"❌ Đáp án sai! Đáp án đúng là: {options[correct_answer]}")

def calculate_results():
    """Tính toán kết quả"""
    if not st.session_state.quiz_data or st.session_state.current_quiz is None:
        return 0, 0, []
    
    quiz_name = st.session_state.current_quiz
    df = st.session_state.quiz_data[quiz_name]
    
    correct_count = 0
    wrong_questions = []
    
    for idx in range(len(df)):
        answer_key = f"{quiz_name}_q{idx}"
        user_answer = st.session_state.user_answers.get(answer_key)
        
        if user_answer is not None:
            correct_answer = df.iloc[idx]['ĐÁP ÁN ĐÚNG'] - 1
            if user_answer == correct_answer:
                correct_count += 1
            else:
                wrong_questions.append({
                    'question_number': idx + 1,
                    'question': df.iloc[idx]['CÂU HỎI'],
                    'user_answer': df.iloc[idx][f'ĐÁP ÁN {user_answer + 1}'],
                    'correct_answer': df.iloc[idx][f'ĐÁP ÁN {correct_answer + 1}']
                })
    
    total_questions = len(df)
    accuracy = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    return correct_count, total_questions, accuracy, wrong_questions

def display_results():
    """Hiển thị kết quả"""
    correct_count, total_questions, accuracy, wrong_questions = calculate_results()
    time_taken = st.session_state.end_time - st.session_state.start_time
    minutes = int(time_taken // 60)
    seconds = int(time_taken % 60)
    
    st.header("📊 Kết Quả Bài Thi")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Số câu đúng", f"{correct_count}/{total_questions}")
    
    with col2:
        st.metric("Tỷ lệ đúng", f"{accuracy:.1f}%")
    
    with col3:
        st.metric("Thời gian làm bài", f"{minutes:02d}:{seconds:02d}")
    
    # Hiển thị các câu trả lời sai
    if wrong_questions:
        st.subheader("📝 Các câu trả lời sai:")
        for wrong in wrong_questions:
            with st.expander(f"Câu {wrong['question_number']}: {wrong['question']}"):
                st.error(f"Đáp án của bạn: {wrong['user_answer']}")
                st.success(f"Đáp án đúng: {wrong['correct_answer']}")
    else:
        st.success("🎉 Chúc mừng! Bạn đã trả lời đúng tất cả các câu hỏi!")

def create_zip_file():
    """Tạo file zip chứa toàn bộ mã nguồn"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Thêm file app.py
        zip_file.writestr('app.py', open(__file__, 'r', encoding='utf-8').read())
        
        # Thêm requirements.txt
        requirements_content = """streamlit==1.28.0
pandas==2.0.3
openpyxl==3.1.2
"""
        zip_file.writestr('requirements.txt', requirements_content)
        
        # Thêm README.md
        readme_content = """# Ứng dụng Thi Trắc Nghiệm

## Mô tả
Ứng dụng thi trắc nghiệm được xây dựng bằng Streamlit, hỗ trợ 17 mục thi từ các file Excel.

## Cài đặt
1. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
