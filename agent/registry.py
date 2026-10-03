from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


@dataclass(frozen=True)
class Skill:
    name: str
    kind: str
    description: str
    consumes: list[str]
    produces: str
    instructions: str


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    _, fm, body = raw.split("---", 2)
    meta: dict[str, str] = {}
    for line in fm.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.strip()


def _load(path: Path) -> Skill:
    meta, body = _parse_frontmatter(path.read_text())
    return Skill(
        name=meta["name"],
        kind=meta.get("kind", "unknown"),
        description=meta.get("description", ""),
        consumes=[c.strip() for c in meta.get("consumes", "").split(",") if c.strip()],
        produces=meta.get("produces", ""),
        instructions=body,
    )


class SkillRegistry:
    def __init__(self, skills_dir: Path = SKILLS_DIR) -> None:
        self.skills: dict[str, Skill] = {}
        for md in sorted(skills_dir.glob("*/SKILL.md")):
            skill = _load(md)
            self.skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        if name not in self.skills:
            raise KeyError(f"unknown skill {name!r}; available: {sorted(self.skills)}")
        return self.skills[name]

    def catalogue(self) -> str:
        lines = []
        for s in self.skills.values():
            lines.append(f"- {s.name} [{s.kind}]: {s.description}")
        return "\n".join(lines)

    def prompt_for(self, name: str) -> str:
        return self.get(name).instructions


REGISTRY = SkillRegistry()