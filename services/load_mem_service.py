import streamlit as st
from mem0 import MemoryClient
from datetime import datetime
import re

memory_client = MemoryClient(
    api_key=st.secrets["MEM0_API_KEY"]
)

def load_full_student_memory(student_id, query):
    """
    Load comprehensive memory with full diagnostics.
    """
    print(f"\n{'='*70}")
    print(f"🔍 LOADING FULL MEMORY FOR STUDENT: {student_id}")
    print(f"   Query: {query}")
    print(f"{'='*70}")
    
    factual_memories = get_factual_memory(student_id)
    session_summaries = get_session_summaries(student_id)
    session_count = get_session_count(student_id)

    print(f"\n📊 RAW RETRIEVAL RESULTS:")
    print(f"   ✓ Session Count: {session_count}")
    print(f"   ✓ Factual Memories Items: {len(factual_memories)}")
    print(f"   ✓ Session Summaries Items: {len(session_summaries)}")

    factual_context = format_factual_memory(factual_memories)
    session_context = format_session_history(session_summaries, session_count)

    print(f"\n📝 FORMATTED MEMORY:")
    print(f"   ✅ Factual Context Length: {len(factual_context)} chars")
    if factual_context:
        print(f"   Preview: {factual_context[:150]}...")
    else:
        print(f"   ⚠️  EMPTY - NO FACTUAL MEMORY!")
    
    print(f"\n   ✅ Session Context Length: {len(session_context)} chars")
    if session_context:
        print(f"   Preview: {session_context[:150]}...")
    else:
        print(f"   ⚠️  EMPTY - NO SESSION HISTORY!")

    full_context = f"{factual_context}\n\n{session_context}".strip()

    # Verify memory is ready to be passed to LLM
    total_memory = len(factual_context) + len(session_context)
    print(f"\n{'='*70}")
    print(f"✅ MEMORY LOADED SUCCESSFULLY")
    print(f"   Total memory length: {total_memory} chars")
    print(f"   Session number for LLM: {session_count}")
    if total_memory == 0:
        print(f"   ⚠️  WARNING: NO MEMORY - This is session 1 (new student)")
    else:
        print(f"   ✅ Memory ready to pass to LLM prompts")
    print(f"{'='*70}\n")

    return {
        "factual_memory": factual_context,
        "session_history": session_context,
        "session_count": session_count,
        "full_context": full_context
    }

def get_student_memories(student_id, query):
    """
    Retrieve relevant memories for a student.
    """
    try:
        results = memory_client.search(
            query=query,
            filters={
                "user_id": str(student_id)
            }
        )
        return results
    except Exception as e:
        print(f"❌ Memory retrieval failed: {e}")
        return []


def get_factual_memory(student_id):
    """
    Retrieve factual memory (topics studied, weak areas, patterns).
    """
    try:
        print(f"\n🔎 SEARCHING FOR FACTUAL MEMORY...")
        
        search_queries = [
            "studied topics weak strong learning",
            "facts patterns",
            "DSA programming",
            "student"
        ]
        
        all_factual = []
        
        for query in search_queries:
            print(f"   Trying query: '{query}'")
            results = memory_client.search(
                query=query,
                filters={"user_id": str(student_id)},
                limit=50
            )
            
            if isinstance(results, dict):
                memories = results.get("results", [])
            else:
                memories = results if results else []
            
            print(f"   Got {len(memories)} results")
            
            for memory in memories:
                memory_text = memory.get("memory", "") or memory.get("text", "") or str(memory)
                
                if any(marker in memory_text for marker in [
                    "STUDENT_FACTS",
                    "Studied:",
                    "Weak in:",
                    "Strong in:",
                    "Prefers:",
                    "Topics",
                    "Updated in session"
                ]):
                    print(f"   ✓ Found factual memory: {memory_text[:100]}")
                    all_factual.append(memory)

        print(f"\n📊 TOTAL FACTUAL MEMORIES FOUND: {len(all_factual)}")
        return all_factual

    except Exception as e:
        print(f"❌ Factual memory retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return []
    

def get_session_summaries(student_id):
    """
    Retrieve session summaries and history.
    """
    try:
        results = memory_client.search(
            query="session summary what was discussed decided",
            filters={
                "user_id": str(student_id)
            }
        )
        
        if isinstance(results, dict):
            memories = results.get("results", [])
        else:
            memories = results

        session_summaries = []
        for memory in memories:
            memory_text = memory.get("memory") or memory.get("text") or str(memory)
            if "SESSION_MEMORY" in memory_text or "SESSION_METADATA" in memory_text:
                session_summaries.append(memory)

        return session_summaries

    except Exception as e:
        print(f"❌ Session summary retrieval failed: {e}")
        return []


def get_session_count(student_id):
    """
    Get total session count by searching for session metadata.
    """
    try:
        results = memory_client.search(
            query="session metadata history",
            filters={
                "user_id": str(student_id)
            }
        )
        
        if isinstance(results, dict):
            memories = results.get("results", [])
        else:
            memories = results

        session_count = 0
        for memory in memories:
            memory_text = memory.get("memory") or memory.get("text") or str(memory)
            if "SESSION_METADATA" in memory_text:
                session_count += 1

        return max(session_count, 1)  # At least 1

    except Exception as e:
        print(f"❌ Session count retrieval failed: {e}")
        return 1


def extract_structured_facts(memory_text):
    """
    Extract structured facts from memory text.
    Parses topics, weak areas, strong areas, patterns.
    """
    facts = {
        "topics": [],
        "weak_areas": [],
        "strong_areas": [],
        "patterns": [],
        "raw": memory_text
    }
    
    # Parse topics
    topics_match = re.search(r'(?:Topics?|Studied)[\s:]+([^\n]*)', memory_text, re.IGNORECASE)
    if topics_match:
        facts["topics"] = [t.strip() for t in topics_match.group(1).split(",")]
    
    # Parse weak areas
    weak_match = re.search(r'(?:Weak|Struggling|Difficulty)[\s:]+([^\n]*)', memory_text, re.IGNORECASE)
    if weak_match:
        facts["weak_areas"] = [w.strip() for w in weak_match.group(1).split(",")]
    
    # Parse strong areas
    strong_match = re.search(r'(?:Strong|Good at|Excels)[\s:]+([^\n]*)', memory_text, re.IGNORECASE)
    if strong_match:
        facts["strong_areas"] = [s.strip() for s in strong_match.group(1).split(",")]
    
    # Parse patterns
    pattern_match = re.search(r'(?:Pattern|Prefer|Style)[\s:]+([^\n]*)', memory_text, re.IGNORECASE)
    if pattern_match:
        facts["patterns"] = [p.strip() for p in pattern_match.group(1).split(",")]
    
    return facts


def format_factual_memory(memories):
    """
    Format factual memory with CLEAR STRUCTURE for LLM comprehension.
    """
    if not memories:
        return ""

    if isinstance(memories, dict):
        memories = memories.get("results", [])

    all_topics = set()
    all_weak = set()
    all_strong = set()
    all_patterns = set()
    raw_facts = []

    for memory in memories:
        if isinstance(memory, dict):
            memory_text = (
                memory.get("memory")
                or memory.get("text")
                or str(memory)
            )
            # Clean up tags
            memory_text = memory_text.replace("FACTUAL_MEMORY", "").replace("STUDENT_FACTS_AND_PATTERNS", "").strip()
            
            if memory_text:
                facts = extract_structured_facts(memory_text)
                
                all_topics.update(f for f in facts["topics"] if f)
                all_weak.update(f for f in facts["weak_areas"] if f)
                all_strong.update(f for f in facts["strong_areas"] if f)
                all_patterns.update(f for f in facts["patterns"] if f)
                raw_facts.append(memory_text)

    # Build structured output
    formatted = ["=== STUDENT PROFILE & LEARNING HISTORY ===\n"]

    if all_topics:
        formatted.append(f"📚 TOPICS STUDIED:\n   • {chr(10).join('   • ' + t for t in sorted(all_topics))}\n")

    if all_weak:
        formatted.append(f"⚠️  WEAK AREAS (Need Extra Focus):\n   • {chr(10).join('   • ' + w for w in sorted(all_weak))}\n")

    if all_strong:
        formatted.append(f"✓ STRONG AREAS:\n   • {chr(10).join('   • ' + s for s in sorted(all_strong))}\n")

    if all_patterns:
        formatted.append(f"🎯 LEARNING PATTERNS & PREFERENCES:\n   • {chr(10).join('   • ' + p for p in sorted(all_patterns))}\n")

    if raw_facts:
        formatted.append("📋 DETAILED NOTES:")
        formatted.extend(raw_facts)

    return "\n".join(formatted)


def format_session_history(memories, session_count=1):
    """
    Format session history with TEMPORAL MARKERS and clear structure.
    """
    if not memories:
        return ""

    if isinstance(memories, dict):
        memories = memories.get("results", [])

    formatted = [f"=== PREVIOUS CONVERSATIONS ({session_count} sessions total) ===\n"]

    session_num = 1
    for memory in memories:
        if isinstance(memory, dict):
            memory_text = (
                memory.get("memory")
                or memory.get("text")
                or str(memory)
            )
            # Clean up tags
            memory_text = memory_text.replace("SESSION_MEMORY", "").replace("SESSION_METADATA", "").strip()
            
            if memory_text:
                formatted.append(f"\n📅 Session {session_num}:")
                formatted.append(f"   {memory_text}\n")
                session_num += 1

    if session_count == 0:
        formatted.append("   (This is the first session - no previous conversations yet)\n")

    return "\n".join(formatted)


def format_memory_context(memories):
    """
    Convert memories into prompt-ready text.
    """
    if not memories:
        return ""

    formatted = []

    if isinstance(memories, dict):
        memories = memories.get("results", [])

    for memory in memories:
        if isinstance(memory, dict):
            memory_text = (
                memory.get("memory")
                or memory.get("text")
                or str(memory)
            )
            formatted.append(memory_text)

    return "\n".join(formatted)


def load_memory_context(student_id, query):
    """
    Load and format all relevant memories for a question.
    """
    memories = get_student_memories(student_id, query)
    memory_context = format_memory_context(memories)

    print("\n📄 MEMORY CONTEXT")
    print(memory_context)

    return memory_context