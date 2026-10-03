import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiUrl, decide, getAudit, getHealth, MODE_STATE } from './api.js'
import { SCENARIO_NAMES, SCENARIOS } from './scenarios.js'
import { Inputs } from './components/Inputs.jsx'
import { Call, Trace } from './components/Call.jsx'
import { Evidence } from './components/Evidence.jsx'
import { Officer } from './components/Officer.jsx'

const AUTORUN = import.meta.env.VITE_AUTORUN === '1'

function ServiceDown({ problem }) {
  return (
    <section className="note fault" style={{ marginTop: 26 }}>
      <p>
        <strong>Cannot reach the decision service.</strong>
      </p>
      <p>{problem.message}</p>
      <p>
        Start it with <code>./run.sh</code>, which brings up the API and this page together. If
        the service is already running, check that the port matches.
      </p>
    </section>
  )
}

function EmptyState({ onLoad }) {
  return (
    <section aria-labelledby="empty-heading" className="empty-state">
      <p className="eyebrow" id="empty-heading">
        How it works
      </p>
      <ol className="trace">
        <li>
          <span className="num" aria-hidden="true">
            1
          </span>
          <p className="skill">sources in</p>
          <p className="srclist" aria-label="Example sources">
            <span>a dispatch note</span>
            <span>a bridge photo</span>
            <span>a weather bulletin</span>
          </p>
        </li>
        <li>
          <span className="num" aria-hidden="true">
            2
          </span>
          <p className="skill">skills assigned</p>
          <p className="because">
            The planner assigns one skill per source. The skills extract, they never decide.
          </p>
        </li>
        <li>
          <span className="num" aria-hidden="true">
            3
          </span>
          <p className="skill">one call out</p>
          <p className="because">
            One step decides. The call, its reasons, and its evidence land on this page.
          </p>
          <button className="primary empty-cta" type="button" onClick={onLoad}>
            Load the convoy situation
          </button>
          <p className="hint">Or attach your own sources on the left and press Decide now.</p>
        </li>
      </ol>
    </section>
  )
}

function Loading({ scenario }) {
  return (
    <section className="progress running" aria-live="polite" aria-busy="true">
      <div>
        <strong>Reconciling sources.</strong> The planner is choosing skills, then each one runs
        on one source at a time.
        <ol>
          <li>plan: reading {scenario ? `${scenario.slice(0, 40)}...` : 'the situation'}</li>
          <li>analyze_document on every text and PDF source</li>
          <li>analyze_image on every image</li>
          <li>make_decision on the skill outputs</li>
        </ol>
      </div>
    </section>
  )
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [serviceError, setServiceError] = useState(null)
  const [audit, setAudit] = useState([])

  const [scenarioName, setScenarioName] = useState(SCENARIO_NAMES[0])
  const [scenario, setScenario] = useState(SCENARIOS[SCENARIO_NAMES[0]].text)
  const [files, setFiles] = useState([])
  const [running, setRunning] = useState(false)
  const [trace, setTrace] = useState(null)
  const [fault, setFault] = useState(null)

  const refreshAudit = useCallback(async () => {
    try {
      setAudit(await getAudit(5))
    } catch {
      setAudit([])
    }
  }, [])

  useEffect(() => {
    let live = true
    getHealth()
      .then((data) => {
        if (live) setHealth(data)
      })
      .catch((error) => {
        if (live) setServiceError(error)
      })
    refreshAudit()
    return () => {
      live = false
    }
  }, [refreshAudit])

  const loadPreset = useCallback(async (name) => {
    setScenarioName(name)
    setScenario(SCENARIOS[name].text)
    setFault(null)
    try {
      const folder = SCENARIOS[name].folder
      const base = `${apiUrl('/demo/dataset')}/${folder}/`
      const response = await fetch(`${base}manifest`)
      if (!response.ok) throw new Error(response.statusText)
      const names = await response.json()
      const loaded = await Promise.all(
        names.map(async (entry) => {
          const file = await fetch(base + entry)
          return new File([await file.blob()], entry, {
            type: file.headers.get('content-type') || 'application/octet-stream',
          })
        }),
      )
      setFiles(loaded)
    } catch {
      setFiles([])
    }
  }, [])

  useEffect(() => {
    loadPreset(SCENARIO_NAMES[0])
  }, [loadPreset])

  const run = useCallback(async () => {
    if (files.length === 0) {
      setFault({
        message: 'No sources attached, so there is nothing to reconcile.',
      })
      return
    }
    setRunning(true)
    setFault(null)
    try {
      const result = await decide(scenario, files)
      setTrace(result)
      refreshAudit()
    } catch (error) {
      if (error.kind === 'unreachable') setServiceError(error)
      else setFault({ message: error.message })
    } finally {
      setRunning(false)
    }
  }, [files, scenario, refreshAudit])

  const mode = health?.mode ?? 'unknown'
  const modeState = MODE_STATE[mode] || { label: 'unrecognised engine', color: 'var(--sb-ink-muted)' }

  const decisionView = useMemo(() => {
    if (serviceError) return <ServiceDown problem={serviceError} />
    if (running) return <Loading scenario={scenario} />
    if (fault) {
      return (
        <section className="note fault" style={{ marginTop: 26 }}>
          <p>
            <strong>The service rejected this run.</strong>
          </p>
          <p>{fault.message}</p>
          <p>The scenario and the sources both have to be present. Nothing was recorded.</p>
        </section>
      )
    }
    if (trace) {
      return (
        <>
          <Call decision={trace.decision} trace={trace} />
          <div className="split">
            <Trace plan={trace.plan} decision={trace.decision} />
            <Evidence decision={trace.decision} />
          </div>
          <Officer runId={trace.run_id} onRecorded={refreshAudit} />
          <details className="raw">
            <summary>Raw skill output and full trace</summary>
            {trace.skill_results.map((result) => (
              <div key={`${result.skill}-${result.source_id}`}>
                <h3>
                  {result.skill} on {result.source_id} / {result.latency_ms} ms
                </h3>
                <pre>{JSON.stringify(result.output, null, 2)}</pre>
              </div>
            ))}
            <h3>complete run record</h3>
            <pre>{JSON.stringify(trace, null, 2)}</pre>
          </details>
        </>
      )
    }
    return <EmptyState onLoad={() => loadPreset(SCENARIO_NAMES[0])} />
  }, [serviceError, running, fault, trace, scenario, refreshAudit, loadPreset])

  return (
    <>
      <a className="skip-link" href="#decision">
        Skip to the decision
      </a>
      <div className="shell">
        <Inputs
          scenarios={SCENARIOS}
          scenarioName={scenarioName}
          onScenarioName={loadPreset}
          scenario={scenario}
          onScenario={setScenario}
          files={files}
          onFiles={setFiles}
          onRun={run}
          running={running || AUTORUN}
          autorun={AUTORUN}
          mode={mode}
          modeLabel={modeState.label}
          sink={health?.bigquery_table}
          audit={audit}
        />

        <main className="main" id="decision">
          <header className="masthead">
            <h1>Get</h1>
            <p>One situation, several sources, one call you can check.</p>
            {mode !== 'heuristic' && health && (
              <p className="runmeta" style={{ marginTop: 8 }}>
                engine {mode} / {modeState.label}
              </p>
            )}
          </header>

          {health && (
            <p className="runmeta" style={{ marginTop: 8 }}>
              engine {mode}.{' '}
              {mode === 'heuristic'
                ? 'Heuristic output, not a model. Set GEMINI_API_KEY in .env and restart to switch engines.'
                : modeState.label}
            </p>
          )}

          {decisionView}
        </main>
      </div>
    </>
  )
}