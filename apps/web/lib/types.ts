export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export type DocumentRead = {
  id: string;
  title: string;
  file_type: string;
  status: DocumentStatus;
  file_path?: string | null;
  summary?: string | null;
  is_public: boolean;
  forked_from?: string | null;
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

export type QuizSummary = {
  id: string;
  title: string;
  difficulty: string;
  question_count: number;
  created_at: string;
};

export type QuizListResponse = {
  quizzes: QuizSummary[];
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

export type StudyPlanItem = {
  document_id: string;
  document_title: string;
  reason: string;
  priority: number;
};

export type StudyPlan = {
  items: StudyPlanItem[];
  generated_at: string;
};

export type ErrorEntry = {
  question_id: string;
  quiz_id: string;
  document_id: string;
  knowledge_point: string;
  question_text: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  mistake_count: number;
  last_wrong_at?: string | null;
};

export type ErrorGroup = {
  knowledge_point: string;
  mistake_count: number;
  mastery_score?: number | null;
  entries: ErrorEntry[];
};

export type ErrorNotebookResponse = {
  groups: ErrorGroup[];
  total_mistakes: number;
};

export type KnowledgeNode = {
  id: string;
  label: string;
  type: string;
};

export type KnowledgeEdge = {
  source: string;
  target: string;
  label: string;
};

export type KnowledgeGraph = {
  document_id: string;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  error?: string;
};

export type UserRead = {
  id: string;
  email: string;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type WeeklyReport = {
  period_days: number;
  documents_added: number;
  quizzes_taken: number;
  questions_answered: number;
  correct_rate: number;
  average_mastery: number;
  weakest_points: string[];
  strongest_points: string[];
  recommendations: string;
  generated_at: string;
};

