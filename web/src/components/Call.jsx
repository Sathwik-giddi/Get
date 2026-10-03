import { DECISION_SKILL } from '../api.js'

export function Call({ decision, trace }) {
  const pct = Math.round(decision.confidence * 100)
  return (
    <section aria-labelledby="the-call">
      <div className="call">
        <p className="eyebrow">The call</p>
        <h2 className="call-text" id="the-call">
          {decision.decision}
        </h2>
        <p className="call-action">{decision.action}</p>
      </div>

      <div className="callmeta">
        <div className="confidence">
          <p className="eyebrow">Confidence</p>
          <p className="value">{pct}%</p>
          <div
            className="meter"
            role="meter"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Confidence in the call"
          >
            <span style={{ width: `${pct}%` }} />
          </div>
          <p>{decision.confidence_rationale}</p>
        </div>

        <div className="runmeta">
          <div>run {trace.run_id}</div>
          <div>
            engine {trace.mode} / {trace.model}
          </div>
          <div>
            {trace.sources.length} sources / {trace.skill_results.length + 1} skill calls /{' '}
            {trace.total_latency_ms} ms end to end
          </div>
        </div>
      </div>
    </section>
  )
}

export function Trace({ plan, decision }) {
  const steps = []

  plan.skills.forEach((step, index) => {
    const uses = step.uses.filter((use) => use !== 'all_skill_outputs')
    steps.push(
      <li key={`plan-${index}`} className={step.skill === DECISION_SKILL ? 'decision' : ''}>
        <span className="num" aria-hidden="true">
          {index + 1}
        </span>
        <p className="skill">{step.skill}</p>
        <p className="why">{step.why}</p>
        {uses.length > 0 && (
          <p className="srclist">
            {uses.map((use) => (
              <span key={use}>{use}</span>
            ))}
          </p>
        )}
      </li>,
    )
  })

  steps.push(
    <li className="break" key="break" role="separator">
      <span>then the reasoning, numbered in the order it was concluded</span>
    </li>,
  )

  decision.reasoning_chain.forEach((step) => {
    steps.push(
      <li key={`chain-${step.step}`}>
        <span className="num" aria-hidden="true">
          {step.step}
        </span>
        <p className="skill">{step.skill}</p>
        <p className="claim">{step.claim}</p>
        <p className="because">{step.because}</p>
      </li>,
    )
  })

  return (
    <div className="railhead">
      <p className="eyebrow">How it got there</p>
      <ol className="trace">{steps}</ol>
    </div>
  )
}