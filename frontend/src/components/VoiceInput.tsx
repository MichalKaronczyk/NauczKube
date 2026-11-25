import { Mic, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

interface Props {
  onRecorded: (blob: Blob) => void
  disabled?: boolean
  busy?: boolean
}

/** Nagranie wyjaśnienia. Audio idzie tylko do transkrypcji i nie jest zapisywane. */
export function VoiceInput({ onRecorded, disabled, busy }: Props) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const timer = useRef<number | null>(null)

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== 'undefined' &&
    'MediaRecorder' in window

  useEffect(
    () => () => {
      if (timer.current) window.clearInterval(timer.current)
      recorder.current?.stream.getTracks().forEach((track) => track.stop())
    },
    [],
  )

  const start = async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const instance = new MediaRecorder(stream)
      chunks.current = []
      instance.ondataavailable = (event) => {
        if (event.data.size) chunks.current.push(event.data)
      }
      instance.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunks.current, { type: instance.mimeType || 'audio/webm' })
        chunks.current = []
        if (blob.size > 0) onRecorded(blob)
      }
      instance.start()
      recorder.current = instance
      setRecording(true)
      setSeconds(0)
      timer.current = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    } catch {
      setError('Nie udało się włączyć mikrofonu. Możesz wpisać wyjaśnienie z klawiatury.')
    }
  }

  const stop = () => {
    recorder.current?.stop()
    recorder.current = null
    setRecording(false)
    if (timer.current) {
      window.clearInterval(timer.current)
      timer.current = null
    }
  }

  if (!supported) {
    return (
      <p className="small muted" style={{ margin: 0 }}>
        Ta przeglądarka nie obsługuje nagrywania — wpisz wyjaśnienie z klawiatury.
      </p>
    )
  }

  return (
    <div className="voice">
      <button
        type="button"
        className={recording ? 'btn' : 'btn btn-primary'}
        onClick={recording ? stop : start}
        disabled={disabled || busy}
        aria-label={recording ? 'Zakończ nagrywanie' : 'Nagraj wyjaśnienie'}
      >
        {recording ? (
          <Square size={16} strokeWidth={1.5} aria-hidden="true" />
        ) : (
          <Mic size={16} strokeWidth={1.5} aria-hidden="true" />
        )}
        <span>{recording ? `Zakończ (${seconds}s)` : busy ? 'Rozpoznaję…' : 'Powiedz'}</span>
      </button>
      {recording ? (
        <span className="small muted">Mów spokojnie, potem sprawdzisz transkrypcję.</span>
      ) : null}
      {error ? <span className="small muted">{error}</span> : null}
    </div>
  )
}
