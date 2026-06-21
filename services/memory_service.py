import streamlit as st
from openai import OpenAI
from mem0 import MemoryClient
from datetime import datetime
import time

client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

memory_client = MemoryClient(
    api_key=st.secrets["MEM0_API_KEY"]
)


def get_session_count(student_id):
    """
    Count total sessions - IMPROVED with fallback searches.
    """
    try:
        print(f"\n{'='*70}")
        print(f"🔢 COUNTING SESSIONS FOR {student_id}")
        print(f"{'='*70}")
        
        # Try multiple search queries to ensure we catch all metadata
        search_queries = [
            "SESSION_METADATA session number",
            "session metadata",
            "SESSION",
            "student session"
        ]
        
        all_memories = []
        
        for query in search_queries:
            print(f"\n   🔍 Trying search query: '{query}'")
            
            try:
                results = memory_client.search(
                    query=query,
                    filters={"user_id": str(student_id)},
                    limit=100
                )
                
                if isinstance(results, dict):
                    memories = results.get("results", [])
                else:
                    memories = results if results else []
                
                print(f"      Found {len(memories)} results")
                all_memories.extend(memories)
            except Exception as e:
                print(f"      Error with this query: {e}")
                continue
        
        # Deduplicate by memory text
        unique_memories = {}
        for memory in all_memories:
            memory_text = memory.get("memory") or memory.get("text") or str(memory)
            if memory_text not in unique_memories:
                unique_memories[memory_text] = memory
        
        all_memories = list(unique_memories.values())
        print(f"\n   📥 Total unique items after dedup: {len(all_memories)}")
        
        # Track unique sessions by extracting session numbers
        session_numbers = []
        
        for i, memory in enumerate(all_memories):
            memory_text = memory.get("memory") or memory.get("text") or str(memory)
            
            # Print first few for debugging
            if i < 5:
                print(f"\n   Item {i+1}:")
                print(f"      Text: {memory_text[:100]}...")
            
            # Look for SESSION_METADATA marker
            if "SESSION_METADATA" in memory_text or "session" in memory_text.lower():
                # Extract session number
                import re
                
                # Try different patterns
                patterns = [r'Session (\d+)', r'SESSION (\d+)', r'session (\d+)', r'Session #(\d+)']
                
                for pattern in patterns:
                    match = re.search(pattern, memory_text)
                    if match:
                        session_num = int(match.group(1))
                        if session_num not in session_numbers:
                            session_numbers.append(session_num)
                            print(f"      ✓ Found Session {session_num}")
                        break
        
        print(f"\n   📊 EXTRACTION SUMMARY:")
        print(f"      All session numbers found: {sorted(session_numbers)}")
        
        # Get the maximum session number
        if session_numbers:
            max_session = max(session_numbers)
            print(f"      Maximum session: {max_session}")
            print(f"\n   ✅ RETURNING: {max_session} (will display Session #{max_session + 1})")
            print(f"{'='*70}\n")
            return max_session
        else:
            print(f"      No session numbers found")
            print(f"\n   ℹ️  RETURNING: 0 (next session will be Session #1)")
            print(f"{'='*70}\n")
            return 0
    
    except Exception as e:
        print(f"❌ Session count retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n")
        return 0


def generate_session_summary(messages):
    """
    Generate short summary of session using correct model.
    """
    conversation = "\n".join(
        [
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini-2026-03-17",  # ✅ FIXED: Valid model name
            messages=[
                {
                    "role": "system",
                    "content": "You are a summarizer. Create a very short summary (2-3 sentences)."
                },
                {
                    "role": "user",
                    "content": f"""Summarize this student coaching session into a very short summary.

Include:
- Problems discussed
- Advice given
- Student commitments

Conversation:

{conversation}"""
                }
            ]
        )
        summary = response.choices[0].message.content
        print(f"✓ Summary generated: {len(summary)} chars")
        return summary
    except Exception as e:
        print(f"❌ Summary generation failed: {e}")
        return "Session completed - student received coaching on their questions."


def extract_student_facts(messages):
    """
    Extract long-term facts with EXPLICIT formatting using correct model.
    """
    conversation = "\n".join(
        [
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini-2026-03-17",  # ✅ FIXED: Valid model name
            messages=[
                {
                    "role": "system",
                    "content": """You are a fact extractor. Extract concrete, specific facts about the student.
                
ALWAYS format facts like this:
- Studied: [topic], [topic]
- Weak in: [area]
- Strong in: [area]
- Prefers: [learning style]
- Struggles with: [issue]

Be specific and concrete."""
                },
                {
                    "role": "user",
                    "content": f"""Extract facts about this student from their conversation.

REQUIRED FORMAT:
- Studied: [list topics they mentioned]
- Weak in: [areas they struggle with]
- Strong in: [areas they're good at]
- Prefers: [how they like to learn]
- Triggers: [stress/motivation triggers]

Examples of good answers:
- Studied: Binary Trees, Recursion, Linked Lists
- Weak in: Dynamic Programming
- Strong in: Basic arrays
- Prefers: Learning through examples
- Triggers: Time pressure makes them anxious

Conversation:
{conversation}"""
                }
            ]
        )

        facts_text = response.choices[0].message.content
        print(f"✓ Facts extracted: {len(facts_text)} chars")
        print(f"\n📝 EXTRACTED FACTS:\n{facts_text}")
        
        return facts_text
    except Exception as e:
        print(f"❌ Fact extraction failed: {e}")
        return "- Studied: Topics from session\n- Weak in: Areas to focus on\n- Prefers: Further clarification needed"


def save_session_memory(student_id, messages):
    """
    Save session with UNIQUE identifiers to prevent duplicates.
    Uses timestamp to ensure each session is distinct.
    """
    current_session_number = get_session_count(student_id) + 1
    timestamp = datetime.now().isoformat()
    unique_session_id = f"SESSION_{current_session_number}_{int(time.time())}"

    print(f"\n{'='*70}")
    print(f"💾 SAVING SESSION {current_session_number} FOR STUDENT {student_id}")
    print(f"   Unique ID: {unique_session_id}")
    print(f"   Timestamp: {timestamp}")
    print(f"{'='*70}")

    summary = generate_session_summary(messages)
    facts = extract_student_facts(messages)

    try:
        # 1. Session metadata with unique identifier
        session_metadata = f"""SESSION_METADATA: Session {current_session_number}
Unique Session ID: {unique_session_id}
Date: {timestamp}
Session Number: {current_session_number}
Summary: {summary}"""
        
        print(f"\n📤 Saving session metadata...")
        memory_client.add(
            session_metadata,
            user_id=str(student_id)
        )
        print(f"✓ Session metadata saved (ID: {unique_session_id})")
        
        # Small delay to ensure Mem0 processes
        time.sleep(0.5)

        # 2. Session summary
        if summary.strip():
            session_summary_msg = f"""SESSION_SUMMARY: Session {current_session_number}
Session ID: {unique_session_id}
What was discussed and decided:
{summary}"""
            
            print(f"📤 Saving session summary...")
            memory_client.add(
                session_summary_msg,
                user_id=str(student_id)
            )
            print(f"✓ Session summary saved")
            
            time.sleep(0.3)

        # 3. CRITICAL: Factual memory - MUST be saved with session tag
        if facts.strip() and len(facts) > 10:
            factual_memory_msg = f"""STUDENT_FACTS_AND_PATTERNS:
Session {current_session_number} Update (ID: {unique_session_id}):
{facts}

(Last updated: {timestamp})"""
            
            print(f"\n💡 SAVING FACTUAL MEMORY:")
            print(f"   Length: {len(factual_memory_msg)} chars")
            print(f"   Content preview: {factual_memory_msg[:200]}")
            
            memory_client.add(
                factual_memory_msg,
                user_id=str(student_id)
            )
            print(f"✓ Factual memory saved to Mem0")
            
            time.sleep(0.3)
        else:
            print(f"⚠️  WARNING: Facts too short or empty: {len(facts)} chars")
            print(f"   Facts content: {facts}")

    except Exception as e:
        print(f"❌ Mem0 save failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    print(f"\n{'='*70}")
    print(f"✅ SESSION {current_session_number} SAVED COMPLETELY")
    print(f"   Sessions total: {current_session_number}")
    print(f"{'='*70}\n")

    return {
        "summary": summary,
        "facts": facts,
        "session_number": current_session_number,
        "unique_id": unique_session_id
    }