import os
from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st
load_dotenv()

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

def generate_response(
    system_prompt: str,
    question: str,
    chat_history: list
):

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages.extend(chat_history)

    messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    response = client.chat.completions.create(
        model="gpt-5.4-mini-2026-03-17",
        messages=messages,
        temperature=0.4
    )

    return response.choices[0].message.content