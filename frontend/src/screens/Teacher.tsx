import { useCallback, useState } from 'react'

import { api, ApiError, downloadCsv } from '../lib/api'
import type { Dashboard } from '../lib/types'

interface Props {
  onBack: () => void
}

type View = 'login' | 'create' | 'dashboard'

export function Teacher({ onBack }: Props) {
  const [view, setView] = useState<View>('login')
  const [code, setCode] = useState('')
  const [pin, setPin] = useState('')
  const [name, setName] = useState('')
  const [created, setCreated] = useState<{ code: string; pin: string } | null>(null)
  const [data, setData] = useState<Dashboard | null>(null)
  const [topicFilter, setTopicFilter] = useState<string>('wszystkie')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async (classCode: string, classPin: string) => {
    setBusy(true)
    setError(null)
    try {
      const dashboard = await api.dashboard(classCode.toUpperCase(), classPin)
      setData(dashboard)
      setView('dashboard')
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Nie udało się wczytać panelu.')
    } finally {
      setBusy(false)
    }
  }, [])

  const createClass = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const klass = await api.createClass(name.trim(), pin)
      setCreated({ code: klass.code, pin })
      setCode(klass.code)
      await load(klass.code, pin)
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Nie udało się utworzyć klasy.')
    } finally {
      setBusy(false)
    }
  }

  const removeClass = async () => {
    if (!data) return
    if (
      !window.confirm(
        `Usunąć klasę ${data.class.code} razem ze wszystkimi danymi uczniów? Tego nie da się cofnąć.`,
      )
    )
      return
    try {
      await api.deleteClass(data.class.code, pin)
      setData(null)
      setView('login')
      setError('Klasa została usunięta razem ze wszystkimi danymi.')
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Nie udało się usunąć klasy.')
    }
  }

  if (view === 'dashboard' && data) {
    const topics = ['wszystkie', ...new Set(data.misconceptions.map((m) => m.topic))]
    const visible = data.misconceptions.filter(
      (m) => topicFilter === 'wszystkie' || m.topic === topicFilter,
    )
    const visibleIds = new Set(visible.map((m) => m.id))

    return (
      <main className="screen screen-teacher">
        <header className="topbar">
          <div>
            <h1>Klasa {data.class.name}</h1>
            <p className="small muted" style={{ margin: 0 }}>
              Kod dla uczniów: <span className="mono">{data.class.code}</span> ·{' '}
              {data.students.length} {data.students.length === 1 ? 'uczeń' : 'uczniów'}
            </p>
          </div>
          <div className="topbar-actions">
            <select
              className="input"
              style={{ width: 'auto' }}
              value={topicFilter}
              onChange={(event) => setTopicFilter(event.target.value)}
              aria-label="Filtr tematów"
            >
              {topics.map((topic) => (
                <option key={topic} value={topic}>
                  {topic}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn"
              onClick={() => void downloadCsv(data.class.code, pin)}
            >
              Eksport CSV
            </button>
            <button type="button" className="btn" onClick={() => void load(data.class.code, pin)}>
              Odśwież
            </button>
            <button type="button" className="btn" onClick={onBack}>
              Wyjdź
            </button>
          </div>
        </header>

        {data.students.length === 0 ? (
          <p className="muted">
            Nikt jeszcze nie dołączył. Podaj uczniom kod <span className="mono">{data.class.code}</span>.
          </p>
        ) : (
          <div className="heatmap-wrap">
            <table className="heatmap">
              <caption className="sr-only">
                Mapa ciepła: uczniowie × błędy w rozumowaniu. Krycie komórki odpowiada
                prawdopodobieństwu opanowania.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Pseudonim</th>
                  {visible.map((m) => (
                    <th scope="col" key={m.id} title={m.title}>
                      {m.id}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.students.map((student) => (
                  <tr key={student.student_id}>
                    <th scope="row">{student.pseudonym}</th>
                    {student.cells
                      .filter((cell) => visibleIds.has(cell.misconception_id))
                      .map((cell) => (
                        <td
                          key={cell.misconception_id}
                          className={cell.p_known === null ? 'is-empty' : ''}
                          style={
                            cell.p_known === null
                              ? undefined
                              : { backgroundColor: `rgba(35, 64, 217, ${cell.p_known.toFixed(2)})` }
                          }
                          title={
                            cell.p_known === null
                              ? 'brak danych'
                              : `P(L) = ${cell.p_known.toFixed(2)}${cell.mastered ? ' · opanowane' : ''}`
                          }
                        >
                          {cell.p_known === null ? (
                            <span className="sr-only">brak danych</span>
                          ) : (
                            <>
                              <span className="sr-only">
                                {Math.round(cell.p_known * 100)} procent
                              </span>
                              {cell.mastered ? <span className="cell-check">✓</span> : null}
                            </>
                          )}
                        </td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <section className="panel teacher-summary">
          <h2 className="summary-h">Czego klasa nie wyłapuje</h2>
          <ul>
            {data.summary
              .filter((row) => visibleIds.has(row.misconception_id))
              .sort((a, b) => (a.avg_p_known ?? 0) - (b.avg_p_known ?? 0))
              .map((row) => (
                <li key={row.misconception_id}>
                  <span className="mono">{row.misconception_id}</span> {row.title} —{' '}
                  {row.students_seen === 0
                    ? 'nikt jeszcze nie próbował'
                    : `${row.students_mastered} z ${row.students_seen} opanowało, średnio ${Math.round(
                        (row.avg_p_known ?? 0) * 100,
                      )}%`}
                </li>
              ))}
          </ul>
        </section>

        <div className="teacher-footer">
          <p className="small muted">
            Widzisz mapę opanowania, nie treść rozmów uczniów. Aplikacja nie wystawia ocen.
          </p>
          <button type="button" className="linkbtn" onClick={removeClass}>
            Usuń klasę i wszystkie dane
          </button>
        </div>

        {error ? (
          <p className="small" role="alert">
            {error}
          </p>
        ) : null}
      </main>
    )
  }

  return (
    <main className="screen screen-start">
      <div className="start-card">
        <h1 className="start-title">Panel nauczyciela</h1>

        {created ? (
          <div className="panel created-box">
            <p style={{ marginTop: 0 }}>
              Klasa utworzona. Kod dla uczniów: <strong className="mono">{created.code}</strong>
            </p>
            <p className="small muted" style={{ marginBottom: 0 }}>
              Zapisz swój PIN — bez niego nie wejdziesz do panelu.
            </p>
          </div>
        ) : null}

        {view === 'login' ? (
          <form
            className="start-form"
            onSubmit={(event) => {
              event.preventDefault()
              void load(code, pin)
            }}
          >
            <div>
              <label className="label" htmlFor="tcode">
                Kod klasy
              </label>
              <input
                id="tcode"
                className="input mono"
                value={code}
                onChange={(event) => setCode(event.target.value.toUpperCase().slice(0, 6))}
                maxLength={6}
                required
                autoComplete="off"
              />
            </div>
            <div>
              <label className="label" htmlFor="tpin">
                PIN
              </label>
              <input
                id="tpin"
                className="input mono"
                type="password"
                inputMode="numeric"
                value={pin}
                onChange={(event) => setPin(event.target.value.replace(/\D/g, '').slice(0, 12))}
                required
                autoComplete="off"
              />
            </div>
            {error ? (
              <p className="small" role="alert" style={{ margin: 0 }}>
                <span className="error-mark" aria-hidden="true" /> {error}
              </p>
            ) : null}
            <div className="start-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Chwilkę…' : 'Otwórz panel'}
              </button>
              <button type="button" className="btn" onClick={() => setView('create')}>
                Utwórz klasę
              </button>
            </div>
          </form>
        ) : (
          <form className="start-form" onSubmit={createClass}>
            <div>
              <label className="label" htmlFor="cname">
                Nazwa klasy (bez nazwisk)
              </label>
              <input
                id="cname"
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value.slice(0, 40))}
                required
                placeholder="np. 2B"
              />
            </div>
            <div>
              <label className="label" htmlFor="cpin">
                PIN do panelu (4–12 cyfr)
              </label>
              <input
                id="cpin"
                className="input mono"
                type="password"
                inputMode="numeric"
                value={pin}
                onChange={(event) => setPin(event.target.value.replace(/\D/g, '').slice(0, 12))}
                minLength={4}
                required
              />
            </div>
            {error ? (
              <p className="small" role="alert" style={{ margin: 0 }}>
                <span className="error-mark" aria-hidden="true" /> {error}
              </p>
            ) : null}
            <div className="start-actions">
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Chwilkę…' : 'Utwórz klasę'}
              </button>
              <button type="button" className="btn" onClick={() => setView('login')}>
                Mam już klasę
              </button>
            </div>
          </form>
        )}

        <hr className="hr" />
        <button type="button" className="linkbtn" onClick={onBack}>
          Wróć do ekranu ucznia
        </button>
      </div>
    </main>
  )
}
