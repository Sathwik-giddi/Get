import { useEffect, useState } from 'react'
import { getOverride, recordOverride } from '../api.js'

export function Officer({ runId, onRecorded }) {
  const [note, setNote] = useState('')
  const [status, setStatus] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let live = true
    setStatus(undefined)
    getOverride(runId)
      .then((record) => {
        if (live) setStatus(record.verdict ? record : null)
      })
      .catch(() => {
        if (live) setStatus(null)
      })
    return () => {
      live = false
    }
  }, [runId])

  async function act(verdict) {
    setBusy(true)
    setError(null)
    try {
      const record = await recordOverride(runId, verdict, note)
      setStatus(record)
      setNote('')
      onRecorded?.()
    } catch (cause) {
      setError(cause.message)
    } finally {
      setBusy(false)
    }
  }

  if (status === undefined) {
    return (
      <section aria-labelledby="officer-heading" className="officer" aria-busy="true">
        <p className="eyebrow" id="officer-heading">
          Duty officer
        </p>
        <p className="hint">Checking the log.</p>
      </section>
    )
  }

  return (
    <section aria-labelledby="officer-heading" className="officer">
      <p className="eyebrow" id="officer-heading">
        Duty officer
      </p>
      {status ? (
        <div className="note">
          <p>
            <strong>
              {status.verdict === 'accept' ? 'Accepted' : 'Overridden'} by the duty officer
            </strong>{' '}
            at {status.recorded_at.slice(0, 16).replace('T', ' ')}
          </p>
          {status.note && <p>{status.note}</p>}
          <p className="hint">Recording again replaces this entry. The log keeps every version.</p>
        </div>
      ) : (
        <p className="hint">No officer has ruled on this run yet.</p>
      )}

      <div className="field officer-gap">
        <label htmlFor="officer-note">Officer note</label>
        <textarea
          id="officer-note"
          value={note}
          disabled={busy}
          maxLength={500}
          placeholder="Route 7 confirmed clear by dispatch"
          onChange={(event) => setNote(event.target.value)}
        />
        <p className="hint" aria-live="polite">
          {note.length}/500
        </p>
      </div>

      <div className="officer-row">
        <button className="quiet" type="button" disabled={busy} onClick={() => act('accept')}>
          {busy ? 'Recording' : 'Accept the call'}
        </button>
        <button className="quiet-solid" type="button" disabled={busy} onClick={() => act('override')}>
          {busy ? 'Recording' : 'Override the call'}
        </button>
      </div>

      {error && (
        <div className="note fault officer-gap">
          <p>{error}</p>
        </div>
      )}
    </section>
  )
}