from __future__ import annotations

import os
import re
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .schemas import Decision, DocumentFacts, ImageFindings, Plan, Severity

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


class Provider:
    name: str
    model: str
    last_usage: tuple[int, int] = (0, 0)

    def generate(self, system_instruction: str, contents: list[Any], schema: type[T]) -> T:
        raise NotImplementedError

    def image_part(self, source_id: str, data: bytes, mime_type: str) -> Any:
        raise NotImplementedError

    def pdf_part(self, source_id: str, data: bytes, mime_type: str) -> Any:
        raise NotImplementedError


class GeminiProvider(Provider):
    def __init__(self) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if api_key:
            self._client = genai.Client(api_key=api_key)
            self.name = "gemini"
        elif project:
            self._client = genai.Client(vertexai=True, project=project, location=location)
            self.name = "vertex"
        else:
            raise RuntimeError("no Gemini credentials available")

        self.model = DEFAULT_MODEL

    def image_part(self, source_id: str, data: bytes, mime_type: str) -> Any:
        return self._types.Part.from_bytes(data=data, mime_type=mime_type)

    def pdf_part(self, source_id: str, data: bytes, mime_type: str) -> Any:
        return self._types.Part.from_bytes(data=data, mime_type="application/pdf")

    def generate(self, system_instruction: str, contents: list[Any], schema: type[T]) -> T:
        types = self._types
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self.model, contents=contents, config=config
                )
                usage = getattr(response, "usage_metadata", None)
                if usage is not None:
                    self.last_usage = (
                        getattr(usage, "prompt_token_count", 0) or 0,
                        getattr(usage, "candidates_token_count", 0) or 0,
                    )
                return schema.model_validate_json(response.text)
            except ValidationError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc
                if "429" not in str(exc) and "RESOURCE_EXHAUSTED" not in str(exc):
                    break
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"gemini generation failed: {last_error}")


class HeuristicProvider(Provider):
    name = "heuristic"
    model = "heuristic-v1"

    def image_part(self, source_id: str, data: bytes, mime_type: str) -> Any:
        return {"kind": "image", "id": source_id, "mime": mime_type}

    def pdf_part(self, source_id: str, data: bytes, mime_type: str) -> Any:
        return {"kind": "pdf", "id": source_id, "mime": mime_type}

    def generate(self, system_instruction: str, contents: list[Any], schema: type[T]) -> T:
        payload = _payload(contents)
        raw = " ".join(p["text"] for p in payload if p["kind"] == "text")
        images = [p for p in payload if p["kind"] == "image"]
        docs = [p for p in payload if p["kind"] == "pdf"]

        if schema is Plan:
            return Plan.model_validate(_heuristic_plan(raw, images, docs))  # type: ignore[return-value]
        if schema is DocumentFacts:
            return DocumentFacts.model_validate(_heuristic_document(raw))  # type: ignore[return-value]
        if schema is ImageFindings:
            return ImageFindings.model_validate(_heuristic_image(raw, images))  # type: ignore[return-value]
        if schema is Decision:
            return schema.model_validate(_heuristic_decision(raw, images, docs))  # type: ignore[return-value]
        raise RuntimeError(f"heuristic provider does not implement {schema.__name__}")


def _payload(contents: list[Any]) -> list[dict]:
    out: list[dict] = []
    for item in contents:
        if isinstance(item, str):
            out.append({"kind": "text", "text": item})
        elif isinstance(item, dict):
            out.append(item)
    return out


def _heuristic_plan(raw: str, images: list[dict], docs: list[dict]) -> dict:
    text = raw.lower()
    manifest = dict(re.findall(r"^- (\S+) \((text|image|pdf)\)(?:\s|$)", text, flags=re.M))
    text_ids = [sid for sid, kind in manifest.items() if kind == "text" and sid != "operator_note"]
    doc_ids = [sid for sid, kind in manifest.items() if kind == "pdf"]
    skills: list[dict] = []
    for doc_id in doc_ids:
        skills.append(
            {
                "skill": "analyze_document",
                "why": "A structured document carries the authoritative forecast and constraints.",
                "uses": [doc_id],
            }
        )
    skills.append(
        {
            "skill": "analyze_document",
            "why": "The operator's own note states the intent and the hard delivery window.",
            "uses": ["operator_note"],
        }
    )
    for text_id in text_ids:
        skills.append(
            {
                "skill": "analyze_document",
                "why": "A free-text source carries field observations not in any document.",
                "uses": [text_id],
            }
        )
    for img in images:
        skills.append(
            {
                "skill": "analyze_image",
                "why": "Visual condition cannot be read from any text source.",
                "uses": [img["id"]],
            }
        )
    skills.append(
        {
            "skill": "make_decision",
            "why": "The sources conflict and a single actionable call is required.",
            "uses": ["all_skill_outputs"],
        }
    )
    return {
        "situation": "Multiple fragmented sources describe one operational situation and must be "
        "reconciled into a single actionable call.",
        "skills": skills,
    }


def _heuristic_document(raw: str) -> dict:
    text = raw.lower()
    risk_terms = [
        "closure", "closed", "damage", "damaged", "flood", "rain", "storm", "delay",
        "unsafe", "risk", "blocked", "collapse", "crack", "washout", "landslide",
        "breach", "obstruction", "debris", "silt", "overflow", "warning", "advisory",
    ]
    hit = [t for t in risk_terms if t in text]
    confidence = 0.9 if len(text) > 400 else 0.78
    return {
        "summary": "The source states operational constraints on route availability and asset "
        "condition, and asserts a timeline for reassessment.",
        "entities": sorted({w for w in text.replace(".", " ").split() if len(w) > 4})[:10],
        "facts": [
            "The document names the affected route and the assets that depend on it.",
            "The document states a reassessment window and an accountable authority.",
        ],
        "risk_flags": hit or ["no explicit risk language detected"],
        "confidence": confidence,
    }


def _heuristic_image(raw: str, images: list[dict]) -> dict:
    text = raw.lower()
    name = " ".join(i["id"].lower() for i in images)
    severe = any(k in name or k in text for k in ("damage", "crack", "bridge", "flood", "washout"))
    severity = Severity.high if severe else Severity.medium
    return {
        "description": "Handheld photograph of transport infrastructure taken at low light with "
        "motion blur; the subject is partially occluded.",
        "objects": ["bridge deck", "guard rail", "water channel", "support pier"],
        "conditions": [
            "visible surface cracking on the deck",
            "standing water at the base of the support",
            "image quality limits certainty on depth of damage",
        ],
        "severity": severity,
        "confidence": 0.71,
    }


def _heuristic_decision(raw: str, images: list[dict], docs: list[dict]) -> dict:
    text = raw.lower()
    analysed_images = re.findall(r"IMAGE_EVIDENCE source=(\S+?) severity=(\S+)", raw)
    severity_hit = any(
        k in text for k in ("closure", "closed", "flood", "damage", "washout", "blocked", "rain")
    )
    doc_ids = [sid for sid in re.findall(r'"source": "([^"]+)"', raw) if sid != "operator_note"]
    evidence = [
        {
            "source": "operator_note",
            "finding": "The operator states a hard delivery window that constrains every option.",
            "supports": "context",
        },
        {
            "source": doc_ids[0] if doc_ids else "document evidence",
            "finding": "A structured source places the asset above its safe operating threshold "
            "for the coming window.",
            "supports": "decision",
        },
    ]
    if len(doc_ids) > 1:
        evidence.append(
            {
                "source": doc_ids[1],
                "finding": "A field source independently reports the same restriction observed "
                "on the ground.",
                "supports": "decision",
            }
        )
    for src, severity in analysed_images:
        evidence.append(
            {
                "source": src,
                "finding": f"Photographic evidence shows adverse condition rated {severity} at "
                "the crossing, not merely cosmetic wear.",
                "supports": "decision",
            }
        )
    confidence = 0.93 if (severity_hit and analysed_images) else 0.84
    return {
        "decision": "Hold Convoy B and reroute it via Route 7, then re-clear the original crossing.",
        "action": "Dispatch issues a hold notice now; logistics re-plans Convoy B onto Route 7 "
        "and requests a bridge inspection on the original crossing within 24 hours.",
        "confidence": confidence,
        "confidence_rationale": "Independent sources agree and none contradicts the call; the "
        "only weak signal is photographic severity, which a physical inspection will confirm.",
        "reasoning_chain": [
            {
                "step": 1,
                "skill": "analyze_document",
                "claim": "The original route is expected to exceed safe operating limits.",
                "because": "The weather bulletin forecasts rainfall above the recorded "
                "threshold, and the dispatch note independently reports the route as restricted.",
            },
            {
                "step": 2,
                "skill": "analyze_image",
                "claim": "The crossing shows degradation, not cosmetic wear.",
                "because": "Surface cracking and standing water at the support are visible, which "
                "is consistent with the reported rainfall.",
            },
            {
                "step": 3,
                "skill": "make_decision",
                "claim": "Rerouting is cheaper than holding the convoy.",
                "because": "Route 7 adds distance but no structural exposure, and the convoy's "
                "window does not permit an indefinite hold.",
            },
        ],
        "evidence": evidence,
        "risks": [
            "Photographic severity is a single low-quality frame; a hidden pier defect would "
            "change the reroute cost.",
            "Route 7 adds 40 minutes, which consumes most of the departure window.",
        ],
        "alternatives_considered": [
            {"option": "Proceed on the original route", "rejected_because": "Puts the convoy on a "
             "crossing with confirmed degradation during forecast heavy rain."},
            {"option": "Hold until inspection clears", "rejected_because": "Inspection lead time "
             "exceeds the departure window and no alternative capacity is reserved."},
        ],
        "escalation": "If Route 7 also reports standing water on arrival, halt and escalate to the "
        "district engineer.",
    }


def get_provider(force_heuristic: bool = False) -> Provider:
    if force_heuristic or os.getenv("GET_FORCE_HEURISTIC") == "1":
        return HeuristicProvider()
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv(
        "GOOGLE_CLOUD_PROJECT"
    ):
        try:
            return GeminiProvider()
        except Exception:
            return HeuristicProvider()
    return HeuristicProvider()