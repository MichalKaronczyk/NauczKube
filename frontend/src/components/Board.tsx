import { getStroke } from 'perfect-freehand'
import { useCallback, useEffect, useImperativeHandle, useRef, useState, type Ref } from 'react'

import type { LineBox } from './KubaLines'

export type Tool = 'pen' | 'marker' | 'eraser'

export interface BoardHandle {
  undo: () => void
  clear: () => void
  /** Wycinek tablicy (poprawka ucznia) jako PNG — do rozpoznania pisma. */
  snapshot: () => Promise<Blob | null>
  hasInk: () => boolean
}

interface Props {
  tool: Tool
  lineBoxes: LineBox[]
  /** Wywoływane, gdy zakreślenie zostanie zmapowane na numer linijki. */
  onMarkLine?: (index: number) => void
  onStrokeEnd?: () => void
  disabled?: boolean
  ref?: Ref<BoardHandle>
}

interface Point {
  x: number
  y: number
  pressure: number
}

interface Stroke {
  tool: Tool
  points: Point[]
}

const PEN_OPTIONS = {
  size: 3.2,
  thinning: 0.6,
  smoothing: 0.6,
  streamline: 0.5,
  simulatePressure: true,
  last: true,
}

const MARKER_OPTIONS = {
  size: 22,
  thinning: 0,
  smoothing: 0.7,
  streamline: 0.6,
  simulatePressure: false,
  last: true,
}

const ERASER_RADIUS = 16
/** Minimalne pokrycie linijki zakreśleniem, żeby uznać ją za wskazaną. */
const OVERLAP_THRESHOLD = 0.22

function toPathData(stroke: number[][]): string {
  if (!stroke.length) return ''
  const d = stroke.reduce(
    (acc, [x0, y0], index, array) => {
      const [x1, y1] = array[(index + 1) % array.length]
      acc.push(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2)
      return acc
    },
    ['M', ...stroke[0], 'Q'] as (string | number)[],
  )
  d.push('Z')
  return d.join(' ')
}

function strokeBounds(points: Point[]) {
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  return {
    left: Math.min(...xs),
    right: Math.max(...xs),
    top: Math.min(...ys),
    bottom: Math.max(...ys),
  }
}

/** Mapowanie zakreślenia na numer linijki: przecięcie obrysów, bez AI. */
export function matchLine(points: Point[], boxes: LineBox[]): number | null {
  if (points.length < 2 || !boxes.length) return null
  const bounds = strokeBounds(points)
  const strokeWidth = bounds.right - bounds.left
  const strokeHeight = bounds.bottom - bounds.top

  let best: { index: number; score: number } | null = null

  for (const box of boxes) {
    const overlapWidth = Math.min(bounds.right, box.right) - Math.max(bounds.left, box.left)
    const overlapHeight = Math.min(bounds.bottom, box.bottom) - Math.max(bounds.top, box.top)
    if (overlapWidth <= 0 || overlapHeight <= 0) continue

    const boxHeight = box.bottom - box.top
    const boxWidth = Math.max(1, box.right - box.left)
    const overlapArea = overlapWidth * overlapHeight
    const strokeArea = Math.max(1, strokeWidth * Math.max(strokeHeight, 1))
    const boxArea = Math.max(1, boxWidth * boxHeight)

    // ile zakreślenia leży na tej linijce i ile linijki jest zakreślone
    const coverOfBox = overlapArea / boxArea
    const coverOfStroke = overlapArea / strokeArea
    // ile punktów pióra wylądowało wewnątrz prostokąta linijki
    const inside =
      points.filter((p) => p.x >= box.left && p.x <= box.right && p.y >= box.top && p.y <= box.bottom)
        .length / points.length

    const score = Math.max(coverOfBox, coverOfStroke * 0.8, inside)
    if (score >= OVERLAP_THRESHOLD && (!best || score > best.score)) {
      best = { index: box.index, score }
    }
  }
  return best ? best.index : null
}

export function Board({ tool, lineBoxes, onMarkLine, onStrokeEnd, disabled, ref }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [current, setCurrent] = useState<Point[]>([])
  const drawing = useRef(false)
  const pointerId = useRef<number | null>(null)

  useImperativeHandle(ref, () => ({
    undo: () => setStrokes((all) => all.slice(0, -1)),
    clear: () => setStrokes([]),
    hasInk: () => strokes.some((stroke) => stroke.tool === 'pen'),
    snapshot: async () => renderSnapshot(containerRef.current, strokes),
  }))

  const position = useCallback((event: React.PointerEvent): Point => {
    const rect = containerRef.current!.getBoundingClientRect()
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      // nacisk rysika; mysz i palec raportują 0 lub 0.5
      pressure: event.pressure > 0 ? event.pressure : 0.5,
    }
  }, [])

  const onPointerDown = (event: React.PointerEvent) => {
    if (disabled) return
    if (event.pointerType === 'mouse' && event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    pointerId.current = event.pointerId
    drawing.current = true
    const point = position(event)

    if (tool === 'eraser') {
      eraseAt(point)
      return
    }
    setCurrent([point])
  }

  const onPointerMove = (event: React.PointerEvent) => {
    if (!drawing.current || pointerId.current !== event.pointerId) return
    const point = position(event)
    if (tool === 'eraser') {
      eraseAt(point)
      return
    }
    setCurrent((points) => [...points, point])
  }

  const onPointerUp = (event: React.PointerEvent) => {
    if (!drawing.current || pointerId.current !== event.pointerId) return
    drawing.current = false
    pointerId.current = null

    if (tool === 'eraser') {
      onStrokeEnd?.()
      return
    }

    const points = current
    setCurrent([])
    if (points.length < 2) return

    if (tool === 'marker') {
      const index = matchLine(points, lineBoxes)
      if (index !== null) {
        onMarkLine?.(index)
        // zakreślenie zostaje narysowane tylko jako chwilowe podświetlenie
        setStrokes((all) => [...all, { tool, points }])
        window.setTimeout(() => setStrokes((all) => all.filter((s) => s.points !== points)), 600)
        return
      }
      // brak trafienia w linijkę — ślad znika, żeby tablica została czysta
      return
    }

    setStrokes((all) => [...all, { tool, points }])
    onStrokeEnd?.()
  }

  const eraseAt = (point: Point) => {
    setStrokes((all) =>
      all.filter(
        (stroke) =>
          !stroke.points.some(
            (p) => Math.hypot(p.x - point.x, p.y - point.y) <= ERASER_RADIUS,
          ),
      ),
    )
  }

  useEffect(() => {
    const prevent = (event: Event) => {
      if (drawing.current) event.preventDefault()
    }
    document.addEventListener('touchmove', prevent, { passive: false })
    return () => document.removeEventListener('touchmove', prevent)
  }, [])

  const allStrokes = current.length ? [...strokes, { tool, points: current }] : strokes

  return (
    <div
      ref={containerRef}
      className={`board-surface${disabled ? ' is-disabled' : ''}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onPointerLeave={onPointerUp}
      style={{ touchAction: 'none' }}
      data-tool={tool}
    >
      <svg className="board-ink" aria-hidden="true">
        {allStrokes.map((stroke, index) => (
          <path
            key={index}
            d={toPathData(
              getStroke(
                stroke.points.map((p) => [p.x, p.y, p.pressure]),
                stroke.tool === 'marker' ? MARKER_OPTIONS : PEN_OPTIONS,
              ),
            )}
            className={stroke.tool === 'marker' ? 'ink-marker' : 'ink-pen'}
          />
        ))}
      </svg>
    </div>
  )
}

/** Rysuje ślady ucznia na białym tle i zwraca PNG (bez pisma Kuby). */
async function renderSnapshot(container: HTMLDivElement | null, strokes: Stroke[]): Promise<Blob | null> {
  if (!container) return null
  const pen = strokes.filter((stroke) => stroke.tool === 'pen')
  if (!pen.length) return null

  const all = pen.flatMap((stroke) => stroke.points)
  const bounds = strokeBounds(all)
  const padding = 18
  const width = Math.max(32, Math.ceil(bounds.right - bounds.left + padding * 2))
  const height = Math.max(32, Math.ceil(bounds.bottom - bounds.top + padding * 2))

  const canvas = document.createElement('canvas')
  const scale = 2
  canvas.width = width * scale
  canvas.height = height * scale
  const context = canvas.getContext('2d')
  if (!context) return null
  context.scale(scale, scale)
  context.fillStyle = '#FFFFFF'
  context.fillRect(0, 0, width, height)
  context.fillStyle = '#111111'

  for (const stroke of pen) {
    const outline = getStroke(
      stroke.points.map((p) => [p.x - bounds.left + padding, p.y - bounds.top + padding, p.pressure]),
      PEN_OPTIONS,
    )
    if (!outline.length) continue
    context.beginPath()
    context.moveTo(outline[0][0], outline[0][1])
    for (const [x, y] of outline.slice(1)) context.lineTo(x, y)
    context.closePath()
    context.fill()
  }

  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), 'image/png'))
}
