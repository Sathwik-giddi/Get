from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.main import app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "demo" / "dataset"
REPORT = ROOT / "demo" / "eval_report.json"

CONVOY_SCENARIO = (
    "Convoy B must reach Kolar field hospital with medical stores before tomorrow "
    "morning. Decide what happens to Convoy B right now, and say what you need from whom."
)
WAREHOUSE_SCENARIO = (
    "A district warehouse has reported water ingress damaging 40 crates of vaccine "
    "stock. Decide the response and name what must happen in the next 6 hours."
)

client = TestClient(app)


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


def run_once(scenario: str, files) -> dict:
    r = client.post("/process", data={"scenario": scenario}, files=files)
    r.raise_for_status()
    return r.json()


def structure_score(trace: dict) -> tuple[float, list[str]]:
    checks = []
    d = trace["decision"]
    checks.append(("decision non-empty", len(d["decision"]) > 10))
    checks.append(("action names a next step", len(d["action"]) > 10))
    checks.append(("confidence in range", 0.0 <= d["confidence"] <= 1.0))
    checks.append(("chain has 2+ steps", len(d["reasoning_chain"]) >= 2))
    checks.append(
        ("every chain step cites a skill",
         all(s["skill"] and len(s["because"]) > 20 for s in d["reasoning_chain"])),
    )
    checks.append(("evidence attributed", all(e["source"] for e in d["evidence"])))
    checks.append(
        ("evidence flags valid",
         all(e["supports"] in {"decision", "against", "context"} for e in d["evidence"])),
    )
    checks.append(("risk listed", len(d["risks"]) >= 1))
    checks.append(("alternative rejected", len(d["alternatives_considered"]) >= 1))
    checks.append(("escalation trigger present", len(d["escalation"]) > 10))
    passed = sum(1 for _, ok in checks if ok)
    failed = [name for name, ok in checks if not ok]
    return passed / len(checks), failed


def main() -> int:
    cases = [
        ("convoy/base", CONVOY_SCENARIO, "scenario_1_convoy"),
        ("convoy/reworded", CONVOY_SCENARIO.replace("Decide what happens", "Tell us what to do") + " ",
         "scenario_1_convoy"),
        ("convoy/shuffled", CONVOY_SCENARIO, "scenario_1_convoy"),
        ("warehouse/base", WAREHOUSE_SCENARIO, "scenario_2_warehouse"),
        ("warehouse/reworded", " " + WAREHOUSE_SCENARIO.replace("Decide the response", "Give the call"),
         "scenario_2_warehouse"),
    ]
    results = []
    print(f"{'case':<20} {'struct':>7} {'conf':>6} {'ms':>6}  failed checks")
    for name, scenario, folder in cases:
        files = upload(DATASET / folder)
        if name.endswith("/shuffled"):
            files = list(reversed(files))
        trace = run_once(scenario, files)
        score, failed = structure_score(trace)
        results.append({
            "case": name,
            "structure": round(score, 3),
            "confidence": trace["decision"]["confidence"],
            "latency_ms": trace["total_latency_ms"],
            "decision": trace["decision"]["decision"],
            "failed": failed,
        })
        print(f"{name:<20} {score:>7.2f} {trace['decision']['confidence']:>6.2f} "
              f"{trace['total_latency_ms']:>6}  {', '.join(failed) or '-'}")

    base = {r["case"]: r["decision"] for r in results if r["case"].endswith("/base")}
    stable = []
    for r in results:
        if r["case"].endswith("/base"):
            continue
        stem = r["case"].rsplit("/", 1)[0] + "/base"
        same = r["decision"] == base[stem]
        stable.append(same)
        r["stable_vs_base"] = same
    stability = sum(stable) / len(stable) if stable else 1.0

    def stable_form(trace: dict) -> dict:
        d = dict(trace["decision"])
        d.pop("total_latency_ms", None)
        return d

    again = run_once(CONVOY_SCENARIO, upload(DATASET / "scenario_1_convoy"))
    base_trace = run_once(CONVOY_SCENARIO, upload(DATASET / "scenario_1_convoy"))
    deterministic = (
        stable_form(again) == stable_form(base_trace) if again.get("mode") == "mock" else None
    )

    probe = run_once(CONVOY_SCENARIO, upload(DATASET / "scenario_1_convoy"))
    report = {
        "engine": probe["mode"],
        "model": probe["model"],
        "cases": results,
        "mean_structure": round(sum(r["structure"] for r in results) / len(results), 3),
        "stability": round(stability, 3),
        "deterministic_rerun": deterministic,
    }
    REPORT.write_text(json.dumps(report, indent=2))
    print(f"\nstability under rewording/shuffle: {stability:.2f}")
    print(f"deterministic rerun (mock only): {deterministic}")
    print(f"mean structure score: {report['mean_structure']:.2f}")
    print(f"report: {REPORT.relative_to(ROOT)}")

    failed = [r for r in results if r["failed"]]
    if failed or stability < 1.0 or deterministic is False:
        print(f"\nEVAL FAIL: {len(failed)} cases with failed checks, stability {stability:.2f}")
        return 1
    print("\nEVAL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
