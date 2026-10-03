import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAudit } from '../api.js'

export default function Runs() {
  const [rows, setRows] = useState(null)

  useEffect(() => {
    let live = true
    getAudit(100)
      .then((data) => {
        if (live) setRows(data)
      })
      .catch(() => {
        if (live) setRows([])
      })
    return () => {
      live = false
    }
  }, [])

  return (
    <div className="page" id="main">
      <a className="skip-link" href="#runs-title">
        Skip to content
      </a>
      <p className="eyebrow">History</p>
      <h1 className="page-title" id="runs-title">Past runs</h1>
      <p className="lede">
        Every recorded decision, newest first. The verdict column shows whether the duty
        officer accepted the call, overrode it, or has not ruled yet.
      </p>

      {rows === null ? (
        <p className="hint" aria-busy="true">
          Reading the log.
        </p>
      ) : rows.length === 0 ? (
        <div className="empty">
          Nothing has been decided yet on this service, so there is no history to show.
          <br />
          <br />
          <Link to="/console">Open the console</Link> to record the first run.
        </div>
      ) : (
        <table className="audit wide">
          <caption className="eyebrow" style={{ position: 'absolute', left: '-9999px' }}>
            Recorded decisions
          </caption>
          <thead>
            <tr>
              <th scope="col">run</th>
              <th scope="col">at</th>
              <th scope="col">engine</th>
              <th scope="col">conf</th>
              <th scope="col">officer</th>
              <th scope="col">call</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.run_id}>
                <td className="run">{row.run_id.slice(4, 14)}</td>
                <td className="at">{row.created_at.slice(0, 16).replace('T', ' ')}</td>
                <td>{row.mode}</td>
                <td>
                  {row.confidence == null ? '-' : `${Math.round(row.confidence * 100)}%`}
                </td>
                <td>{row.override ? row.override.verdict : 'none'}</td>
                <td>{(row.decision || '').slice(0, 72)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
