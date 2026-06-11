export const PHASE_ONE_TASKS = [
  "upload_pdf",
  "ingest_document",
  "chat_with_document",
  "generate_summary",
  "generate_quiz"
] as const;

export type PhaseOneTask = (typeof PHASE_ONE_TASKS)[number];

