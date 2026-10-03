from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from . import audit
from .gemini import Provider, get_provider
from .registry import REGISTRY
from .schemas import (
    Decision,
    DocumentFacts,
    ImageFindings,
    Plan,
    PlannedSkill,
    RunTrace,
    SkillResult,
)
from .storage import StoredSource, save_all, text_of

DECISION_SKILL = "make_decision"
NOTE_ID = "operator_note"

USE_ALIASES = {
    "operator_text": NOTE_ID,
    "scenario": NOTE_ID,
    "operator_note": NOTE_ID,
    "text": NOTE_ID,
    "all_skill_outputs": "",
    "all": "",
}


def _resolve_use(use: str, by_id: dict[str, StoredSource]) -> StoredSource | None:
    use = use.strip()
    if use in USE_ALIASES:
        alias = USE_ALIASES[use]
        return by_id.get(alias) if alias else None
    return by_id.get(use)

PLANNER_SYSTEM = """\
You are the planner of Space Bunny, a multi-modal decision agent.

You receive one operational scenario plus a set of fragmented sources: free text, images
and documents. Your only job is to decide which skills to run and in what order. You do not
analyse anything yourself and you do not answer the scenario.

Available skills:
{catalogue}

Rules:
1. Run `analyze_document` once per source that matters, and once for the operator's own
   note. The operator note is a source with id `operator_note`. Every entry must name the
   source ids it consumes in `uses`, and those ids must be sources you were given.
2. Run `analyze_image` once per image that could change the outcome. Omit an image only if
   it is clearly decorative, and never omit it because a text source already mentions it.
3. Always finish with `{decision_skill}`. It must be the last entry.
4. Prefer few skills. Do not run a skill whose output would not change the decision.
5. `why` must be one short sentence tied to this specific input, not a generic description.
"""


class SpaceBunny:
    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or get_provider()

    def plan(self, scenario: str, sources: list[StoredSource]) -> Plan:
        manifest = "\n".join(f"- {s.id} ({s.kind})" for s in sources)
        contents: list = [
            f"OPERATOR SCENARIO:\n{scenario}\n",
            f"SOURCE MANIFEST:\n{manifest}\n",
        ]
        for src in sources:
            contents.append(f"SOURCE id={src.id} kind={src.kind}")
            if src.kind == "image":
                contents.append(self.provider.image_part(src.id, src.bytes, src.mime_type))
            elif src.kind == "pdf":
                contents.append(self.provider.pdf_part(src.id, src.bytes, src.mime_type))
                extracted = text_of(src)
                if extracted:
                    contents.append(f"EXTRACTED TEXT of {src.id}:\n{extracted[:6000]}")
            else:
                contents.append(text_of(src)[:8000])
        system = PLANNER_SYSTEM.format(
            catalogue=REGISTRY.catalogue(), decision_skill=DECISION_SKILL
        )
        plan = self.provider.generate(system, contents, Plan)
        return _repair_plan(plan)

    def run(self, scenario: str, uploads: list[tuple[str, str, bytes]]) -> RunTrace:
        started = time.perf_counter()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        note = StoredSource(
            id=NOTE_ID,
            kind="text",
            mime_type="text/plain",
            bytes=scenario.encode("utf-8"),
        )
        sources = [note] + (save_all(run_id, uploads) if uploads else [])

        plan = self.plan(scenario, sources)
        by_id = {s.id: s for s in sources}
        consumed: set[str] = set()

        results: list[SkillResult] = []
        for step in plan.skills:
            if step.skill == DECISION_SKILL:
                continue
            skill = REGISTRY.get(step.skill)
            targets: list[StoredSource] = []
            for use in step.uses:
                resolved = _resolve_use(use, by_id)
                if resolved and resolved.id not in consumed:
                    targets.append(resolved)
            if not targets:
                targets = [
                    s
                    for s in sources
                    if s.kind in skill.consumes and s.id not in consumed
                ][:1]
            for src in targets:
                consumed.add(src.id)
                results.append(self._execute(skill.name, step.why, src))

        decision = self._decide(scenario, sources, results)

        trace = RunTrace(
            run_id=run_id,
            mode=self.provider.name,  # type: ignore[arg-type]
            model=self.provider.model,
            scenario=scenario,
            sources=[s.id for s in sources],
            plan=plan,
            skill_results=results,
            decision=decision,
            total_latency_ms=int((time.perf_counter() - started) * 1000),
            created_at=audit.now(),
        )
        audit.log_run(_audit_row(trace))
        return trace

    def _execute(self, skill_name: str, why: str, src: StoredSource) -> SkillResult:
        skill = REGISTRY.get(skill_name)
        contents: list = [f"WHY THIS SKILL WAS SELECTED: {why}", f"SOURCE id={src.id}"]
        if src.kind == "image":
            contents.append(self.provider.image_part(src.id, src.bytes, src.mime_type))
        else:
            body = text_of(src)
            if src.kind == "pdf":
                contents.append(self.provider.pdf_part(src.id, src.bytes, src.mime_type))
            contents.append(body[:8000] or f"(no extractable text in {src.id})")

        started = time.perf_counter()
        self.provider.last_usage = (0, 0)
        if skill_name == "analyze_document":
            output: DocumentFacts | ImageFindings = self.provider.generate(
                skill.instructions, contents, DocumentFacts
            )
        else:
            output = self.provider.generate(skill.instructions, contents, ImageFindings)
        latency = int((time.perf_counter() - started) * 1000)
        tokens_in, tokens_out = self.provider.last_usage
        return SkillResult(
            skill=skill_name,
            source_id=src.id,
            output=output,
            latency_ms=latency,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    def _decide(
        self, scenario: str, sources: list[StoredSource], results: list[SkillResult]
    ) -> Decision:
        dossier = [
            {
                "source": r.source_id,
                "skill": r.skill,
                "output": r.output.model_dump(mode="json"),
            }
            for r in results
        ]
        image_lines = []
        for r in results:
            if r.skill != "analyze_image":
                continue
            sev = getattr(r.output, "severity", "unknown")
            sev = getattr(sev, "value", sev)
            image_lines.append(f"IMAGE_EVIDENCE source={r.source_id} severity={sev}")
        contents: list = [
            f"OPERATOR SCENARIO:\n{scenario}",
            f"SOURCE MANIFEST: {[s.id for s in sources]}",
            "\n".join(image_lines) if image_lines else "IMAGE_EVIDENCE: none",
            "SKILL OUTPUT DOSSIER:\n" + json.dumps(dossier, ensure_ascii=False, indent=2),
        ]
        for src in sources:
            if src.kind == "text" and src.id != NOTE_ID:
                contents.append(f"RAW TEXT of {src.id}:\n{text_of(src)[:4000]}")
        started = time.perf_counter()
        decision = self.provider.generate(
            REGISTRY.prompt_for(DECISION_SKILL), contents, Decision
        )
        decision.total_latency_ms = int((time.perf_counter() - started) * 1000)
        return decision


def _repair_plan(plan: Plan) -> Plan:
    valid = [s for s in plan.skills if s.skill in REGISTRY.skills]
    if not any(s.skill == DECISION_SKILL for s in valid):
        valid.append(
            PlannedSkill(
                skill=DECISION_SKILL,
                why="A single actionable call is required from the reconciled sources.",
                uses=["all_skill_outputs"],
            )
        )
    ordered = [s for s in valid if s.skill != DECISION_SKILL][:4]
    ordered += [s for s in valid if s.skill == DECISION_SKILL][:1]
    return plan.model_copy(update={"skills": ordered})


def _audit_row(trace: RunTrace) -> dict:
    d = trace.decision
    return {
        "run_id": trace.run_id,
        "created_at": trace.created_at,
        "mode": trace.mode,
        "model": trace.model,
        "scenario": trace.scenario,
        "sources": ",".join(trace.sources),
        "skills_run": ",".join([trace.plan.skills[0].skill] + [r.skill for r in trace.skill_results]),
        "decision": d.decision,
        "action": d.action,
        "confidence": d.confidence,
        "reasoning_chain": json.dumps([s.model_dump() for s in d.reasoning_chain]),
        "evidence": json.dumps([e.model_dump() for e in d.evidence]),
        "total_latency_ms": trace.total_latency_ms,
    }


def load_dataset(folder: Path) -> list[tuple[str, str, bytes]]:
    import mimetypes

    items = []
    for p in sorted(folder.iterdir()):
        if p.is_file():
            mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            items.append((p.name, mime, p.read_bytes()))
    return items


def load_text_only(folder: Path) -> str:
    parts = [p.read_text(errors="replace") for p in sorted(folder.iterdir()) if p.is_file()]
    return "\n\n".join(parts)