import streamlit as st
from openai import OpenAI
from mem0 import MemoryClient

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

memory_client = MemoryClient(
    api_key=st.secrets["MEM0_API_KEY"]
)




def generate_session_summary(
    messages
):

    conversation = "\n".join(
        [
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ]
    )

    response = client.responses.create(
        model="gpt-5.4-mini-2026-03-17",
        input=f"""
Summarize this student coaching session into a very short summary.

Include:
- Problems discussed
- Advice given
- Student commitments

Conversation:

{conversation}
"""
    )
    return response.output_text


def extract_student_facts(
    messages
):

    conversation = "\n".join(
        [
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ]
    )

    response = client.responses.create(
        model="gpt-5.4-mini-2026-03-17",
        input=f"""
Extract 0-3 long-term facts about the student.

Examples:
- Preparing for placements
- Weak in DSA
- Prefers video learning
- Studies at night

if no long term fact is there return empty
Conversation:

{conversation}
"""
    )

    return response.output_text


# In memory_service.py
def save_session_memory(student_id, messages):
    summary = generate_session_summary(messages)
    facts = extract_student_facts(messages)

    try:
        memory_client.add(
            f"Session Summary: {summary}",
            user_id=str(student_id)
        )
        memory_client.add(
            f"Student Facts: {facts}",
            user_id=str(student_id)
        )
    except Exception as e:
        print(f"Mem0 save failed: {e}")
        raise   # so Streamlit shows the real error

    return {"summary": summary, "facts": facts}