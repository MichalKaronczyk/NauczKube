import katex from 'katex'
import { useMemo } from 'react'

interface Props {
  latex: string
  display?: boolean
  className?: string
}

/** Renderuje LaTeX przez KaTeX. Kolor dziedziczony po rodzicu. */
export function TeX({ latex, display = false, className }: Props) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex, {
        displayMode: display,
        throwOnError: false,
        strict: false,
        trust: false,
        output: 'html',
      })
    } catch {
      return latex
    }
  }, [latex, display])

  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />
}
