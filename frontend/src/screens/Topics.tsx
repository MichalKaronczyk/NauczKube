import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { StudentMap, StudentOut, TopicGroup } from '../lib/types'

interface Props {
  student: StudentOut
  onStart: (misconceptionId: string) => void
  onBack: () => void
  busy?: boolean
}

export function Topics({ student, onStart, onBack, busy }: Props) {
  const [topics, setTopics] = useState<TopicGroup[]>([])
  const [mastery, setMastery] = useState<StudentMap | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    Promise.all([api.topics(), api.studentMap(student.student_id)])
      .then(([topicsResponse, map]) => {
        if (!active) return
        setTopics(topicsResponse.topics)
        setMastery(map)
      })
      .catch(() => active && setError('Nie udało się wczytać tematów.'))
    return () => {
      active = false
    }
  }, [student.student_id])

  const score = (id: string) =>
    mastery?.entries.find((entry) => entry.misconception_id === id) ?? null

  return (
    <main className="screen screen-topics">
      <header className="topbar">
        <div>
          <h1>Tematy</h1>
          <p className="small muted" style={{ margin: 0 }}>
            {student.pseudonym}
            {student.class_code ? ` · klasa ${student.class_code}` : ' · tryb solo'}
          </p>
        </div>
        <button type="button" className="btn" onClick={onBack}>
          Wyjdź
        </button>
      </header>

      {error ? <p role="alert">{error}</p> : null}

      <p className="topics-lead">
        Wybierz błąd, który chcesz przećwiczyć. Kuba rozwiąże zadanie z tego tematu i popełni
        <strong> właśnie ten błąd</strong> w jednej linijce — Twoim zadaniem będzie go znaleźć
        i wytłumaczyć mu, dlaczego to źle.
      </p>

      <div className="topics-list">
        {topics.map((group) => (
          <section className="panel topic-group" key={group.topic}>
            <h2 className="topic-title">{group.topic}</h2>
            <ul>
              {group.misconceptions.map((item) => {
                const entry = score(item.id)
                const percent = Math.round((entry?.p_known ?? 0) * 100)
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="topic-row"
                      onClick={() => onStart(item.id)}
                      disabled={busy}
                    >
                      <span className="topic-row-main">
                        <span className="topic-row-id mono">{item.id}</span>
                        <span className="topic-row-name">{item.title}</span>
                        {entry?.mastered ? (
                          <span className="topic-row-done" aria-label="opanowane">
                            ✓
                          </span>
                        ) : null}
                      </span>
                      <span className="topic-meter" aria-hidden="true">
                        <span className="topic-meter-fill" style={{ width: `${percent}%` }} />
                      </span>
                      <span className="sr-only">Opanowanie {percent} procent</span>
                      <span className="topic-row-curriculum small muted">{item.curriculum}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
      </div>

      <p className="small muted">
        Pasek pod nazwą pokazuje, na ile już opanowałeś dany błąd (model BKT) — to diagnoza,
        a nie ocena szkolna. Zaczynasz od dowolnego tematu, kolejność nie ma znaczenia.
      </p>
    </main>
  )
}
