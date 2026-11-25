import { Check, Circle } from 'lucide-react'
import { useEffect, useRef } from 'react'

import type { Emotion, Hint, Idea } from '../lib/types'
import { KubaAvatar } from './KubaAvatar'

export interface Message {
  id: number
  role: 'kuba' | 'student' | 'hint'
  text: string
  emotion?: Emotion
  level?: number
}

interface Props {
  messages: Message[]
  ideas: Idea[]
  hint: Hint | null
  thinking?: boolean
}

export function Conversation({ messages, ideas, hint, thinking }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, thinking, hint?.text])

  const required = ideas.filter((idea) => idea.required)

  return (
    <div className="conversation">
      <div className="conversation-log" role="log" aria-live="polite">
        {messages.map((message) =>
          message.role === 'kuba' ? (
            <div className="bubble bubble-kuba" key={message.id}>
              <span className="bubble-avatar">
                <KubaAvatar emotion={message.emotion ?? 'neutral'} size={32} />
              </span>
              <p>{message.text}</p>
            </div>
          ) : message.role === 'hint' ? (
            <div className="bubble bubble-hint" key={message.id}>
              <span className="bubble-title">Podpowiedź {message.level ? `${message.level}/3` : ''}</span>
              <p>{message.text}</p>
            </div>
          ) : (
            <div className="bubble bubble-student" key={message.id}>
              <p>{message.text}</p>
            </div>
          ),
        )}
        {thinking ? (
          <div className="bubble bubble-kuba is-thinking">
            <span className="bubble-avatar">
              <KubaAvatar emotion="neutral" size={32} />
            </span>
            <p aria-label="Kuba pisze">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </p>
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      {required.length ? (
        <div className="ideas" aria-label="Kluczowe idee do wytłumaczenia">
          <span className="label" style={{ marginBottom: 4 }}>
            Co Kuba musi zrozumieć
          </span>
          <ul>
            {required.map((idea) => (
              <li key={idea.id} className={idea.covered ? 'is-covered' : ''}>
                {idea.covered ? (
                  <Check size={15} strokeWidth={2} aria-hidden="true" />
                ) : (
                  <Circle size={15} strokeWidth={1.5} aria-hidden="true" />
                )}
                <span>{idea.text}</span>
                <span className="sr-only">{idea.covered ? ' — wytłumaczone' : ' — jeszcze nie'}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
