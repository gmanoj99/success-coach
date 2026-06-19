import streamlit as st
from dotenv import load_dotenv

from agents.coach_graph import run_coach

load_dotenv()

st.set_page_config(
    page_title="Student Success Coach",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Success Coach")

# ----------------------------------
# Student Selection
# ----------------------------------

student_options = {
    "Student 1": "STU001",
    "Student 2": "STU002",
    "Student 3": "STU003"
}

selected_student = st.sidebar.selectbox(
    "Select Student",
    list(student_options.keys())
)

student_id = student_options[selected_student]

# ----------------------------------
# Reset chat when student changes
# ----------------------------------

if (
    "current_student" not in st.session_state
    or st.session_state.current_student != student_id
):
    st.session_state.current_student = student_id
    st.session_state.messages = []

# ----------------------------------
# Initialize chat history
# ----------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------------------------
# Display previous messages
# ----------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ----------------------------------
# User Input
# ----------------------------------

user_input = st.chat_input(
    "Ask your question..."
)

if user_input:

    # Store user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate answer
    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            try:

                answer = run_coach(
                    question=user_input,
                    student_id=student_id,
                    chat_history=st.session_state.messages
                )

            except Exception as e:

                answer = f"Error: {str(e)}"

            st.markdown(answer)

    # Store assistant answer
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )