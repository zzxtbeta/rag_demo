import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, ThreadSummary } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface UseChatStreamResult {
  activeThreadId: string | null;
  threads: ThreadSummary[];
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  switchThread: (threadId: string) => void;
  createThread: () => void;
}

export function useChatStream(userId: string = "demo-user"): UseChatStreamResult {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  const ensureThread = useCallback(() => {
    if (activeThreadId) return activeThreadId;
    const id = `thread_${userId}_${Date.now()}`;
    const title = "New Chat";
    const now = Date.now();
    setThreads((prev) => [{ id, title, lastUpdated: now }, ...prev]);
    setActiveThreadId(id);
    return id;
  }, [activeThreadId, userId]);

  const switchThread = useCallback((threadId: string) => {
    setActiveThreadId(threadId);
    setMessages((prev) => prev.filter((m) => m.threadId === threadId));
  }, []);

  const createThread = useCallback(() => {
    const id = `thread_${userId}_${Date.now()}`;
    const title = "New Chat";
    const now = Date.now();
    setThreads((prev) => [{ id, title, lastUpdated: now }, ...prev]);
    setActiveThreadId(id);
    setMessages([]);
  }, [userId]);

  const attachWebSocket = useCallback(
    (threadId: string) => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      const wsUrl = API_BASE.replace(/^http/, "ws") + `/ws/${encodeURIComponent(threadId)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const threadIdFromData = data.thread_id ?? threadId;
          const nodeName = data.node_name;
          const messageType = data.message_type;
          const rawData = data.data ?? {};

          let nodeContent = "";
          let extractedAiMessage: ChatMessage | null = null;
          let shouldShowNodeMessage = false;

          if (messageType === "complete") {
            return;
          }

          if (messageType === "error") {
            nodeContent = `Error: ${rawData.error || "Unknown error"}`;
            shouldShowNodeMessage = true;
          } else if (rawData.messages && Array.isArray(rawData.messages)) {
            const aiMessages = rawData.messages.filter(
              (m: any) => m.type === "ai" && m.data?.content,
            );
            if (aiMessages.length > 0) {
              const lastAiMsg = aiMessages[aiMessages.length - 1];
              extractedAiMessage = {
                id: `${Date.now()}_ai_${Math.random().toString(36).slice(2)}`,
                threadId: threadIdFromData,
                role: "assistant",
                content: lastAiMsg.data.content,
                timestamp: Date.now(),
              };
              nodeContent = JSON.stringify(rawData, null, 2);
              shouldShowNodeMessage = true;
            } else {
              nodeContent = JSON.stringify(rawData, null, 2);
              shouldShowNodeMessage = true;
            }
          } else if (Object.keys(rawData).length > 0) {
            nodeContent = JSON.stringify(rawData, null, 2);
            shouldShowNodeMessage = true;
          } else {
            return;
          }

          if (nodeName && nodeName !== "workflow" && shouldShowNodeMessage) {
            const nodeMsg: ChatMessage = {
              id: `${Date.now()}_node_${Math.random().toString(36).slice(2)}`,
              threadId: threadIdFromData,
              role: "node",
              content: nodeContent,
              nodeName: nodeName,
              messageType: messageType,
              timestamp: Date.now(),
            };
            setMessages((prev) => [...prev, nodeMsg]);
          }

          if (extractedAiMessage && extractedAiMessage.content.trim()) {
            setMessages((prev) => {
              const lastMsg = prev[prev.length - 1];
              if (
                lastMsg?.role === "assistant" &&
                lastMsg.content === extractedAiMessage!.content
              ) {
                return prev;
              }
              return [...prev, extractedAiMessage!];
            });
          }

          // 更新线程时间戳
          const updateTime = Date.now();
          setThreads((prev) =>
            prev.map((t) =>
              t.id === threadIdFromData ? { ...t, lastUpdated: updateTime } : t,
            ),
          );
        } catch {
          // ignore malformed messages
        }
      };

      ws.onopen = () => {
        setIsStreaming(true);
      };

      ws.onclose = () => {
        setIsStreaming(false);
      };
    },
    [],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const threadId = ensureThread();
      const userMessage: ChatMessage = {
        id: `${Date.now()}_user`,
        threadId,
        role: "user",
        content,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setThreads((prev) =>
        prev.map((t) =>
          t.id === threadId ? { ...t, lastUpdated: userMessage.timestamp } : t,
        ),
      );

      attachWebSocket(threadId);

      await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          thread_id: threadId,
          user_id: userId,
          message: content,
        }),
      });
    },
    [ensureThread, attachWebSocket, userId],
  );

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    activeThreadId,
    threads,
    messages: messages.filter(
      (m) => !activeThreadId || m.threadId === activeThreadId,
    ),
    isStreaming,
    sendMessage,
    switchThread,
    createThread,
  };
}


