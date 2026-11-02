"""
ContextIQ — Pydantic Request / Response Models
================================================
Pydantic models serve three purposes in FastAPI:
  1. Automatic JSON validation — invalid input returns 422 before any handler runs.
  2. Auto-generated OpenAPI schema — visible at /docs.
  3. Type safety — editors and linters catch mismatches at write-time.

QueryRequest validation rules:
  - min_length=3  : prevents 1-2 char queries that would waste an LLM call.
  - max_length=500: prevents context-window overflow attacks.
  - field_validator: strips leading/trailing whitespace and rejects blank strings.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The IT support question from the employee.",
        examples=["My VPN keeps disconnecting after the password reset."],
    )

    @field_validator("question")
    @classmethod
    def strip_and_reject_blank(cls, v: str) -> str:
        """Strip whitespace and reject strings that are blank after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Question cannot be empty or whitespace only.")
        return stripped


class QueryResponse(BaseModel):
    answer: str = Field(description="The agent's response to the question.")
    sources: List[str] = Field(
        default=[],
        description=(
            "Ticket IDs of the historical IT tickets that informed this answer. "
            "Empty list when the query was rejected as out-of-scope."
        ),
    )
