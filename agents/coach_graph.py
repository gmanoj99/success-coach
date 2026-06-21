from langgraph.graph import (
    StateGraph,
    START,
    END
)
from services.load_mem_service import (
    load_memory_context,
    load_full_student_memory
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
    RAG_SYSTEM_PROMPT,
    build_rag_system_prompt
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


# -------------------------
# LOAD FULL STUDENT MEMORY
# -------------------------
def load_memory_node(state):
    """
    Load comprehensive memory including factual and session data.
    Also determines session count for context-awareness.
    """
    memory_data = load_full_student_memory(
        state["student_id"],
        state["question"]
    )
    print(f"\n✅ MEMORY LOADED INTO STATE:")
    print(f"   Session Count: {memory_data['session_count']}")
    print(f"   Factual Memory Length: {len(memory_data['factual_memory'])}")
    print(f"   Session History Length: {len(memory_data['session_history'])}")

    return {
        "factual_memory": memory_data["factual_memory"],
        "session_history": memory_data["session_history"],
        "session_count": memory_data["session_count"],
        "memory_context": memory_data["full_context"]
    }


# -------------------------
# LOAD STUDENT CONTEXT
# -------------------------
def load_student_context_node(state):
    """
    Load current student data (scores, attendance, etc.).
    """
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
    """
    Answer generic questions - NOW WITH FULL MEMORY INTEGRATION.
    Personalizes generic advice using student's history.
    """
    print(f"\n🎯 ANSWERING GENERIC QUESTION")
    print(f"   Memory Available: {len(state.get('factual_memory', ''))} chars")
    print(f"   Session Count: {state.get('session_count', 1)}")
    
    # Show what memory is being passed
    memory_preview = state.get('factual_memory', '')[:100]
    if memory_preview:
        print(f"   Memory Preview: {memory_preview}...")
    else:
        print(f"   ⚠️  NO FACTUAL MEMORY - will give generic answer")
    
    prompt = build_generic_system_prompt(
        session_count=state.get("session_count", 1),
        factual_memory=state.get("factual_memory", ""),
        session_history=state.get("session_history", "")
    )

    print(f"\n📋 PROMPT PREVIEW (first 800 chars):")
    print(prompt[:800])
    print(f"\n   Total prompt length: {len(prompt)} chars")
    
    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )

    return {
        "answer": answer
    }


def answer_student(state):
    """
    Answer student-specific questions with full memory context.
    """
    print(f"\n🎯 ANSWERING STUDENT-SPECIFIC QUESTION")
    print(f"   Memory Available: {len(state.get('factual_memory', ''))} chars")
    print(f"   Session Count: {state.get('session_count', 1)}")
    
    # Show what memory is being passed
    memory_preview = state.get('factual_memory', '')[:100]
    if memory_preview:
        print(f"   Memory Preview: {memory_preview}...")
    else:
        print(f"   ⚠️  NO FACTUAL MEMORY AVAILABLE")
    
    prompt = build_system_prompt(
        student_context=state["student_context"],
        session_count=state.get("session_count", 1),
        factual_memory=state.get("factual_memory", ""),
        session_history=state.get("session_history", "")
    )
    
    print(f"\n📋 PROMPT PREVIEW (first 800 chars):")
    print(prompt[:800])
    print(f"\n   Total prompt length: {len(prompt)} chars")
    
    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )

    return {
        "answer": answer
    }


def answer_kb(state):
    """
    Answer KB questions with student memory context.
    Personalizes knowledge base answers using student profile.
    """
    print(f"\n🎯 ANSWERING KNOWLEDGE BASE QUESTION")
    print(f"   KB Context: {len(state.get('kb_context', ''))} chars")
    print(f"   Memory Available: {len(state.get('factual_memory', ''))} chars")
    print(f"   Session Count: {state.get('session_count', 1)}")
    
    print("\n📚 KB CONTEXT")
    print(state["kb_context"][:1000])
    
    prompt = build_rag_system_prompt(
        kb_context=state["kb_context"],
        factual_memory=state.get("factual_memory", ""),
        session_history=state.get("session_history", ""),
        session_count=state.get("session_count", 1)
    )

    answer = generate_response(
        prompt,
        state["question"],
        state["chat_history"]
    )
    
    print("\n📝 FINAL ANSWER:")
    print(answer[:500])
    
    return {
        "answer": answer
    }


def answer_student_and_kb(state):
    """
    Answer combining student data, memory, and KB context.
    Maximum personalization with full context integration.
    """
    print(f"\n🎯 ANSWERING COMBINED (STUDENT + KB) QUESTION")
    print(f"   Student Context: {len(state.get('student_context', ''))} chars")
    print(f"   Memory Available: {len(state.get('factual_memory', ''))} chars")
    print(f"   KB Context: {len(state.get('kb_context', ''))} chars")
    print(f"   Session Count: {state.get('session_count', 1)}")
    
    session_count = state.get('session_count', 1)
    factual_memory = state.get('factual_memory', '')
    session_history = state.get('session_history', '')
    
    # Session-specific tone
    if session_count == 1:
        session_note = "FIRST SESSION: Build rapport and learn their background."
    elif session_count >= 5:
        session_note = f"SESSION {session_count}: Reference previous discussions. Be direct."
    else:
        session_note = f"SESSION {session_count}: Build on established context."
    
    # Memory acknowledgment for combined responses
    memory_instruction = ""
    if factual_memory or session_history:
        memory_instruction = """

⚡ YOU MUST ACKNOWLEDGE PREVIOUS DISCUSSIONS:
   - Start with: "Based on what we've covered..." or "Since you've worked on..."
   - Reference their weak/strong areas
   - Connect KB knowledge to their profile
"""

    prompt = f"""
You are a Student Success Coach - SESSION {session_count}

{session_note}

╔════════════════════════════════════════════════════════════════╗
║                        CURRENT CONTEXT                         ║
╚════════════════════════════════════════════════════════════════╝

STUDENT INFORMATION:
{state.get('student_context', '')}

STUDENT PROFILE & HISTORY:
{factual_memory}

PREVIOUS CONVERSATIONS:
{session_history}

COURSE KNOWLEDGE:
{state.get('kb_context', '')}

{memory_instruction}

INSTRUCTIONS:

1. **Integrate all three sources**
   - Use student data when relevant
   - Reference their history for continuity
   - Apply KB knowledge to their situation
   - Show you understand their complete context

2. **Personalize KB answers**
   - Explain based on their weak/strong areas
   - Reference previous topics covered
   - Adapt depth to their session level

3. **Build on relationships**
   - Show you remember them
   - Reference specific topics discussed before
   - Connect new knowledge to their journey
   - Avoid repeating previous advice

4. **Be educational**
   - Explain the "why" not just "what"
   - Make learning connections
   - Be encouraging and supportive
   - Give actionable advice

5. **Handle edge cases**
   - If not in KB → say so clearly
   - If info conflicts → ask for clarification
   - If off-topic → redirect appropriately
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
# GRAPH SETUP
# -------------------

graph = StateGraph(
    CoachState
)

# Add all nodes
graph.add_node("router", router_node)
graph.add_node("load_memory", load_memory_node)
graph.add_node("load_student", load_student_context_node)
graph.add_node("retrieve_kb", retrieve_knowledge_node)
graph.add_node("answer_generic", answer_generic)
graph.add_node("answer_student", answer_student)
graph.add_node("answer_kb", answer_kb)
graph.add_node("answer_student_and_kb", answer_student_and_kb)

# Define flow
graph.add_edge(START, "load_memory")
graph.add_edge("load_memory", "router")

# Router decision
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

# Student flow
graph.add_conditional_edges(
    "load_student",
    after_load_student,
    {
        "student_data": "answer_student",
        "student_and_kb": "retrieve_kb"
    }
)

# KB flow
graph.add_conditional_edges(
    "retrieve_kb",
    after_retrieve_kb,
    {
        "knowledge_base": "answer_kb",
        "student_and_kb": "answer_student_and_kb"
    }
)

# End edges
graph.add_edge("answer_generic", END)
graph.add_edge("answer_student", END)
graph.add_edge("answer_kb", END)
graph.add_edge("answer_student_and_kb", END)

# Compile
coach_app = graph.compile()


# -------------------
# RUNNER
# -------------------

def run_coach(question, student_id, chat_history):
    """
    Run the coach graph with memory awareness.
    """
    result = coach_app.invoke(
        {
            "question": question,
            "student_id": student_id,
            "chat_history": chat_history,
            "session_count": 1  # Will be updated by load_memory_node
        }
    )

    return (
        result["answer"],
        result["route"]
    )