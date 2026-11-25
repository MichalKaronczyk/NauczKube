// Klient API. Klucze AI zostają na serwerze — przeglądarka ich nigdy nie widzi.

import type {
  AppInfo,
  Dashboard,
  OcrResult,
  SessionPayload,
  StudentMap,
  StudentOut,
  TopicGroup,
  Transcription,
  TurnView,
} from './types'

// Zawsze ścieżka relatywna: w dev proxy Vite, w produkcji ten sam serwer FastAPI.
const BASE = ''

export class ApiError extends Error {
  status: number
  /** true, gdy żądanie w ogóle nie dotarło do serwera (serwer nie działa, brak sieci). */
  offline: boolean

  constructor(message: string, status: number, offline = false) {
    super(message)
    this.status = status
    this.offline = offline
  }
}

export const SERVER_DOWN =
  'Serwer aplikacji nie odpowiada. Uruchom go poleceniem „docker compose up” ' +
  'albo „uvicorn app.main:app” w katalogu backend i spróbuj ponownie.'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}/api${path}`, {
      headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
      ...init,
    })
  } catch {
    // fetch rzuca TypeError, gdy nie ma połączenia — bez tego użytkownik
    // widziałby tylko „coś poszło nie tak”
    throw new ApiError(SERVER_DOWN, 0, true)
  }

  if (!response.ok) {
    let detail = `Błąd ${response.status}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        // Pydantic dokleja „Value error, ” — uczeń nie musi tego widzieć
        detail = String(body.detail[0].msg).replace(/^Value error,\s*/i, '')
      }
    } catch {
      /* odpowiedź bez JSON */
    }
    throw new ApiError(detail, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  info: () => request<AppInfo>('/info'),
  health: () => request<Record<string, unknown>>('/health'),
  topics: () => request<{ topics: TopicGroup[] }>('/topics'),

  createStudent: (pseudonym: string, classCode?: string) =>
    request<StudentOut>('/students', {
      method: 'POST',
      body: JSON.stringify({ pseudonym, class_code: classCode || null }),
    }),

  startSession: (studentId: string, misconceptionId?: string, topic?: string) =>
    request<{ session: SessionPayload; turn: TurnView }>('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        student_id: studentId,
        misconception_id: misconceptionId ?? null,
        topic: topic ?? null,
      }),
    }),

  mark: (sessionId: string, lineIndex: number) =>
    request<TurnView>(`/sessions/${sessionId}/mark`, {
      method: 'POST',
      body: JSON.stringify({ line_index: lineIndex }),
    }),

  explain: (sessionId: string, text: string, modality: 'text' | 'voice' | 'ink' = 'text') =>
    request<TurnView>(`/sessions/${sessionId}/explain`, {
      method: 'POST',
      body: JSON.stringify({ text, modality }),
    }),

  explainAudio: (sessionId: string, blob: Blob) => {
    const form = new FormData()
    form.append('audio', blob, 'nagranie.webm')
    form.append('autosend', 'false')
    return request<{ transcription: Transcription; turn: TurnView | null; message?: string }>(
      `/sessions/${sessionId}/explain-audio`,
      { method: 'POST', body: form },
    )
  },

  correction: (sessionId: string, blob: Blob) => {
    const form = new FormData()
    form.append('image', blob, 'poprawka.png')
    return request<{ ocr: OcrResult }>(`/sessions/${sessionId}/correction`, {
      method: 'POST',
      body: form,
    })
  },

  confirmCorrection: (sessionId: string, latex: string) =>
    request<{ verification: { accepted: boolean; reason: string; parsed: string | null; expected: string | null } }>(
      `/sessions/${sessionId}/correction/confirm`,
      { method: 'POST', body: JSON.stringify({ latex }) },
    ),

  transfer: (sessionId: string, approve: boolean, lineIndex?: number | null) =>
    request<TurnView>(`/sessions/${sessionId}/transfer`, {
      method: 'POST',
      body: JSON.stringify({ approve, line_index: lineIndex ?? null }),
    }),

  hint: (sessionId: string) =>
    request<TurnView>(`/sessions/${sessionId}/hint`, { method: 'POST' }),

  studentMap: (studentId: string) => request<StudentMap>(`/students/${studentId}/map`),

  createClass: (name: string, pin: string) =>
    request<{ class_id: string; code: string; name: string }>('/classes', {
      method: 'POST',
      body: JSON.stringify({ name, pin }),
    }),

  dashboard: (code: string, pin: string) =>
    request<Dashboard>(`/classes/${code}/dashboard`, { headers: { 'X-Teacher-Pin': pin } }),

  exportCsvUrl: (code: string) => `${BASE}/api/classes/${code}/export.csv`,

  deleteClass: (code: string, pin: string) =>
    request<{ deleted: boolean }>(`/classes/${code}`, {
      method: 'DELETE',
      headers: { 'X-Teacher-Pin': pin },
    }),
}

export async function downloadCsv(code: string, pin: string): Promise<void> {
  let response: Response
  try {
    response = await fetch(api.exportCsvUrl(code), { headers: { 'X-Teacher-Pin': pin } })
  } catch {
    throw new ApiError(SERVER_DOWN, 0, true)
  }
  if (!response.ok) throw new ApiError('Nie udało się wyeksportować danych.', response.status)
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `klasa-${code}.csv`
  anchor.click()
  URL.revokeObjectURL(url)
}
