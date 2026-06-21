import datetime
import streamlit as st
from dotenv import load_dotenv

from agents.coach_graph import run_coach
from services.memory_service import (
    save_session_memory,
    get_session_count
)
from services.sheets_service import (
    get_signals_for_date,
    get_plan_for_date,
    get_unresolved_signals,
)
from services.signal_detector_service import (
    get_data_driven_signals,
)
from agents.plan_generator_agent import (
    generate_daily_plan,
    auto_book_calendar_events,
    build_plan_summary,
    rank_signals,
)
from models.signal import Signal
from datetime import date
from agents.session_analyzer import analyze_full_session
from services.sheets_service import append_signal
load_dotenv()

st.set_page_config(
    page_title="Student Success Coach",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Success Coach")

# ----------------------------------
# View Selection (Student / Coach)
# ----------------------------------

view_col1, view_col2 = st.columns(2)
with view_col1:
    if st.button("📚 Student View", use_container_width=True, key="student_view_btn"):
        st.session_state.view = "student"
with view_col2:
    if st.button("👨‍💼 Coach View", use_container_width=True, key="coach_view_btn"):
        st.session_state.view = "coach"

# Initialize view state
if "view" not in st.session_state:
    st.session_state.view = "student"

st.divider()

# ----------------------------------
# STUDENT VIEW
# ----------------------------------

if st.session_state.view == "student":
    
    # Student Selection
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

                    answer, route, session_signal = run_coach(
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
        
        # Display signal if detected
        if session_signal:
            st.warning(
                f"🚨 **Signal Detected**: {session_signal.description}\n\n"
                f"**Severity**: {session_signal.severity_color()} {session_signal.severity.value}\n\n"
                f"**Urgency**: {session_signal.urgency_badge()}\n\n"
                f"**Recommended Action**: {session_signal.recommended_action}"
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
            
            st.subheader("🚨 Session Analysis - Detecting Signals...")
            
            # Analyze the entire session for signals
            signals = analyze_full_session(student_id, st.session_state.messages)
            
            # Save all signals to Google Sheets
            # Save all signals to Google Sheets — deduplicated by type+student+date
            spreadsheet_id = st.secrets.get("GOOGLE_SPREADSHEET_ID")
            if signals and spreadsheet_id:
                print(f"\n🔔 DEBUG: Found {len(signals)} signals to save")
                
                # Fetch already saved signals for today to deduplicate
                from services.sheets_service import get_signals_for_date
                from datetime import datetime as dt
                today_str = dt.now().strftime('%Y-%m-%d')
                existing_signals = get_signals_for_date(spreadsheet_id, today_str)
                existing_keys = {
                    (s.get('student_id'), s.get('type'))
                    for s in existing_signals
                }
                
                for signal in signals:
                    # Skip if same student + signal type already saved today
                    dedup_key = (signal.student_id, signal.signal_type.value)
                    if dedup_key in existing_keys:
                        print(f"   ⏭️  Skipping duplicate: {dedup_key}")
                        continue
                    
                    try:
                        signal_dict = signal.to_dict()
                        result = append_signal(spreadsheet_id, signal_dict)
                        existing_keys.add(dedup_key)  # prevent duplicates within same batch
                        print(f"   ✅ Saved signal: {signal.signal_type.value}")
                        st.warning(
                            f"🚨 **{signal.signal_type.value.upper()}** - {signal.description}\n\n"
                            f"Severity: {signal.severity.value} | "
                            f"Urgency: {signal.urgency.value}\n\n"
                            f"Action: {signal.recommended_action}"
                        )
                    except Exception as e:
                        print(f"   ERROR: {e}")
                        st.error(f"Error saving signal: {e}")
            elif not signals:
                st.success("✅ Session completed. No concerning signals detected.")
            else:
                if not spreadsheet_id:
                    st.warning("⚠️ GOOGLE_SPREADSHEET_ID not configured - signals not saved")
            # Clear messages for next session and rerun to refresh session count
            st.session_state.messages = []
            print(f"\n{'='*70}")
            print(f"✅ SESSION SAVED - CLEARING FOR NEXT SESSION")
            print(f"   Session Number: {result['session_number']}")
            print(f"   Messages cleared: ready for next session")
            print(f"{'='*70}\n")
            st.rerun()


# ----------------------------------
# COACH VIEW
# ----------------------------------

elif st.session_state.view == "coach":
    
    st.subheader("👨‍💼 Coach Dashboard")
    
    # Try to get spreadsheet ID
    spreadsheet_id = st.secrets.get("GOOGLE_SPREADSHEET_ID")
    
    # Create two main sections
    alert_col, plan_col = st.columns([1, 2])
    
    # ----------------------------------
    # ALERTS SECTION
    # ----------------------------------
    with alert_col:
        st.write("### 🚨 Alerts")
        
        if "selected_signals" not in st.session_state:
            st.session_state.selected_signals = set()
        
        if st.button("🔄 Refresh Alerts", key="refresh_alerts_btn"):
            st.session_state.selected_signals = set()
            st.rerun()
        
        spreadsheet_id = st.secrets.get("GOOGLE_SPREADSHEET_ID")
        if spreadsheet_id:
            try:
                signals = get_unresolved_signals(spreadsheet_id)
                
                st.metric("Total Alerts", len(signals))
                st.caption(f"Selected: {len(st.session_state.selected_signals)} for plan")
                
                if signals:
                    for idx, signal in enumerate(signals[:10]):
                        severity = signal.get('severity', 'medium').lower()
                        urgency = signal.get('urgency', 'can_wait').lower()
                        signal_id = signal.get('signal_id', f'sig_{idx}')
                        
                        with st.container(border=True):
                            col_info, col_act = st.columns([3, 1])
                            
                            with col_info:
                                st.write(f"**{signal.get('type', 'Unknown').upper()}**")
                                st.write(f"Student: {signal.get('student_id')}")
                                st.write(f"📝 {signal.get('description')}")
                                st.caption(f"Severity: {severity} | Urgency: {urgency}")
                                st.caption(f"Action: {signal.get('recommended_action')}")
                            
                            with col_act:
                                is_selected = signal_id in st.session_state.selected_signals
                                button_label = "✅ Acting" if is_selected else "🎬 Act"
                                
                                if st.button(button_label, key=f"act_{idx}", use_container_width=True):
                                    if is_selected:
                                        st.session_state.selected_signals.discard(signal_id)
                                    else:
                                        st.session_state.selected_signals.add(signal_id)
                                    st.rerun()
                else:
                    st.info("✅ No alerts")
            except Exception as e:
                st.error(f"Error loading alerts: {e}")
        
    # ----------------------------------
    # DAILY PLAN SECTION
    with plan_col:
        st.write("### 📅 Daily Plan")
        
        # Plan generation controls
        plan_controls_col1, plan_controls_col2 = st.columns([1, 1])
        with plan_controls_col1:
            if st.button("📋 Generate Plan", key="generate_plan_btn", use_container_width=True):
                st.session_state.generate_plan = True
        
        with plan_controls_col2:
            if st.button("🔄 Refresh Plan", key="refresh_plan_btn", use_container_width=True):
                st.session_state.refresh_plan = True
        
        # Generate plan if requested
        if st.session_state.get("generate_plan", False):
            with st.spinner("📊 Generating plan..."):
                try:
                    # Get selected or all unresolved signals
                    today_signals = []
                    if spreadsheet_id:
                        sheet_signals = get_unresolved_signals(spreadsheet_id)
                        selected_ids = st.session_state.get("selected_signals", set())
                        
                        for signal_data in sheet_signals:
                            signal_id = signal_data.get('signal_id')
                            # Include if selected, or if no selection made include all
                            if not selected_ids or signal_id in selected_ids:
                                try:
                                    today_signals.append(Signal.from_sheet_row(signal_data))
                                except Exception as e:
                                    print(f"Error converting signal: {e}")
                    
                    if not today_signals:
                        st.warning("No signals selected or found — select alerts to include in plan.")
                        st.session_state.generate_plan = False
                    else:
                        # Generate plan
                        plan = generate_daily_plan(
                            target_date=date.today(),
                            signals=today_signals,
                            max_slots_available=8
                        )
                        
                        # Auto-book calendar events
                        plan = auto_book_calendar_events(plan)
                        
                        # Save plan as markdown
                        import os
                        from datetime import datetime as dt
                        os.makedirs("data/plans", exist_ok=True)
                        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"data/plans/plan_{date.today()}_{timestamp}.md"
                        
                        with open(filename, 'w') as f:
                            f.write(f"# Daily Coaching Plan - {date.today().strftime('%B %d, %Y')}\n\n")
                            f.write(f"**Generated**: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                            f.write("## 📅 Scheduled Sessions\n\n")
                            for session in plan.scheduled_sessions:
                                f.write(f"### {session.student_name}\n")
                                f.write(f"- **Time**: {session.time_slot}\n")
                                f.write(f"- **Type**: {session.session_type.value.title()}\n")
                                f.write(f"- **Duration**: {session.duration_minutes} min\n")
                                f.write(f"- **Status**: {'✅ Booked' if session.is_booked else '⏳ Pending'}\n\n")
                            
                            if plan.deferred_students:
                                f.write("## ⏸️ Deferred\n\n")
                                for d in plan.deferred_students:
                                    f.write(f"- {d.student_name} ({d.severity_level})\n")
                        
                        # Mark only the signals that were actually scheduled as resolved.
                        # Deferred items stay in alerts so the coach can act on them later.
                        try:
                            from services.sheets_service import update_signal_resolved
                            scheduled_keys = {
                                (session.student_id, session.reason)
                                for session in plan.scheduled_sessions
                            }
                            for signal in today_signals:
                                signal_key = (signal.student_id, signal.description)
                                if signal_key in scheduled_keys:
                                    update_signal_resolved(spreadsheet_id, signal.signal_id)
                        except Exception as e:
                            print(f"Error marking signals resolved: {e}")
                        
                        st.session_state.daily_plan = plan
                        st.session_state.generate_plan = False
                        st.session_state.selected_signals = set()
                        
                        st.success(f"✅ Plan generated and saved to {filename}!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error generating plan: {e}")
                    print(f"Error: {e}")
        
        # Display plan
        if st.session_state.get("daily_plan"):
            plan = st.session_state.daily_plan
            
            # Plan summary
            st.info(build_plan_summary(plan))
            
            # Scheduled sessions
            st.write(f"**✅ Scheduled ({len(plan.scheduled_sessions)} sessions)**")
            for session in plan.scheduled_sessions:
                with st.container(border=True):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**{session.student_name}**")
                        st.caption(f"{session.session_type.value.title()} • {session.duration_minutes} min")
                        st.caption(f"📍 {session.time_slot if session.time_slot else 'Not scheduled'}")
                    with col2:
                        if session.is_booked:
                            st.caption("✅ Booked")
                        else:
                            st.caption("⏳ Pending")
                    
                    st.caption(f"📝 {session.reason}")
            
            # Deferred students
            if plan.deferred_students:
                st.write(f"**⏸️ Deferred ({len(plan.deferred_students)})**")
                for deferred in plan.deferred_students:
                    with st.container(border=True):
                        st.write(f"**{deferred.student_name}**")
                        st.caption(f"Severity: {deferred.severity_level}")
                        st.caption(f"Deferred to: {deferred.deferred_to}")
                        st.caption(f"Reason: {deferred.reason}")
        else:
            st.info(
                "**No plan yet**\n\n"
                "Click 'Generate Plan' to create today's coaching schedule based on alerts."
            )