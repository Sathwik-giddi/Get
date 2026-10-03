import { EVIDENCE_STANCE } from '../api.js'

export function Evidence({ decision }) {
  return (
    <section className="reference" aria-labelledby="evidence-heading">
      <div>
        <p className="eyebrow" id="evidence-heading">
          Evidence
        </p>
        {decision.evidence.map((item, index) => {
          const stance = EVIDENCE_STANCE[item.supports] || {
            label: item.supports,
            color: 'var(--sb-ink-muted)',
          }
          return (
            <div className="ev" key={`${item.source}-${index}`}>
              <span className="stance" style={{ color: stance.color }}>
                {stance.label}
              </span>
              <span className="src">{item.source}</span>
              <br />
              {item.finding}
            </div>
          )
        })}
      </div>

      {decision.risks.length > 0 && (
        <section aria-labelledby="risks-heading">
          <p className="eyebrow" id="risks-heading">
            What would make this wrong
          </p>
          {decision.risks.map((risk, index) => (
            <div className="ev" key={index}>
              {risk}
            </div>
          ))}
        </section>
      )}

      {decision.alternatives_considered.length > 0 && (
        <details className="raw">
          <summary>
            Rejected first ({decision.alternatives_considered.length})
          </summary>
          {decision.alternatives_considered.map((alt, index) => (
            <div className="ev" key={index}>
              <strong>{alt.option}</strong>
              <br />
              <span className="why">{alt.rejected_because}</span>
            </div>
          ))}
        </details>
      )}

      <section aria-labelledby="escalation-heading">
        <p className="eyebrow" id="escalation-heading">
          Hand it to a human when
        </p>
        <div className="note">{decision.escalation}</div>
      </section>
    </section>
  )
}