import { useCallback, useEffect, useState } from 'react'

import { api, ApiError, SERVER_DOWN } from './lib/api'
import type { AppInfo, SessionPayload, StudentOut, Summary as SummaryData, TurnView } from './lib/types'
import { BoardScreen } from './screens/BoardScreen'
import { Start } from './screens/Start'
import { Summary } from './screens/Summary'
import { Teacher } from './screens/Teacher'
import { Topics } from './screens/Topics'

type Screen = 'start' | 'topics' | 'board' | 'summary' | 'teacher'

export function App() {
  const [screen, setScreen] = useState<Screen>('start')
  const [info, setInfo] = useState<AppInfo | null>(null)
  const [student, setStudent] = useState<StudentOut | null>(null)
  const [session, setSession] = useState<SessionPayload | null>(null)
  const [firstTurn, setFirstTurn] = useState<TurnView | null>(null)
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [lastMisconception, setLastMisconception] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [serverDown, setServerDown] = useState(false)

  const checkServer = useCallback(() => {
    api
      .info()
      .then((value) => {
        setInfo(value)
        setServerDown(false)
      })
      .catch(() => setServerDown(true))
  }, [])

  useEffect(checkServer, [checkServer])

  // dopóki serwer nie odpowiada, sprawdzamy co 5 s — baner zniknie sam
  useEffect(() => {
    if (!serverDown) return
    const timer = window.setInterval(checkServer, 5000)
    return () => window.clearInterval(timer)
  }, [serverDown, checkServer])

  const startSession = useCallback(
    async (misconceptionId: string) => {
      if (!student) return
      setBusy(true)
      setError(null)
      try {
        const response = await api.startSession(student.student_id, misconceptionId)
        setSession(response.session)
        setFirstTurn(response.turn)
        setLastMisconception(misconceptionId)
        setScreen('board')
      } catch (exception) {
        setError(
          exception instanceof ApiError ? exception.message : 'Nie udało się rozpocząć sesji.',
        )
      } finally {
        setBusy(false)
      }
    },
    [student],
  )

  return (
    <>
      {serverDown ? (
        <div className="banner banner-down" role="alert">
          <span>{SERVER_DOWN}</span>
          <button type="button" className="linkbtn" onClick={checkServer}>
            Sprawdź ponownie
          </button>
        </div>
      ) : null}

      {error ? (
        <div className="banner" role="alert">
          {error}
          <button type="button" className="linkbtn" onClick={() => setError(null)}>
            Zamknij
          </button>
        </div>
      ) : null}

      {screen === 'start' ? (
        <Start
          info={info}
          onReady={(created) => {
            setStudent(created)
            setScreen('topics')
          }}
          onTeacher={() => setScreen('teacher')}
        />
      ) : null}

      {screen === 'teacher' ? <Teacher onBack={() => setScreen('start')} /> : null}

      {screen === 'topics' && student ? (
        <Topics
          student={student}
          busy={busy}
          onStart={(id) => void startSession(id)}
          onBack={() => {
            setStudent(null)
            setScreen('start')
          }}
        />
      ) : null}

      {screen === 'board' && session && firstTurn ? (
        <BoardScreen
          key={session.session_id}
          session={session}
          firstTurn={firstTurn}
          onFinished={(turn) => {
            if (turn.summary) {
              setSummary(turn.summary)
              window.setTimeout(() => setScreen('summary'), 2200)
            }
          }}
          onLeave={() => setScreen('topics')}
        />
      ) : null}

      {screen === 'summary' && summary && student ? (
        <Summary
          summary={summary}
          pseudonym={student.pseudonym}
          onAgain={() => lastMisconception && void startSession(lastMisconception)}
          onTopics={() => setScreen('topics')}
        />
      ) : null}
    </>
  )
}
