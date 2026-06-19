from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class CoachState(TypedDict):
    question: str
    student_id: str
    chat_history: list[dict]
    needs_student_data: bool
    student_context: str
    answer: str