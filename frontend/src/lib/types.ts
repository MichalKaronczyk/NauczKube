// Kontrakty API — odpowiadają modelom Pydantic po stronie backendu.

export type Emotion = 'neutral' | 'confused' | 'aha' | 'happy'

export type SessionState =
  | 'INTRO'
  | 'AWAIT_MARK'
  | 'DEFEND'
  | 'AWAIT_EXPLANATION'
  | 'PROBE'
  | 'ACCEPTED'
  | 'TRANSFER'
  | 'DONE'
  | 'HALTED'

export interface Line {
  index: number
  display_index: number
  latex: string
  note?: string
  code?: string
  corrected?: boolean
}

export interface Idea {
  id: string
  text: string
  required: boolean
  covered: boolean
}

export interface KubaTurn {
  text: string
  emotion: Emotion
  directive: string
  provider: string
}

export interface Hint {
  level: number
  title: string
  text: string
  highlight_lines: number[]
}

export interface IdeaVerdict {
  id: string
  required: boolean
  text: string
  covered: boolean
  evidence: string
  evidence_score: number
  model_claimed: boolean
}

export interface Evaluation {
  ideas: IdeaVerdict[]
  student_errors: string[]
  off_topic: boolean
  model_used: string
  rejected: string[]
}

export interface Correction {
  lines: Line[]
  correct_line_latex: string
  wrong_step_index: number
}

export interface TransferTask {
  task_latex: string
  lines: Line[]
  intro: KubaTurn
}

export interface Summary {
  misconception_id: string
  title: string
  topic: string
  headline: string
  ideas: Idea[]
  kuba_learned: string
  kuba_learned_latex: string
  correct_line_latex: string
  wrong_step_index: number
  hints_used: number
  wrong_marks: number
  transfer_correct: boolean | null
  p_known: number
  mastered: boolean
  outcome: string | null
  curriculum: string
}

export interface TurnView {
  session_id: string
  state: SessionState
  kuba: KubaTurn | null
  hint: Hint | null
  mark_correct: boolean | null
  evaluation: Evaluation | null
  correction: Correction | null
  transfer: TransferTask | null
  summary: Summary | null
  wellbeing_card: { title: string; body: string } | null
  ideas: Idea[]
  hints_used: number
  message: string | null
}

export interface SessionPayload {
  session_id: string
  misconception_id: string
  topic: string
  title: string
  task_latex: string
  lines: Line[]
  state: SessionState
  hints_used: number
  language: string | null
  ideas: Idea[]
}

export interface StudentOut {
  student_id: string
  pseudonym: string
  class_id: string | null
  class_code: string | null
}

export interface TopicGroup {
  topic: string
  misconceptions: { id: string; title: string; curriculum: string }[]
}

export interface MasteryEntry {
  misconception_id: string
  title: string
  topic: string
  p_known: number
  observations: number
  mastered: boolean
  seen: boolean
}

export interface StudentMap {
  student_id: string
  pseudonym?: string
  threshold: number
  entries: MasteryEntry[]
  sessions_finished?: number
}

export interface HeatmapCell {
  misconception_id: string
  p_known: number | null
  observations: number
  mastered: boolean
}

export interface Dashboard {
  class: { code: string; name: string }
  misconceptions: { id: string; title: string; topic: string }[]
  students: { student_id: string; pseudonym: string; cells: HeatmapCell[] }[]
  summary: {
    misconception_id: string
    title: string
    topic: string
    students_seen: number
    students_mastered: number
    avg_p_known: number | null
  }[]
  threshold: number
}

export interface OcrResult {
  latex: string
  confidence: number
  unreadable: boolean
  needs_confirmation: boolean
  provider: string
  message: string
}

export interface Transcription {
  text: string
  provider: string
  latency_ms: number
  editable: boolean
}

export interface AppInfo {
  app: string
  version: string
  offline_only: boolean
  disclaimer: string
  privacy: string
}
