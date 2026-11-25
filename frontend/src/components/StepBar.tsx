import type { SessionState } from '../lib/types'

const STEPS = [
  { key: 'find', label: 'Znajdź błędną linijkę' },
  { key: 'explain', label: 'Wytłumacz, dlaczego to źle' },
  { key: 'check', label: 'Oceń nowe zadanie Kuby' },
] as const

/** Instrukcja dopasowana do tego, co uczeń ma zrobić teraz. */
const INSTRUCTION: Record<string, string> = {
  find: 'Zakreśl zakreślaczem linijkę, w której Kuba użył złej reguły (możesz w nią kliknąć).',
  explain: 'Napisz lub powiedz własnymi słowami, na czym polega błąd. Kuba będzie dopytywał.',
  check: 'Kuba rozwiązał nowe zadanie. Zatwierdź je albo zakreśl linijkę, z którą się nie zgadzasz.',
  done: 'Gotowe — za chwilę zobaczysz podsumowanie.',
}

function currentStep(state: SessionState): 'find' | 'explain' | 'check' | 'done' {
  if (state === 'INTRO' || state === 'AWAIT_MARK') return 'find'
  if (state === 'DEFEND' || state === 'AWAIT_EXPLANATION' || state === 'PROBE') return 'explain'
  if (state === 'TRANSFER' || state === 'ACCEPTED') return 'check'
  return 'done'
}

interface Props {
  state: SessionState
  onHelp: () => void
}

export function StepBar({ state, onHelp }: Props) {
  const step = currentStep(state)
  const activeIndex = STEPS.findIndex((s) => s.key === step)

  return (
    <div className="stepbar">
      <ol className="stepbar-steps" aria-label="Etapy sesji">
        {STEPS.map((item, index) => {
          const done = activeIndex > index
          const active = activeIndex === index
          return (
            <li
              key={item.key}
              className={`stepbar-step${active ? ' is-active' : ''}${done ? ' is-done' : ''}`}
              aria-current={active ? 'step' : undefined}
            >
              <span className="stepbar-no" aria-hidden="true">
                {done ? '✓' : index + 1}
              </span>
              <span className="stepbar-label">{item.label}</span>
            </li>
          )
        })}
      </ol>

      <p className="stepbar-instruction" aria-live="polite">
        {INSTRUCTION[step]}
        <button type="button" className="linkbtn stepbar-help" onClick={onHelp}>
          Jak to działa?
        </button>
      </p>
    </div>
  )
}
