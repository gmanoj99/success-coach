ROUTER_PROMPT = """
You decide if a student success coach needs THIS student's personal data
(attendance, scores, exams, program, cohort) to answer well.

Return needs_student_data=true for questions about:
- this student's performance, attendance, scores, exams
- study plans tied to their schedule or weak subjects
- personalized advice based on their record

Return needs_student_data=false for:
- general programming/CS/math concepts
- generic study tips, productivity, career advice
- questions not about this specific student's data

Question: {question}
"""