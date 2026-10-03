# Get

A multi-modal decision agent. Hand it one messy operational situation: a dispatch note, a
blurry phone photo, a PDF bulletin. It works out which skills to run, runs them one source at a
time, and returns a single call with the reasoning chain and confidence behind it.

Built for **P42**: scalable, multi-modal AI with Gemini and Google Cloud, making accurate,
context-aware, explainable decisions in dynamic environments.

## The idea in one paragraph

Most multi-modal AI answers in one shot: everything goes in, one answer comes out, and nobody
can see how it got there. Get splits the work. A planner chooses skills, each skill is
a markdown contract that returns a typed, validated result, and one skill is reserved for the
call itself.

Because every step is separate and structured, the explanation is not an afterthought the model
writes about its own answer. It is the pipeline that produced the answer.

## Pipeline

```
text + image + pdf
        |
        v
   [ planner ]          picks ordered skills, names the source ids each one consumes
        |
        v
   [ skills ]           analyze_document / analyze_image   (one call per source)
        |
        v
   [ make_decision ]    reconciles every skill output into one call
        |
        v
   decision + reasoning chain + evidence + confidence + risks + escalation
        |
        v
   audit row            JSONL locally, BigQuery when configured
        |
        v
   duty officer         accept or override, appended to the same trail
```

Read as an OODA loop: the sources are Observe, the plan and skill outputs are Orient, the
single call is Decide, and the officer verdict plus the audit row are Act. The loop is
visible on screen in that order, which is the point.

## Related work

Ideas below are cited where they are used. No code was taken from any of them.

- RAPTOR-AI (arXiv:2602.00030): agentic multimodal retrieval for disaster response, with a
  controller that picks its strategy per scenario. Our planner is the small version of that
  controller, and the OODA framing above comes from this paper.
- SafeMate (2025): evidence-grounded emergency guidance with Chain-of-Verification. Backs the
  rule that every reasoning step cites the skill output it came from.
- CrisiSense-RAG: split text and visual analysts fused into one damage assessment. Inspired
  `tests/test_eval.py`, which scores our runs for structure and stability instead of fusing.
- Multimodal AI Triage Assistant: per-decision explanations with an audit trail and override
  tracking. Inspired `POST /audit/{run_id}/override`.
- google-gemini/gemini-skills: skill format and structured-output practice for the provider.

## Layout

```
agent/          core.py orchestration, gemini.py provider + heuristic fallback, schemas.py,
                registry.py skill loader, storage.py uploads, audit.py log
skills/         one SKILL.md per skill, frontmatter declares the contract
api/            FastAPI service (deployable to Cloud Run as-is)
web/            React front end, Vite, served on :3000
                pages/ Landing, Console, Runs behind a topbar; one design system
demo/           dataset generator for the two demo scenarios
tests/          acceptance checks you can run before any demo
```

## Run it

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium   # only needed for the browser gate and screenshots
.venv/bin/python demo/make_dataset.py     # generates the messy demo inputs
cd web && npm ci && cd ..                 # front-end dependencies
./run.sh dev                             # API on :8123, web on http://localhost:3000
```

Both ports are configurable: `API_PORT=9000 WEB_PORT=3600 ./run.sh dev`.

For a production-shaped run, build the front end and let FastAPI serve it, which is
the single container Cloud Run deploys:

```bash
./run.sh serve        # one process on :8123, no second server
```

## Modes

The agent runs in one of three modes, and the UI always tells you which.

| Mode | When | What it is |
| --- | --- | --- |
| `heuristic` | no credentials present, or `GET_FORCE_HEURISTIC=1` | keyword-rule stand-in, no network calls. Fine for building and for rehearsing the demo. |
| `gemini` | `GEMINI_API_KEY` is set | Gemini via the AI Developer API |
| `vertex` | `GOOGLE_CLOUD_PROJECT` is set | Gemini on Vertex AI |

Never present heuristic output as a real run. The UI states the engine in words on every
screen, including when the engine is heuristic.

```bash
cp .env.example .env      # then paste a key into GEMINI_API_KEY
```

## Skills

Each skill is a `SKILL.md`: YAML-ish frontmatter declaring `consumes`, `produces` and the
type of the result, then instructions written as constraints rather than suggestions.

| Skill | Reads | Returns |
| --- | --- | --- |
| `analyze_document` | text notes, PDFs | `DocumentFacts`: entities, facts, risk flags |
| `analyze_image` | images | `ImageFindings`: visible conditions, severity, confidence |
| `make_decision` | all skill outputs | `Decision`: the call, the chain, the evidence |

Two rules do the heavy lifting on the explainability claim:

1. Only `make_decision` is allowed to decide. Everything upstream extracts and reports.
2. `make_decision` must cite the specific skill output behind every step in its chain, must
   list at least one alternative it rejected, and must lower its confidence when the sources
   disagree.

Adding a skill means adding one folder under `skills/` and one Pydantic model in
`agent/schemas.py`. The registry picks it up automatically; `/health` and the UI sidebar list
it with no code change.

## Output contract

Every run returns the same shape, which is what the UI, the audit log and BigQuery all read:

```json
{
  "run_id": "run_1a2b3c4d5e6f",
  "mode": "gemini",
  "sources": ["operator_note", "IMG_4471_bridge.jpg", "bulletin.pdf", "dispatch.txt"],
  "plan": { "situation": "...", "skills": [{ "skill": "...", "why": "...", "uses": [...] }] },
  "skill_results": [{ "skill": "...", "source_id": "...", "output": {}, "latency_ms": 812 }],
  "decision": {
    "decision": "one imperative sentence",
    "action": "who does what next",
    "confidence": 0.93,
    "confidence_rationale": "...",
    "reasoning_chain": [{ "step": 1, "skill": "...", "claim": "...", "because": "..." }],
    "evidence": [{ "source": "...", "finding": "...", "supports": "decision" }],
    "risks": ["..."],
    "alternatives_considered": [{ "option": "...", "rejected_because": "..." }],
    "escalation": "the observable trigger that needs a human"
  }
}
```

Model output is validated against a Pydantic schema on every call, and `temperature=0.1`. If
validation fails the call is retried, so a malformed response cannot silently become a
decision.

## Google Cloud

Local-first by default, cloud-enabled by flag. Nothing breaks when a flag is off.

| Flag | Effect |
| --- | --- |
| `GOOGLE_CLOUD_PROJECT` | Gemini runs on Vertex AI instead of the AI Developer API |
| `GET_BIGQUERY=1` | audit rows are inserted into BigQuery as well as JSONL |
| `GET_GCS=1` + `GCS_BUCKET` | uploads are mirrored to Cloud Storage and referenced by `gs://` URI |
| `GET_FORCE_HEURISTIC=1` | force heuristic mode even with credentials present |

For Cloud Run, the `Dockerfile` builds both halves into one image: Python deps, then
`npm ci` and `npm run build`, then uvicorn serves the API and the built front end from the
same process. One deploy, one cold start.

```bash
gcloud run deploy get \
  --source . --region asia-south1 --min-instances 1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT,GET_BIGQUERY=1
```

`--min-instances 1` is not optional if you plan to demo on it: cold starts in the middle of a
pitch are how good demos die.

## Demo scenarios

`demo/make_dataset.py` generates two, so you never demo against a file you have not seen:

- **scenario_1_convoy**: a dispatch note, a blurry tilted photo of a bridge, and a weather
  bulletin. The sources agree the route is not safe and disagree about what to do about the
  fuel margin. Good for showing contradiction handling.
- **scenario_2_warehouse**: a warehouse incident report, a flooded-floor photo, and a cold
  chain SOP with a reachability clause. Good for showing that a procedural document changes
  the decision, not just the facts.

Set `VITE_AUTORUN=1` when starting the web UI to skip the upload dialog and run the first scenario
on load. Useful for a live pitch where a file picker is one more thing to fail.

## Design

`DESIGN.md` holds the direction: who the user is, what the screen is for, the palette with
measured contrast ratios, the type rules, and the identity motif. Read it before changing
anything in `web/src/`.

The short version: this is an operations console, not a dashboard. One focal point per screen
(the call), one accent color on exactly two elements, and a vertical trace rail that carries
the plan and the reasoning chain as one continuous line of custody.

`docs/audits/` holds the design reviews this interface went through and what each one changed.

## Tests

```bash
.venv/bin/python tests/test_acceptance.py   # pipeline and output contract, no browser
.venv/bin/python tests/test_eval.py         # structure + stability scoring, writes demo/eval_report.json
.venv/bin/python tests/test_gate_web.py    # the rendered UI, measured in a real browser
```

The acceptance checks cover what the demo depends on: every planned skill executes, no source
is analysed twice, the plan always terminates in `make_decision`, every reasoning step names a
skill it really came from, evidence is attributed and flagged, the audit row lands, the duty
officer can accept or override a run with the latest verdict winning, blank input
is rejected, and heuristic mode is deterministic.

The eval harness runs both demo scenarios plus reworded and shuffled variants, scores each run
on ten structural checks, and measures decision stability across the variants. It writes
`demo/eval_report.json` so the numbers in the deck are regenerable, not typed in.

The gate checks what the eye cannot: it reads computed styles from the live DOM and verifies
contrast for all fourteen text roles against their real backgrounds, asserts the call is the
largest text on the page, walks the tab order and checks the focus ring, exercises the uploader
and its remove buttons, walks four viewports for horizontal overflow, checks every tap target
against 44px, and fails on console errors. It runs the app rather than trusting the stylesheet,
which is how the defects in `docs/audits/audit-002` and `audit-003` were caught.

## Screenshots

```bash
.venv/bin/python demo/capture_screens.py     # requires the stack to be running
```

Drives the real UI with a headless browser and writes `demo/shots/`:

| File | What it shows |
| --- | --- |
| `01_landing.png` | product, skills, engine mode, empty audit trail |
| `02_convoy_decision.png` | the decision, confidence, plan and attributed evidence |
| `02_convoy_reasoning.png` | the reasoning chain, risks, rejected alternatives, escalation |
| `03_warehouse_*.png` | the same UI on the second scenario |

Regenerate these after you add a real Gemini key, so nothing in the deck carries the
heuristic-mode notice.