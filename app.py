import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import os

from services.student_service import (
    build_student_context
)

from prompts.system_prompt import (
    build_system_prompt
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

st.set_page_config(
    page_title="Student AI Assistant",
    page_icon="🎓",
    layout="wide"
)

# Demo student
student_id = "STU001"

student_context = build_student_context(student_id)

system_prompt = build_system_prompt(student_context)

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🎓 Student Success Coach")

st.caption(
    "Ask academic or personal growth questions."
)

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input( "Ask your question...")

if user_input:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(
        st.session_state.messages
    )

    with st.chat_message( "assistant"):

        with st.spinner("Thinking..."):

            response = (
                client.chat.completions.create(
                    model="gpt-5.4-mini",
                    messages=messages,
                    temperature=0.4
                )
            )

            answer = (response.choices[0].message.content)
            st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )