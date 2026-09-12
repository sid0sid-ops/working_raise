export * from '../schemas/common';
export * from '../schemas/chat';
export * from '../schemas/sources';
export * from '../schemas/graph';
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
  error?: any;
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
  sources?: any[];
  thread_id?: string;
  session_id?: string;
  username?: string;
  created_at?: string;
  updated_at?: string;
  is_saved?: boolean;
}

