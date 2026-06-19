from langgraph.graph import StateGraph, START, END

from agents.state import CoachState

from services.student_service import (
    build_student_context
)

from services.llm_service import (
    generate_response
)

from prompts.system_prompt import (
    build_system_prompt,
    build_generic_system_prompt
)


def router_node(state):

    student_keywords = [
        "score",
        "marks",
        "attendance",
        "exam",
        "subject",
        "performance",
        "result",
        "cgpa"
    ]

    question = state["question"].lower()

    needs_student_data = any(
        keyword in question
        for keyword in student_keywords
    )

    return {
        "needs_student_data": needs_student_data
    }


def load_student_context_node(state):

    context = build_student_context(
        state["student_id"]
    )

    return {
        "student_context": context
    }


def answer_with_student_data(state):

    system_prompt = build_system_prompt(
        state["student_context"]
    )

    answer = generate_response(
        system_prompt=system_prompt,
        question=state["question"],
        chat_history=state["chat_history"]
    )

    return {
        "answer": answer
    }


def answer_without_student_data(state):

    system_prompt = build_generic_system_prompt()

    answer = generate_response(
        system_prompt=system_prompt,
        question=state["question"],
        chat_history=state["chat_history"]
    )

    return {
        "answer": answer
    }


def route_after_classifier(state):

    if state["needs_student_data"]:
        return "load_context"

    return "answer_generic"


graph = StateGraph(CoachState)

graph.add_node("router", router_node)

graph.add_node(
    "load_context",
    load_student_context_node
)

graph.add_node(
    "answer_with_data",
    answer_with_student_data
)

graph.add_node(
    "answer_generic",
    answer_without_student_data
)

graph.add_edge(
    START,
    "router"
)

graph.add_conditional_edges(
    "router",
    route_after_classifier,
    {
        "load_context": "load_context",
        "answer_generic": "answer_generic"
    }
)

graph.add_edge(
    "load_context",
    "answer_with_data"
)

graph.add_edge(
    "answer_with_data",
    END
)

graph.add_edge(
    "answer_generic",
    END
)

coach_app = graph.compile()


def run_coach(
    question,
    student_id,
    chat_history
):

    result = coach_app.invoke(
        {
            "question": question,
            "student_id": student_id,
            "chat_history": chat_history
        }
    )

    return result["answer"]