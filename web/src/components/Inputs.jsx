export function Inputs({
  scenarios,
  scenarioName,
  onScenarioName,
  scenario,
  onScenario,
  files,
  onFiles,
  onRun,
  running,
  autorun,
  mode,
  modeLabel,
  sink,
  audit,
}) {
  const preset = scenarios[scenarioName]

  return (
    <aside className="rail" aria-label="Inputs and audit trail">
      <div className="field">
        <label htmlFor="scenario-name">Situation</label>
        <select
          id="scenario-name"
          value={scenarioName}
          disabled={running || autorun}
          onChange={(event) => onScenarioName(event.target.value)}
        >
          {Object.keys(scenarios).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="scenario-text">What has happened</label>
        <textarea
          id="scenario-text"
          value={scenario}
          disabled={running || autorun}
          onChange={(event) => onScenario(event.target.value)}
        />
      </div>

      <div className="field">
        <span className="label" id="sources-label">
          Sources
        </span>
        <label className="dropzone" htmlFor="file-input">
          <strong>{files.length > 0 ? 'Replace sources' : 'Attach sources'}</strong>
          <span>Text, a photo, a PDF. The disagreement between them is the point.</span>
          <input
            id="file-input"
            type="file"
            multiple
            disabled={running || autorun}
            accept=".txt,.md,.pdf,.png,.jpg,.jpeg,.webp"
            aria-labelledby="sources-label"
            onChange={(event) => onFiles(Array.from(event.target.files || []))}
          />
        </label>

        {files.length > 0 && (
          <ul className="filelist">
            {files.map((file) => (
              <li key={`${file.name}-${file.size}`}>
                <span>{file.name}</span>
                <button
                  type="button"
                  aria-label={`Remove ${file.name}`}
                  disabled={running || autorun}
                  onClick={() => onFiles(files.filter((item) => item !== file))}
                >
                  <span aria-hidden="true">x</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        className="primary"
        type="button"
        onClick={onRun}
        disabled={running || files.length === 0}
      >
        {running ? 'Reconciling' : 'Decide now'}
      </button>

      {files.length === 0 && !running && (
        <p className="hint">
          No sources attached, so there is nothing to reconcile. Pick the situation preset above,
          which loads its own three sources.
        </p>
      )}

      <div style={{ marginTop: 40 }}>
        <p className="eyebrow">Audit trail</p>
        <p className="hint">
          {sink ? `Writing to ${sink}.` : 'Writing to local JSONL. BigQuery is off.'}
        </p>

        {audit.length > 0 ? (
          <>
            <table className="audit">
              <caption className="eyebrow" style={{ position: 'absolute', left: '-9999px' }}>
                Most recent decisions
              </caption>
              <thead>
                <tr>
                  <th scope="col">run</th>
                  <th scope="col">at</th>
                  <th scope="col">conf</th>
                  <th scope="col">officer</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((row) => (
                  <tr key={row.run_id}>
                    <td className="run">{row.run_id.slice(4, 12)}</td>
                    <td className="at">{row.created_at.slice(0, 16).replace('T', ' ')}</td>
                    <td>
                      {row.confidence == null
                        ? '-'
                        : `${Math.round(row.confidence * 100)}%`}
                    </td>
                    <td>{row.override ? row.override.verdict : 'none'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="hint">
              {audit.length} most recent. Every run is kept, including the ones you discard.
            </p>
          </>
        ) : (
          <div className="empty">
            Nothing has been decided yet on this service, so there is no history to show.
            <br />
            <br />
            Pick a situation, attach its sources, then press Decide now. Every run appends a row
            here, including the ones you throw away.
          </div>
        )}
      </div>
    </aside>
  )
}