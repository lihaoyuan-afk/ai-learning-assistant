export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export type DocumentRead = {
  id: string;
  title: string;
  file_type: string;
  status: DocumentStatus;
  file_path?: string | null;
  summary?: string | null;
  created_at: string;
};

export type SourceChunk = {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  page_number?: number | null;
  section_title?: string | null;
  score?: number | null;
};

export type DocumentListResponse = {
  documents: DocumentRead[];
};

export type DocumentIngestResponse = {
  document: DocumentRead;
  message: string;
};

export type ChatResponse = {
  answer: string;
  sources: SourceChunk[];
};

export type SummaryResponse = {
  document_id: string;
  summary: string;
};

export type QuizQuestion = {
  id: string;
  type: string;
  question: string;
  options: string[];
  answer: string;
  explanation: string;
  knowledge_point?: string | null;
};

export type QuizResponse = {
  id: string;
  document_id: string;
  title: string;
  difficulty: string;
  questions: QuizQuestion[];
};

export type QuizAttemptRequest = {
  answers: Record<string, string>;
};

export type QuestionResult = {
  question_id: string;
  is_correct: boolean;
  requires_review: boolean;
  user_answer: string;
  correct_answer: string;
  explanation: string;
};

export type QuizAttemptResponse = {
  attempt_id: string;
  quiz_id: string;
  score: number;
  total: number;
  results: QuestionResult[];
};

export type MasteryItem = {
  knowledge_point: string;
  mastery_score: number;
  correct_count: number;
  mistake_count: number;
  last_reviewed_at: string | null;
};

export type MasteryResponse = {
  items: MasteryItem[];
  total: number;
  average_score: number;
};

export type ReviewQuestion = {
  id: string;
  type: string;
  question: string;
  options: string[];
  answer: string;
  explanation: string;
};

export type ReviewItem = {
  knowledge_point: string;
  mastery_score: number;
  next_review_at: string | null;
  questions: ReviewQuestion[];
};

export type ReviewResponse = {
  items: ReviewItem[];
  total: number;
};

