from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.main import app
from agent.schemas import DocumentFacts, ImageFindings

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "demo" / "dataset"
SKILL_INSTRUCTIONS = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}

client = TestClient(app)
passed = 0
failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed.append(f"{name} {detail}")
        print(f"  FAIL  {name} {detail}")


def upload(folder: Path) -> list[tuple[str, tuple[str, bytes, str]]]:
    out = []
    for p in sorted(folder.iterdir()):
        if p.is_file():
            ct = {
                ".txt": "text/plain",
                ".pdf": "application/pdf",
                ".jpg": "image/jpeg",
                ".png": "image/png",
            }[p.suffix.lower()]
            out.append(("files", (p.name, p.read_bytes(), ct)))
    return out


print("\n[1] health and skills")
h = client.get("/health")
check("health 200", h.status_code == 200, h.text[:200])
check("skills registered", set(h.json()["skills"]) == SKILL_INSTRUCTIONS)
check("mode is reported", h.json()["mode"] in {"mock", "gemini", "vertex"})

s = client.get("/skills")
check("skills endpoint 200", s.status_code == 200)
check("every skill has a body", all(x["kind"] != "unknown" for x in s.json()))

print("\n[2] each skill produces its declared schema")
r = client.post(
    "/process",
    data={"scenario": "Decide the response now and say who acts."},
    files=upload(DATASET / "scenario_1_convoy"),
)
check("process 200", r.status_code == 200, r.text[:300])
if r.status_code != 200:
    raise SystemExit(1)
trace = r.json()

produces = {x["name"]: x["produces"] for x in s.json()}
schema_fields = {
    "DocumentFacts": set(DocumentFacts.model_fields),
    "ImageFindings": set(ImageFindings.model_fields),
}
for res in trace["skill_results"]:
    keys = set(res["output"].keys())
    expected = schema_fields[produces[res["skill"]]]
    check(
        f"{res['skill']} on {res['source_id']} matches declared schema",
        keys == expected,
        f"missing={sorted(expected - keys)} extra={sorted(keys - expected)}",
    )

print("\n[3] plan integrity")
planned = [(p["skill"], tuple(p["uses"])) for p in trace["plan"]["skills"]]
check("plan ends with make_decision", trace["plan"]["skills"][-1]["skill"] == "make_decision")
check("plan has no duplicated skill+source step", len(planned) == len(set(planned)), str(planned))
executed = [(r["skill"], r["source_id"]) for r in trace["skill_results"]]
check(
    "no source analyzed twice", len(executed) == len(set(executed)), str(executed)
)
check(
    "every analyzed source was a planned source",
    all(sid in trace["sources"] for _, sid in executed),
    str(executed),
)

print("\n[4] decision explainability")
d = trace["decision"]
check("decision is non-empty", len(d["decision"]) > 10)
check("confidence in range", 0.0 <= d["confidence"] <= 1.0, str(d["confidence"]))
check("chain has >= 2 steps", len(d["reasoning_chain"]) >= 2)
check(
    "every chain step names a skill",
    all(s["skill"] in SKILL_INSTRUCTIONS for s in d["reasoning_chain"]),
)
check(
    "every chain step has a because",
    all(len(s["because"]) > 20 for s in d["reasoning_chain"]),
)
check("evidence is attributed", all(e["source"] for e in d["evidence"]))
check(
    "evidence supports flag is valid",
    all(e["supports"] in {"decision", "against", "context"} for e in d["evidence"]),
)
check("at least one risk listed", len(d["risks"]) >= 1)
check("at least one alternative rejected", len(d["alternatives_considered"]) >= 1)
check("escalation trigger present", len(d["escalation"]) > 10)

print("\n[5] audit trail")
rows = client.get("/audit?limit=5").json()
check("audit log non-empty", len(rows) >= 1)
if rows:
    row = rows[0]
    check("audit row has run_id", row["run_id"] == trace["run_id"])
    check("audit row has confidence", isinstance(row["confidence"], float))
    check("audit row has reasoning chain", json.loads(row["reasoning_chain"]))
    check("audit row carries override slot", "override" in row)

print("\n[5b] officer override trail")
rid = trace["run_id"]
r = client.post(f"/audit/{rid}/override", data={"verdict": "accept", "note": "Route 7 confirmed."})
check("accept records 200", r.status_code == 200, r.text[:200])
check("accept echoes verdict", r.json()["verdict"] == "accept")
mine = [x for x in client.get("/audit?limit=5").json() if x["run_id"] == rid][0]
check("override merged into audit row", mine["override"]["verdict"] == "accept")
r = client.post(f"/audit/{rid}/override", data={"verdict": "override", "note": "Holding instead."})
check("latest verdict wins", client.get(f"/audit/{rid}/override").json()["verdict"] == "override")
check("bad verdict rejected", client.post(f"/audit/{rid}/override", data={"verdict": "maybe"}).status_code == 422)
check("unknown run 404", client.post("/audit/run_nope/override", data={"verdict": "accept"}).status_code == 404)
fresh = client.post("/process", data={"scenario": "Decide now."}, files=upload(DATASET / "scenario_2_warehouse")).json()
blank = client.get(f"/audit/{fresh['run_id']}/override").json()
check("known run without ruling returns null verdict", blank["verdict"] is None, str(blank))
check("unknown status 404", client.get("/audit/run_nope/override").status_code == 404)

print("\n[6] validation and failure modes")
r2 = client.post("/process", data={"scenario": "  "}, files=upload(DATASET / "scenario_1_convoy"))
check("blank scenario rejected", r2.status_code == 422, str(r2.status_code))
r3 = client.post("/process", data={"scenario": "Decide."}, files=[])
check("no sources rejected", r3.status_code == 422, str(r3.status_code))

print("\n[7] text-only input still decides")
r4 = client.post(
    "/process",
    data={"scenario": "Decide whether to hold the convoy and say who acts."},
    files=[
        ("files", ("note.txt", b"Weather warning: 68mm rain expected. Convoy must leave by 16:00.",
                   "text/plain"))
    ],
)
check("text-only 200", r4.status_code == 200, r4.text[:300])
if r4.status_code == 200:
    t4 = r4.json()
    check("text-only produced a decision", len(t4["decision"]["decision"]) > 10)
    check("text-only still has a chain", len(t4["decision"]["reasoning_chain"]) >= 2)

print("\n[8] determinism in mock mode")
a = client.post("/process", data={"scenario": "Decide."}, files=upload(DATASET / "scenario_1_convoy"))
b = client.post("/process", data={"scenario": "Decide."}, files=upload(DATASET / "scenario_1_convoy"))
if a.json()["mode"] == "mock" and b.json()["mode"] == "mock":
    check("mock output is stable", a.json()["decision"] == b.json()["decision"])

print(f"\n{passed} passed, {len(failed)} failed")
for f in failed:
    print(f"  - {f}")
raise SystemExit(1 if failed else 0)