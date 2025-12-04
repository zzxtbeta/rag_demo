export type Role = "user" | "assistant" | "system" | "node";

export interface ChatMessage {
  id: string;
  threadId: string;
  role: Role;
  content: string;
  nodeName?: string;
  messageType?: string;
  timestamp: number;
}

export interface ThreadSummary {
  id: string;
  title: string;
  lastUpdated: number;
}


