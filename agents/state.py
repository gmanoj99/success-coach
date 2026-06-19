from typing import TypedDict


class CoachState(TypedDict):

    question: str
    student_id: str
    chat_history: list
    route: str
    student_context: str
    kb_context: str
    retrieved_chunks: list
    answer: str