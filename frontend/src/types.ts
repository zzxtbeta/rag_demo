export type Role = "user" | "assistant" | "system" | "node";

export interface DocumentMetadata {
  filename?: string
  format?: string
  markdown_content: string
}

export interface ChatMessage {
  id: string;
  threadId: string;
  role: Role;
  content: string;
  nodeName?: string;
  messageType?: string;
  timestamp: number;
  documents?: DocumentMetadata[];
}

export interface NodeStep {
  id: string;
  nodeName: string;
  status: "start" | "running" | "completed" | "error";
  messageType: "start" | "output" | "token" | "error" | "custom";
  timestamp: number;
  executionTimeMs?: number;
  data?: any;
  isExpanded?: boolean;
}

export interface Turn {
  id: string;
  threadId: string;
  userMessage: ChatMessage;
  nodeSteps: NodeStep[];
  assistantMessage: ChatMessage | null;
  timestamp: number;
}

export interface ThreadSummary {
  id: string;
  title: string;
  lastUpdated: number;
}

export interface TraceStats {
  rootRunId: string | null;
  totalLatencyMs: number | null;
  totalTokens: number | null;
}


