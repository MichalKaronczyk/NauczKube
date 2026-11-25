import type { Emotion } from '../lib/types'

interface Props {
  emotion: Emotion
  size?: number
}

const LABELS: Record<Emotion, string> = {
  neutral: 'Kuba — mina neutralna',
  confused: 'Kuba — mina zdziwiona',
  aha: 'Kuba — mina „aha!”',
  happy: 'Kuba — mina zadowolona',
}

/** Rysunek liniowy w kolorze akcentu: koło, dwie kropki, kreska ust. */
export function KubaAvatar({ emotion, size = 40 }: Props) {
  return (
    <svg
      className="avatar"
      width={size}
      height={size}
      viewBox="0 0 40 40"
      role="img"
      aria-label={LABELS[emotion]}
    >
      <circle cx="20" cy="20" r="17" fill="none" stroke="currentColor" strokeWidth="1.5" />

      {emotion === 'aha' ? (
        <>
          <line x1="12" y1="14" x2="16" y2="12" stroke="currentColor" strokeWidth="1.5" />
          <line x1="28" y1="14" x2="24" y2="12" stroke="currentColor" strokeWidth="1.5" />
        </>
      ) : null}

      {emotion === 'confused' ? (
        <>
          <circle cx="14.5" cy="17" r="1.6" fill="currentColor" />
          <circle cx="25.5" cy="17" r="1.6" fill="currentColor" />
          <line x1="22" y1="12.5" x2="29" y2="14" stroke="currentColor" strokeWidth="1.5" />
        </>
      ) : (
        <>
          <circle cx="14.5" cy="17" r="1.6" fill="currentColor" />
          <circle cx="25.5" cy="17" r="1.6" fill="currentColor" />
        </>
      )}

      {emotion === 'neutral' ? (
        <line x1="14" y1="27" x2="26" y2="27" stroke="currentColor" strokeWidth="1.5" />
      ) : null}
      {emotion === 'confused' ? (
        <path d="M14 28 q6 -4 12 0" fill="none" stroke="currentColor" strokeWidth="1.5" />
      ) : null}
      {emotion === 'aha' ? (
        <circle cx="20" cy="27" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      ) : null}
      {emotion === 'happy' ? (
        <path d="M13 25 q7 6 14 0" fill="none" stroke="currentColor" strokeWidth="1.5" />
      ) : null}
    </svg>
  )
}
