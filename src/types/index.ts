import type { Citation } from '../schemas/chat';

export * from '../schemas/chat';
export * from '../schemas/common';
export * from '../schemas/graph';
export * from '../schemas/sources';
export * from '../schemas/system';

export type AppMode = 'mock' | 'connected' | 'degraded' | 'offline';
export type ConfigMode = 'mock' | 'remote' | 'auto';

export interface ResponseVersion {
  id: string;
  text: string;
  response?: any;
  error?: any;
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
  response?: any;
  sources?: string[] | any[];
  citations?: Citation[] | any[];
  error?: any;
  durationSec?: number;
  questionVersions?: QuestionVersion[];
  currentQuestionVersionIndex?: number;
  persistenceFailed?: boolean;
  isStopped?: boolean;
  feedback?: 'thumbs_up' | 'thumbs_down' | null;
  id?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  messages: ChatMessage[];
  selectedSourceIds?: string[];
  sources?: SourceDocument[] | any[];
  thread_id?: string;
  session_id?: string;
  username?: string;
  created_at?: string;
  updated_at?: string;
  is_saved?: boolean;
  attached_docs?: string[];
}

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

export interface DynamicSuggestion {
  query: string;
  title?: string;
  prompt?: string;
  category?: string;
  grounding_confidence?: string;
  complexity?: string;
  relationship_path?: string;
}
