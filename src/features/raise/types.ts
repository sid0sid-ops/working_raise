import { SubgraphQueryResponse } from '../../types';
import { BackendErrorDetails } from '../../components/chat/BackendErrorCard';

export interface SourceDocument {
  id: string;
  name: string;
  size: string;
  bytes?: number;
  pages: number;
  color: 'rose' | 'indigo' | 'emerald' | 'amber';
  selected: boolean;
  status?: 'ready' | 'processing' | 'failed';
  uploadProgress?: number;
}

export interface ResponseVersion {
  id: string;
  text: string;
  response?: Partial<SubgraphQueryResponse>;
  error?: BackendErrorDetails;
  durationSec?: number;
  timestamp?: string;
  isStopped?: boolean;
}

export interface QuestionVersion {
  id: string;
  question: string;
  responseVersions: ResponseVersion[];
  currentResponseVersionIndex: number;
  timestamp?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  response?: Partial<SubgraphQueryResponse>;
  error?: BackendErrorDetails;
  durationSec?: number;
  questionVersions?: QuestionVersion[];
  currentQuestionVersionIndex?: number;
  persistenceFailed?: boolean;
  isStopped?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  messages: ChatMessage[];
  selectedSourceIds?: string[];
  sources?: SourceDocument[];
  thread_id?: string;
  session_id?: string;
  username?: string;
  created_at?: string;
  updated_at?: string;
  is_saved?: boolean;
}

export interface DynamicSuggestion {
  query: string;
  title?: string;
  prompt?: string;
  category?: string;
  grounding_confidence?: string;
  complexity?: string;
  relationship_path?: string;
}
