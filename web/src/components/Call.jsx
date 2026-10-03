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

      <div className="confstrip">
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
        <div>
          <p className="confnote">{decision.confidence_rationale}</p>
          <p className="runmeta">
            run {trace.run_id} · engine {trace.mode}/{trace.model} ·{' '}
            {trace.total_latency_ms} ms end to end
          </p>
        </div>
      </div>
    </section>
  )
}

export function Trace({ decision, summary }) {
  return (
    <div className="railhead">
      <p className="eyebrow">How it got there</p>
      {summary && <p className="hint">{summary}</p>}
      <ol className="trace">
        {decision.reasoning_chain.map((step) => (
          <li key={`chain-${step.step}`}>
            <span className="num" aria-hidden="true">
              {step.step}
            </span>
            <p className="skill">{step.skill}</p>
            <p className="claim">{step.claim}</p>
            <p className="because">{step.because}</p>
          </li>
        ))}
      </ol>
    </div>
  )
}