import { Eraser, Highlighter, Lightbulb, PenLine, Undo2 } from 'lucide-react'

import type { Tool } from './Board'

interface Props {
  tool: Tool
  onTool: (tool: Tool) => void
  onUndo: () => void
  onHint: () => void
  hintsUsed: number
  disabled?: boolean
}

const TOOLS: { id: Tool; label: string; icon: typeof PenLine; hint: string }[] = [
  { id: 'marker', label: 'Zakreślacz', icon: Highlighter, hint: 'Zakreśl linijkę z błędem' },
  { id: 'pen', label: 'Pióro', icon: PenLine, hint: 'Napisz poprawkę' },
  { id: 'eraser', label: 'Gumka', icon: Eraser, hint: 'Usuń swój ślad' },
]

export function Toolbar({ tool, onTool, onUndo, onHint, hintsUsed, disabled }: Props) {
  return (
    <div className="toolbar" role="toolbar" aria-label="Narzędzia tablicy">
      {TOOLS.map(({ id, label, icon: Icon, hint }) => (
        <button
          key={id}
          type="button"
          className={`tool${tool === id ? ' is-active' : ''}`}
          onClick={() => onTool(id)}
          aria-pressed={tool === id}
          title={hint}
          disabled={disabled}
        >
          <Icon size={18} strokeWidth={1.5} aria-hidden="true" />
          <span>{label}</span>
        </button>
      ))}

      <span className="toolbar-sep" aria-hidden="true" />

      <button type="button" className="tool" onClick={onUndo} title="Cofnij" disabled={disabled}>
        <Undo2 size={18} strokeWidth={1.5} aria-hidden="true" />
        <span>Cofnij</span>
      </button>

      <button
        type="button"
        className="tool"
        onClick={onHint}
        title="Poproś o podpowiedź"
        disabled={disabled || hintsUsed >= 3}
      >
        <Lightbulb size={18} strokeWidth={1.5} aria-hidden="true" />
        <span>Podpowiedź {hintsUsed > 0 ? `${hintsUsed}/3` : ''}</span>
      </button>
    </div>
  )
}
