import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Board, type BoardHandle, type Tool } from '../components/Board'
import { Conversation, type Message } from '../components/Conversation'
import { KubaLines, type LineBox } from '../components/KubaLines'
import { StepBar } from '../components/StepBar'
import { Tutorial, tutorialSeen } from '../components/Tutorial'
import { TeX } from '../components/TeX'
import { Toolbar } from '../components/Toolbar'
import { VoiceInput } from '../components/VoiceInput'
import { api, ApiError } from '../lib/api'
import type { Hint, Idea, Line, SessionPayload, TransferTask, TurnView } from '../lib/types'

interface Props {
  session: SessionPayload
  firstTurn: TurnView
  onFinished: (turn: TurnView) => void
  onLeave: () => void
}

let messageId = 0
const nextId = () => (messageId += 1)

export function BoardScreen({ session, firstTurn, onFinished, onLeave }: Props) {
  const [lines, setLines] = useState<Line[]>(session.lines)
  const [ideas, setIdeas] = useState<Idea[]>(firstTurn.ideas.length ? firstTurn.ideas : session.ideas)
  const [messages, setMessages] = useState<Message[]>(() =>
    firstTurn.kuba
      ? [{ id: nextId(), role: 'kuba', text: firstTurn.kuba.text, emotion: firstTurn.kuba.emotion }]
      : [],
  )
  const [state, setState] = useState(firstTurn.state)
  const [hint, setHint] = useState<Hint | null>(null)
  const [hintsUsed, setHintsUsed] = useState(firstTurn.hints_used)
  const [tool, setTool] = useState<Tool>('marker')
  const [markedLine, setMarkedLine] = useState<number | null>(null)
  const [dashedLine, setDashedLine] = useState<number | null>(null)
  const [lineBoxes, setLineBoxes] = useState<LineBox[]>([])
  const [thinking, setThinking] = useState(false)
  const [explanation, setExplanation] = useState('')
  const [voiceBusy, setVoiceBusy] = useState(false)
  const [transcriptionNote, setTranscriptionNote] = useState<string | null>(null)
  const [transfer, setTransfer] = useState<TransferTask | null>(null)
  const [transferChoice, setTransferChoice] = useState<number | null>(null)
  const [correctionNote, setCorrectionNote] = useState<string | null>(null)
  const [wellbeing, setWellbeing] = useState<{ title: string; body: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showTutorial, setShowTutorial] = useState(() => !tutorialSeen())

  const boardRef = useRef<BoardHandle>(null)
  const lastActivity = useRef(Date.now())
  const explanationRef = useRef<HTMLTextAreaElement>(null)

  const sessionId = session.session_id
  const awaitingMark = state === 'AWAIT_MARK' || state === 'INTRO'
  const awaitingExplanation = state === 'AWAIT_EXPLANATION' || state === 'PROBE' || state === 'DEFEND'
  const inTransfer = state === 'TRANSFER'
  const halted = state === 'HALTED'

  const pushKuba = useCallback((turn: TurnView) => {
    if (turn.kuba) {
      setMessages((all) => [
        ...all,
        { id: nextId(), role: 'kuba', text: turn.kuba!.text, emotion: turn.kuba!.emotion },
      ])
    }
    if (turn.hint) {
      setHint(turn.hint)
      setMessages((all) => [
        ...all,
        { id: nextId(), role: 'hint', text: turn.hint!.text, level: turn.hint!.level },
      ])
    }
    if (turn.ideas.length) setIdeas(turn.ideas)
    setHintsUsed(turn.hints_used)
    setState(turn.state)
    if (turn.wellbeing_card) setWellbeing(turn.wellbeing_card)
    if (turn.correction) {
      setLines(turn.correction.lines)
      setMarkedLine(null)
      setDashedLine(null)
    }
    if (turn.transfer) {
      setTransfer(turn.transfer)
      setHint(null)
      setTransferChoice(null)
      setMessages((all) => [
        ...all,
        {
          id: nextId(),
          role: 'kuba',
          text: turn.transfer!.intro.text,
          emotion: turn.transfer!.intro.emotion,
        },
      ])
    }
    if (turn.state === 'DONE' && turn.summary) onFinished(turn)
    lastActivity.current = Date.now()
  }, [onFinished])

  const act = useCallback(
    async (call: () => Promise<TurnView>) => {
      setError(null)
      setThinking(true)
      try {
        const turn = await call()
        if (turn.message) setError(turn.message)
        pushKuba(turn)
        return turn
      } catch (exception) {
        setError(exception instanceof ApiError ? exception.message : 'Brak połączenia z serwerem.')
        return null
      } finally {
        setThinking(false)
      }
    },
    [pushKuba],
  )

  // --- bramka 1: zakreślenie linijki ------------------------------------
  const markLine = useCallback(
    async (index: number) => {
      if (!awaitingMark || thinking) return
      setMarkedLine(index)
      setDashedLine(null)
      const turn = await act(() => api.mark(sessionId, index))
      if (turn && turn.mark_correct === false) {
        setMarkedLine(null)
        setDashedLine(index)
        window.setTimeout(() => setDashedLine(null), 1200)
      }
      if (turn && turn.mark_correct) {
        setTool('pen')
        window.setTimeout(() => explanationRef.current?.focus(), 200)
      }
    },
    [act, awaitingMark, sessionId, thinking],
  )

  // --- bramka 2: wyjaśnienie -------------------------------------------
  const sendExplanation = useCallback(
    async (text: string, modality: 'text' | 'voice' = 'text') => {
      const trimmed = text.trim()
      if (!trimmed || thinking) return
      setMessages((all) => [...all, { id: nextId(), role: 'student', text: trimmed }])
      setExplanation('')
      setTranscriptionNote(null)
      await act(() => api.explain(sessionId, trimmed, modality))
    },
    [act, sessionId, thinking],
  )

  const requestHint = useCallback(async () => {
    await act(() => api.hint(sessionId))
  }, [act, sessionId])

  // podpowiedź po 90 s bez ruchu
  useEffect(() => {
    if (halted || state === 'DONE') return
    const timer = window.setInterval(() => {
      if (Date.now() - lastActivity.current > 90_000 && hintsUsed < 3 && !thinking) {
        lastActivity.current = Date.now()
        void requestHint()
      }
    }, 10_000)
    return () => window.clearInterval(timer)
  }, [halted, hintsUsed, requestHint, state, thinking])

  // --- poprawka odręczna → LaTeX ---------------------------------------
  const sendCorrection = useCallback(async () => {
    const blob = await boardRef.current?.snapshot()
    if (!blob) {
      setCorrectionNote('Najpierw napisz poprawkę piórem na tablicy.')
      return
    }
    setCorrectionNote('Odczytuję zapis…')
    try {
      const { ocr } = await api.correction(sessionId, blob)
      if (ocr.unreadable) {
        setCorrectionNote(ocr.message)
        return
      }
      const confirmed = window.confirm(`Czy dobrze odczytałem?\n\n${ocr.latex}`)
      if (!confirmed) {
        setCorrectionNote('Dobrze, przepisz poprawkę z klawiatury w polu wyjaśnienia.')
        return
      }
      const { verification } = await api.confirmCorrection(sessionId, ocr.latex)
      setCorrectionNote(
        verification.accepted
          ? 'SymPy potwierdza: ta poprawka jest równoważna poprawnemu krokowi.'
          : `SymPy: ${verification.reason}`,
      )
    } catch (exception) {
      setCorrectionNote(
        exception instanceof ApiError ? exception.message : 'Nie udało się odczytać zapisu.',
      )
    }
  }, [sessionId])

  // --- zadanie transferowe ---------------------------------------------
  const resolveTransfer = useCallback(
    async (approve: boolean, lineIndex: number | null) => {
      await act(() => api.transfer(sessionId, approve, lineIndex))
    },
    [act, sessionId],
  )

  const highlight = useMemo(
    () => (inTransfer ? [] : (hint?.highlight_lines ?? [])),
    [hint, inTransfer],
  )

  if (wellbeing) {
    return (
      <main className="screen screen-wellbeing">
        <section className="panel wellbeing-card">
          <h1>{wellbeing.title}</h1>
          <p>{wellbeing.body}</p>
          <button type="button" className="btn btn-primary" onClick={onLeave}>
            Wracam później
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="screen screen-board">
      {showTutorial ? (
        <Tutorial
          topic={session.topic}
          lineCount={lines.length}
          onClose={() => setShowTutorial(false)}
        />
      ) : null}

      <header className="topbar">
        <div className="topbar-task">
          <span className="label" style={{ marginBottom: 2 }}>
            {session.topic} · {session.misconception_id}
          </span>
          <span className="task-latex">
            <TeX latex={inTransfer && transfer ? transfer.task_latex : session.task_latex} />
          </span>
        </div>
        <div className="topbar-actions">
          <button type="button" className="btn" onClick={onLeave}>
            Przerwij
          </button>
        </div>
      </header>

      <StepBar state={state} onHelp={() => setShowTutorial(true)} />

      <div className="board-layout">
        <section className="board" aria-label="Tablica">
          <Toolbar
            tool={tool}
            onTool={setTool}
            onUndo={() => boardRef.current?.undo()}
            onHint={requestHint}
            hintsUsed={hintsUsed}
            disabled={thinking || inTransfer || state === 'DONE'}
          />

          <div className="board-stack">
            <div className="board-paper">
              <KubaLines
                lines={inTransfer && transfer ? transfer.lines : lines}
                animate
                markedLine={markedLine}
                highlightLines={highlight}
                dashedLine={dashedLine}
                onBoxes={setLineBoxes}
                clickable={awaitingMark || inTransfer}
                onLineClick={(index) =>
                  inTransfer ? setTransferChoice(index) : void markLine(index)
                }
              />
              <Board
                ref={boardRef}
                tool={tool}
                lineBoxes={lineBoxes}
                onMarkLine={(index) => (inTransfer ? setTransferChoice(index) : void markLine(index))}
                onStrokeEnd={() => {
                  lastActivity.current = Date.now()
                }}
                disabled={thinking || state === 'DONE'}
              />
            </div>

            {transferChoice !== null && inTransfer ? (
              <p className="small" style={{ margin: 0 }}>
                Zakwestionowana linijka: <strong>{transferChoice + 1}</strong>
              </p>
            ) : null}

            {correctionNote ? (
              <p className="small muted" style={{ margin: 0 }}>
                {correctionNote}
              </p>
            ) : null}

            {awaitingExplanation ? (
              <button
                type="button"
                className="linkbtn"
                onClick={sendCorrection}
                style={{ alignSelf: 'flex-start' }}
              >
                Napisałem poprawkę piórem — odczytaj ją
              </button>
            ) : null}
          </div>
        </section>

        <aside className="side" aria-label="Rozmowa z Kubą">
          <Conversation messages={messages} ideas={ideas} hint={hint} thinking={thinking} />

          {awaitingExplanation ? (
            <form
              className="composer"
              onSubmit={(event) => {
                event.preventDefault()
                void sendExplanation(explanation)
              }}
            >
              <label className="label" htmlFor="explanation">
                Twoje wyjaśnienie
              </label>
              <textarea
                id="explanation"
                ref={explanationRef}
                className="input"
                value={explanation}
                onChange={(event) => {
                  setExplanation(event.target.value)
                  lastActivity.current = Date.now()
                }}
                placeholder="Napisz albo powiedz, dlaczego ten krok jest zły…"
                maxLength={4000}
                disabled={thinking}
              />
              {transcriptionNote ? (
                <p className="small muted" style={{ margin: 0 }}>
                  {transcriptionNote}
                </p>
              ) : null}
              <div className="composer-actions">
                <VoiceInput
                  busy={voiceBusy}
                  disabled={thinking}
                  onRecorded={async (blob) => {
                    setVoiceBusy(true)
                    setTranscriptionNote(null)
                    try {
                      const response = await api.explainAudio(sessionId, blob)
                      if (response.transcription.text) {
                        setExplanation(response.transcription.text)
                        setTranscriptionNote('Sprawdź transkrypcję i popraw, jeśli trzeba.')
                      } else {
                        setTranscriptionNote(
                          response.message ?? 'Nie rozpoznałem mowy. Wpisz wyjaśnienie z klawiatury.',
                        )
                      }
                    } catch (exception) {
                      setTranscriptionNote(
                        exception instanceof ApiError
                          ? exception.message
                          : 'Transkrypcja niedostępna — wpisz wyjaśnienie z klawiatury.',
                      )
                    } finally {
                      setVoiceBusy(false)
                    }
                  }}
                />
                <button type="submit" className="btn" disabled={thinking || !explanation.trim()}>
                  Wyślij
                </button>
              </div>
            </form>
          ) : null}

          {inTransfer ? (
            <div className="composer">
              <p className="small" style={{ marginTop: 0 }}>
                Kuba rozwiązał nowe zadanie. Zatwierdź albo zakreśl linijkę, z którą się nie zgadzasz.
              </p>
              <div className="composer-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void resolveTransfer(true, null)}
                  disabled={thinking}
                >
                  Dobrze zrobione
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => void resolveTransfer(false, transferChoice)}
                  disabled={thinking || transferChoice === null}
                >
                  Tu jest błąd
                </button>
              </div>
            </div>
          ) : null}

          {error ? (
            <p className="small" role="alert" style={{ margin: 0 }}>
              <span className="error-mark" aria-hidden="true" /> {error}
            </p>
          ) : null}
        </aside>
      </div>
    </main>
  )
}
