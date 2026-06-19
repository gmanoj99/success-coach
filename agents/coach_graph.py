from langgraph.graph import (
    StateGraph,
    START,
    END
)

from agents.state import CoachState

from services.student_service import (
    build_student_context
)

from services.llm_service import (
    generate_response,
    classify_route
)

from prompts.system_prompt import (
    build_system_prompt,
    build_generic_system_prompt
)

from prompts.rag_prompt import (
    RAG_SYSTEM_PROMPT
)

from services.rag_service import (
    retrieve_context,
    format_kb_context
)


# -------------------
# ROUTER
# -------------------

def router_node(state):

    decision = classify_route(
        state["question"]
    )

    return {
        "route": decision.route
    }


# -------------------
# STUDENT CONTEXT
# -------------------

def load_student_context_node(state):

    context = build_student_context(
        state["student_id"]
    )

    return {
        "student_context": context
    }


# -------------------
# KB RETRIEVAL
# -------------------

def retrieve_knowledge_node(state):

    chunks = retrieve_context(
        state["question"],
        top_k=10
    )

    print("\n" + "=" * 50)
    print("QUESTION:")
    print(state["question"])

    # for chunk in chunks:
    #     print("\nDISTANCE:", chunk["distance"])
    #     print(chunk["text"][:300])

    # print("=" * 50)

    kb_context = format_kb_context(
        chunks
    )

    return {
        "kb_context": kb_context,
        "retrieved_chunks": chunks
    }


# -------------------
# ANSWER NODES
# -------------------

def answer_generic(state):

    prompt = build_generic_system_prompt()

    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )

    return {
        "answer": answer
    }


def answer_student(state):

    prompt = build_system_prompt(
        state["student_context"]
    )

    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )

    return {
        "answer": answer
    }


def answer_kb(state):
    print("\nKB CONTEXT")
    print(state["kb_context"][:1000])
    prompt = RAG_SYSTEM_PROMPT.format(
        kb_context=state["kb_context"]
    )

    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )
    print("\nFINAL ANSWER:")
    print(answer)
    return {
        "answer": answer
    }


def answer_student_and_kb(state):

    prompt = f"""
You are a Student Success Coach.

Student Information:
{state['student_context']}

Course Knowledge:
{state['kb_context']}

Instructions:

- Use student data when relevant.
- Use the knowledge base as the primary source for course-related information.
- If the knowledge base contains the answer, use it.
- If the knowledge base partially answers the question, provide the best answer possible.
- If the information is not available in the knowledge base, clearly state that.
- Do not invent policies, deadlines, platform features, or course rules.
- Give practical and concise guidance.
"""

    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )

    return {
        "answer": answer
    }


# -------------------
# ROUTING HELPERS
# -------------------

def route_after_router(state):
    return state["route"]


def after_load_student(state):
    return state["route"]


def after_retrieve_kb(state):
    return state["route"]


# -------------------
# GRAPH
# -------------------

graph = StateGraph(
    CoachState
)

graph.add_node(
    "router",
    router_node
)

graph.add_node(
    "load_student",
    load_student_context_node
)

graph.add_node(
    "retrieve_kb",
    retrieve_knowledge_node
)

graph.add_node(
    "answer_generic",
    answer_generic
)

graph.add_node(
    "answer_student",
    answer_student
)

graph.add_node(
    "answer_kb",
    answer_kb
)

graph.add_node(
    "answer_student_and_kb",
    answer_student_and_kb
)

# -------------------
# START
# -------------------

graph.add_edge(
    START,
    "router"
)

# -------------------
# ROUTER DECISIONS
# -------------------

graph.add_conditional_edges(
    "router",
    route_after_router,
    {
        "generic": "answer_generic",
        "student_data": "load_student",
        "knowledge_base": "retrieve_kb",
        "student_and_kb": "load_student"
    }
)

# -------------------
# STUDENT FLOW
# -------------------

graph.add_conditional_edges(
    "load_student",
    after_load_student,
    {
        "student_data": "answer_student",
        "student_and_kb": "retrieve_kb"
    }
)

# -------------------
# KB FLOW
# -------------------

graph.add_conditional_edges(
    "retrieve_kb",
    after_retrieve_kb,
    {
        "knowledge_base": "answer_kb",
        "student_and_kb": "answer_student_and_kb"
    }
)

# -------------------
# END NODES
# -------------------

graph.add_edge(
    "answer_generic",
    END
)

graph.add_edge(
    "answer_student",
    END
)

graph.add_edge(
    "answer_kb",
    END
)

graph.add_edge(
    "answer_student_and_kb",
    END
)

# -------------------
# COMPILE
# -------------------

coach_app = graph.compile()


# -------------------
# RUNNER
# -------------------

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

    return (
        result["answer"],
        result["route"]
    )