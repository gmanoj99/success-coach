from pydantic import BaseModel
from typing import Literal

class RouteDecision(BaseModel):
    route: Literal["generic", "student_data", "knowledge_base", "student_and_kb"]
    reason: str