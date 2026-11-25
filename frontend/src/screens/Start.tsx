import { useState } from 'react'

import { api, ApiError } from '../lib/api'
import type { AppInfo, StudentOut } from '../lib/types'

interface Props {
  info: AppInfo | null
  onReady: (student: StudentOut) => void
  onTeacher: () => void
}

type Mode = 'choose' | 'solo' | 'class'

export function Start({ info, onReady, onTeacher }: Props) {
  const [mode, setMode] = useState<Mode>('choose')
  const [pseudonym, setPseudonym] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const student = await api.createStudent(
        pseudonym.trim(),
        mode === 'class' ? code.trim().toUpperCase() : undefined,
      )
      onReady(student)
    } catch (exception) {
      setError(
        exception instanceof ApiError
          ? exception.message
          : 'Nie udało się rozpocząć. Odśwież stronę i spróbuj ponownie.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="screen screen-start">
      <div className="start-card">
        <h1 className="start-title">Naucz Kubę</h1>
        <p className="start-lead">
          Kuba to kolega z klasy, który rozwiązuje zadanie i popełnia jeden typowy błąd
          w rozumowaniu. Twoje zadanie: znaleźć go i wytłumaczyć — aż Kuba naprawdę zrozumie.
        </p>

        {mode === 'choose' ? (
          <div className="start-actions">
            <button type="button" className="btn btn-primary" onClick={() => setMode('solo')}>
              Ćwiczę sam
            </button>
            <button type="button" className="btn" onClick={() => setMode('class')}>
              Mam kod klasy
            </button>
          </div>
        ) : (
          <form className="start-form" onSubmit={submit}>
            {mode === 'class' ? (
              <div>
                <label className="label" htmlFor="code">
                  Kod klasy (6 znaków)
                </label>
                <input
                  id="code"
                  className="input mono"
                  value={code}
                  onChange={(event) => setCode(event.target.value.toUpperCase().slice(0, 6))}
                  autoComplete="off"
                  maxLength={6}
                  required
                  placeholder="np. K7MQ2P"
                />
              </div>
            ) : null}

            <div>
              <label className="label" htmlFor="pseudonym">
                Twój pseudonim (nie podawaj imienia ani nazwiska)
              </label>
              <input
                id="pseudonym"
                className="input"
                value={pseudonym}
                onChange={(event) => setPseudonym(event.target.value.slice(0, 24))}
                autoComplete="off"
                minLength={2}
                maxLength={24}
                required
                placeholder="np. Lis42"
              />
            </div>

            {error ? (
              <p className="small" role="alert" style={{ margin: 0, color: 'var(--ink)' }}>
                <span className="error-mark" aria-hidden="true" /> {error}
              </p>
            ) : null}

            <div className="start-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Chwilkę…' : 'Zaczynamy'}
              </button>
              <button type="button" className="btn" onClick={() => setMode('choose')}>
                Wróć
              </button>
            </div>
          </form>
        )}

        <hr className="hr" />

        <p className="small muted start-disclaimer">
          {info?.disclaimer ??
            'Kuba to program AI. Myli się celowo, żebyś mógł go nauczyć — ale czasem może pomylić się też przypadkiem.'}
        </p>
        <p className="small muted">
          {info?.privacy ??
            'Nie zbieramy danych osobowych: brak kont, e-maili i nazwisk. Nagrania głosu nie są zapisywane.'}
        </p>
        {info?.offline_only ? (
          <p className="small muted">Tryb offline: wszystko liczy się na tym komputerze.</p>
        ) : null}

        <button type="button" className="linkbtn start-teacher" onClick={onTeacher}>
          Jestem nauczycielem
        </button>
      </div>
    </main>
  )
}
