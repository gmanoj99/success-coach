import streamlit as st
from dotenv import load_dotenv

from agents.coach_graph import run_coach
from services.memory_service import (
    save_session_memory,
    get_session_count
)

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

# Display session count (with refresh on each page load)
session_count = get_session_count(student_id)
print(f"\n📊 UI DISPLAY: Session count for {student_id} = {session_count}")
print(f"   Displaying: Session #{session_count + 1}")
st.sidebar.info(f"📊 Session #{session_count + 1}")

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

                answer, route = run_coach(
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

st.divider()

if st.button("End Session"):
    if not st.session_state.messages:
        st.warning("No conversation to save.")
    else:
        result = save_session_memory(
            student_id,
            st.session_state.messages
        )
        st.success(
            f"✅ Session #{result['session_number']} saved successfully!"
        )

        st.subheader("📝 Session Summary")
        st.write(result["summary"])

        st.subheader("💡 Key Facts")
        facts = result["facts"].split("\n")
        for fact in facts:
            fact = fact.strip()
            if fact:
                st.write(f"• {fact}")
        
        # Clear messages for next session and rerun to refresh session count
        st.session_state.messages = []
        print(f"\n{'='*70}")
        print(f"✅ SESSION SAVED - CLEARING FOR NEXT SESSION")
        print(f"   Session Number: {result['session_number']}")
        print(f"   Messages cleared: ready for next session")
        print(f"{'='*70}\n")
        st.rerun()