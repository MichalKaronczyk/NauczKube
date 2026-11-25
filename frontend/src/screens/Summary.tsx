import { Check, Circle } from 'lucide-react'

import { KubaAvatar } from '../components/KubaAvatar'
import { TeX } from '../components/TeX'
import type { Summary as SummaryData } from '../lib/types'

interface Props {
  summary: SummaryData
  pseudonym: string
  onAgain: () => void
  onTopics: () => void
}

export function Summary({ summary, pseudonym, onAgain, onTopics }: Props) {
  const required = summary.ideas.filter((idea) => idea.required)
  const extra = summary.ideas.filter((idea) => !idea.required)
  const percent = Math.round(summary.p_known * 100)

  return (
    <main className="screen screen-summary">
      <header className="topbar">
        <div>
          <h1>{summary.headline}</h1>
          <p className="small muted" style={{ margin: 0 }}>
            {summary.topic} · {summary.misconception_id} {summary.title} · {pseudonym}
          </p>
        </div>
      </header>

      <div className="summary-grid">
        <section className="panel summary-block">
          <h2 className="summary-h">Co wytłumaczyłeś</h2>
          <ul className="summary-ideas">
            {required.map((idea) => (
              <li key={idea.id} className={idea.covered ? 'is-covered' : ''}>
                {idea.covered ? (
                  <Check size={16} strokeWidth={2} aria-hidden="true" />
                ) : (
                  <Circle size={16} strokeWidth={1.5} aria-hidden="true" />
                )}
                <span>{idea.text}</span>
              </li>
            ))}
            {extra.map((idea) => (
              <li key={idea.id} className={`is-extra${idea.covered ? ' is-covered' : ''}`}>
                {idea.covered ? (
                  <Check size={16} strokeWidth={2} aria-hidden="true" />
                ) : (
                  <Circle size={16} strokeWidth={1.5} aria-hidden="true" />
                )}
                <span>
                  {idea.text} <span className="muted small">(dodatkowa)</span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel summary-block">
          <h2 className="summary-h">Czego się dziś nauczyłem</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            {summary.kuba_learned}
          </p>
          <div className="summary-kuba">
            <KubaAvatar emotion="happy" size={40} />
            <p className="kuba-quote">
              {summary.kuba_learned_latex ? (
                <TeX latex={summary.kuba_learned_latex} />
              ) : (
                `„${summary.kuba_learned}”`
              )}
            </p>
          </div>
          <p className="small muted" style={{ marginBottom: 4 }}>
            Poprawiona linijka {summary.wrong_step_index + 1}:
          </p>
          <p className="summary-correct">
            <TeX latex={summary.correct_line_latex} />
          </p>
        </section>

        <section className="panel summary-block">
          <h2 className="summary-h">Mapa rozumienia</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            Prawdopodobieństwo opanowania tego błędu (model BKT)
          </p>
          <div className="meter" role="img" aria-label={`Opanowanie ${percent} procent`}>
            <span className="meter-fill" style={{ width: `${percent}%` }} />
          </div>
          <p className="meter-value">
            {percent}%{summary.mastered ? ' · opanowane ✓' : ''}
          </p>
          <hr className="hr" />
          <dl className="summary-stats">
            <div>
              <dt>Podpowiedzi</dt>
              <dd>{summary.hints_used} / 3</dd>
            </div>
            <div>
              <dt>Nietrafione wskazania</dt>
              <dd>{summary.wrong_marks}</dd>
            </div>
            <div>
              <dt>Zadanie transferowe</dt>
              <dd>
                {summary.transfer_correct === null
                  ? '—'
                  : summary.transfer_correct
                    ? 'ocenione trafnie ✓'
                    : 'ocenione nietrafnie'}
              </dd>
            </div>
          </dl>
          <p className="small muted">{summary.curriculum}</p>
        </section>
      </div>

      <div className="summary-actions">
        <button type="button" className="btn btn-primary" onClick={onAgain}>
          Jeszcze raz, inne liczby
        </button>
        <button type="button" className="btn" onClick={onTopics}>
          Wybierz inny temat
        </button>
      </div>

      <p className="small muted">
        Aplikacja nie wystawia ocen szkolnych. Mapa rozumienia służy do diagnozy.
      </p>
    </main>
  )
}
