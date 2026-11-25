import { useEffect, useRef } from 'react'

const STORAGE_KEY = 'naucz-kube:tutorial-widziany'

export function tutorialSeen(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function markTutorialSeen(): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, '1')
  } catch {
    /* tryb prywatny — trudno, pokaże się jeszcze raz */
  }
}

interface Props {
  topic: string
  /** Ile linijek ma rozwiązanie — „jedna z 4” jest konkretniejsze niż „jedna”. */
  lineCount: number
  onClose: () => void
}

const STEPS = [
  {
    title: 'Znajdź błędną linijkę',
    body:
      'Kuba rozwiązał zadanie i w jednej linijce popełnił błąd — nie rachunkowy, tylko w regule, ' +
      'której użył. Weź zakreślacz i zakreśl tę linijkę (możesz też po prostu w nią kliknąć).',
  },
  {
    title: 'Wytłumacz, dlaczego to źle',
    body:
      'Napisz albo powiedz własnymi słowami, na czym polega błąd. Samo „to jest źle” nie wystarczy — ' +
      'Kuba szczerze wierzy w swoją regułę i będzie się bronił.',
  },
  {
    title: 'Odpowiadaj na pytania Kuby',
    body:
      'Kuba dopytuje, aż padną wszystkie kluczowe idee z listy po prawej. Dopiero wtedy mówi „aha”, ' +
      'poprawia linijkę i rozwiązuje nowe zadanie, które Ty oceniasz.',
  },
]

export function Tutorial({ topic, lineCount, onClose }: Props) {
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    buttonRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="overlay" role="presentation" onClick={onClose}>
      <div
        className="panel tutorial"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tutorial-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="tutorial-title" className="tutorial-title">
          Jak to działa
        </h2>
        <p className="tutorial-lead">
          Temat: <strong>{topic}</strong>. W {lineCount} linijkach rozwiązania Kuby jest{' '}
          <strong>dokładnie jeden</strong> błędny krok. Twoim zadaniem nie jest rozwiązać zadanie —
          tylko nauczyć Kubę.
        </p>

        <ol className="tutorial-steps">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <span className="tutorial-step-no" aria-hidden="true">
                {index + 1}
              </span>
              <span>
                <strong>{step.title}</strong>
                <br />
                {step.body}
              </span>
            </li>
          ))}
        </ol>

        <p className="small muted tutorial-hint">
          Nie wiesz, od czego zacząć? Kliknij <strong>Podpowiedź</strong> — dostaniesz zawężenie do
          kilku linijek, potem test liczbowy. Poprawnej reguły nie dostaniesz: masz ją wymyślić sam.
        </p>

        <div className="tutorial-actions">
          <button
            ref={buttonRef}
            type="button"
            className="btn btn-primary"
            onClick={() => {
              markTutorialSeen()
              onClose()
            }}
          >
            Rozumiem, zaczynamy
          </button>
          <button type="button" className="linkbtn" onClick={onClose}>
            Pokaż jeszcze raz następnym razem
          </button>
        </div>
      </div>
    </div>
  )
}
