from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SourceKind(str, Enum):
    text = "text"
    image = "image"
    pdf = "pdf"
    document = "document"


class PlannedSkill(BaseModel):
    skill: str = Field(description="Skill id, must be one of the available skills.")
    why: str = Field(description="One sentence on why this skill is needed for this input.")
    uses: list[str] = Field(
        default_factory=list,
        description="Source ids this skill will consume, e.g. ['closure_note.txt'].",
    )


class Plan(BaseModel):
    situation: str = Field(description="One paragraph restating the operational situation.")
    skills: list[PlannedSkill] = Field(
        description="Ordered skills to execute. 2 to 5 entries.", min_length=2, max_length=5
    )


class DocumentFacts(BaseModel):
    summary: str = Field(description="What this document says, in 2 sentences.")
    entities: list[str] = Field(description="Locations, units, assets, dates, agencies.")
    facts: list[str] = Field(description="Verifiable statements, each self-contained.")
    risk_flags: list[str] = Field(description="Anything indicating risk, delay or blockage.")
    confidence: float = Field(ge=0.0, le=1.0)


class ImageFindings(BaseModel):
    description: str = Field(description="Literal description of what is visible.")
    objects: list[str] = Field(description="Detected objects of interest.")
    conditions: list[str] = Field(description="Damage, obstruction, weather, lighting conditions.")
    severity: Severity = Field(description="Worst condition visible in the image.")
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    source: str = Field(description="Filename or source id the evidence came from.")
    finding: str = Field(description="The specific finding being cited.")
    supports: Literal["decision", "against", "context"]


class ReasoningStep(BaseModel):
    step: int = Field(ge=1)
    skill: str = Field(description="Skill that produced this step.")
    claim: str = Field(description="What this step concluded.")
    because: str = Field(description="Why that conclusion follows from the inputs.")


class Alternative(BaseModel):
    option: str
    rejected_because: str


class Decision(BaseModel):
    decision: str = Field(description="The call, in one imperative sentence.")
    action: str = Field(description="Who does what, next.")
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_rationale: str = Field(description="Why the confidence is at that level.")
    reasoning_chain: list[ReasoningStep] = Field(min_length=2, max_length=6)
    evidence: list[EvidenceItem] = Field(min_length=1)
    risks: list[str] = Field(description="What could invalidate this decision.")
    alternatives_considered: list[Alternative]
    escalation: str = Field(description="Trigger that would require a human to override.")
    total_latency_ms: int = 0


class SkillResult(BaseModel):
    skill: str
    source_id: str
    output: DocumentFacts | ImageFindings
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0


class RunTrace(BaseModel):
    run_id: str
    mode: Literal["gemini", "vertex", "heuristic"]
    model: str
    scenario: str
    sources: list[str]
    plan: Plan
    skill_results: list[SkillResult]
    decision: Decision
    total_latency_ms: int
    created_at: str