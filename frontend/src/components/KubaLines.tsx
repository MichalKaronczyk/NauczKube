import { useEffect, useMemo, useRef, useState } from 'react'

import type { Line } from '../lib/types'
import { TeX } from './TeX'

const MS_PER_CHAR = 40

export interface LineBox {
  index: number
  top: number
  left: number
  right: number
  bottom: number
}

interface Props {
  lines: Line[]
  /** Linijki pojawiają się kolejno jak pismo odręczne. */
  animate?: boolean
  markedLine?: number | null
  highlightLines?: number[]
  dashedLine?: number | null
  /** Zgłasza prostokąty linijek (do mapowania zakreślenia na numer linijki). */
  onBoxes?: (boxes: LineBox[]) => void
  onLineClick?: (index: number) => void
  clickable?: boolean
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
}

export function KubaLines({
  lines,
  animate = true,
  markedLine = null,
  highlightLines = [],
  dashedLine = null,
  onBoxes,
  onLineClick,
  clickable = false,
}: Props) {
  const reduced = useMemo(prefersReducedMotion, [])
  const [visible, setVisible] = useState(animate && !reduced ? 0 : lines.length)
  const containerRef = useRef<HTMLOListElement>(null)
  const itemRefs = useRef<(HTMLLIElement | null)[]>([])
  const signature = lines.map((line) => line.latex).join('|')

  useEffect(() => {
    if (!animate || reduced) {
      setVisible(lines.length)
      return
    }
    setVisible(0)
    let cancelled = false
    let index = 0

    const step = () => {
      if (cancelled) return
      index += 1
      setVisible(index)
      if (index < lines.length) {
        const chars = Math.max(8, lines[index - 1]?.latex.length ?? 10)
        window.setTimeout(step, Math.min(1400, chars * MS_PER_CHAR))
      }
    }
    const first = window.setTimeout(step, 150)
    return () => {
      cancelled = true
      window.clearTimeout(first)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, animate, reduced])

  // prostokąty linijek dla zakreślacza
  useEffect(() => {
    if (!onBoxes) return
    const measure = () => {
      const container = containerRef.current
      if (!container) return
      const base = container.getBoundingClientRect()
      const boxes: LineBox[] = []
      itemRefs.current.forEach((element, index) => {
        if (!element) return
        const rect = element.getBoundingClientRect()
        boxes.push({
          index,
          top: rect.top - base.top,
          left: rect.left - base.left,
          right: rect.right - base.left,
          bottom: rect.bottom - base.top,
        })
      })
      onBoxes(boxes)
    }
    measure()
    const observer = new ResizeObserver(measure)
    if (containerRef.current) observer.observe(containerRef.current)
    window.addEventListener('resize', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, visible])

  return (
    <ol className="kuba-lines" ref={containerRef}>
      {lines.map((line, index) => {
        const shown = index < visible
        // Kod programu nie jest pismem odręcznym — czcionka o stałej szerokości
        // i brak animacji „pisania”, żeby wcięcia i nawiasy były czytelne.
        const isCode = Boolean(line.code)
        const chars = Math.max(8, line.latex.length)
        const classes = [
          'kuba-line',
          isCode ? 'is-code' : '',
          shown ? 'is-shown' : 'is-hidden',
          markedLine === index ? 'is-marked' : '',
          highlightLines.includes(index) ? 'is-highlighted' : '',
          dashedLine === index ? 'is-dashed' : '',
          line.corrected ? 'is-corrected' : '',
          clickable ? 'is-clickable' : '',
        ]
          .filter(Boolean)
          .join(' ')

        return (
          <li
            key={`${index}-${line.latex}`}
            ref={(element) => {
              itemRefs.current[index] = element
            }}
            className={classes}
            style={
              shown && animate && !reduced && !isCode
                ? { ['--write-duration' as string]: `${Math.min(1400, chars * MS_PER_CHAR)}ms` }
                : undefined
            }
            onClick={clickable && shown ? () => onLineClick?.(index) : undefined}
            onKeyDown={
              clickable && shown
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onLineClick?.(index)
                    }
                  }
                : undefined
            }
            tabIndex={clickable && shown ? 0 : -1}
            role={clickable ? 'button' : undefined}
            aria-label={clickable ? `Zakreśl linijkę ${line.display_index}` : undefined}
          >
            <span className="kuba-line-no" aria-hidden="true">
              {line.display_index}
            </span>
            <span className="kuba-line-body">
              {isCode ? (
                <code className="kuba-code">{line.code}</code>
              ) : (
                <TeX latex={line.latex} />
              )}
              {line.note ? <span className="kuba-line-note">{line.note}</span> : null}
            </span>
            {markedLine === index ? (
              <span className="sr-only">zakreślona</span>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
