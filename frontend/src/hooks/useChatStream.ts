import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, ThreadSummary } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const STORAGE_KEY_THREADS = "chat_threads";
const STORAGE_KEY_ACTIVE_THREAD = "chat_active_thread";
const STORAGE_KEY_CHAT_MODEL = "chat_model";

interface UseChatStreamResult {
  activeThreadId: string | null;
  threads: ThreadSummary[];
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  switchThread: (threadId: string) => Promise<void>;
  createThread: () => void;
  chatModel: string;
  setChatModel: (model: string) => void;
}

// 从 localStorage 加载 threads
function loadThreadsFromStorage(): ThreadSummary[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_THREADS);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error("Failed to load threads from storage:", error);
  }
  return [];
}

// 保存 threads 到 localStorage
function saveThreadsToStorage(threads: ThreadSummary[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_THREADS, JSON.stringify(threads));
  } catch (error) {
    console.error("Failed to save threads to storage:", error);
  }
}

// 从 localStorage 加载 activeThreadId
function loadActiveThreadFromStorage(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY_ACTIVE_THREAD);
  } catch (error) {
    console.error("Failed to load active thread from storage:", error);
  }
  return null;
}

// 保存 activeThreadId 到 localStorage
function saveActiveThreadToStorage(threadId: string | null): void {
  try {
    if (threadId) {
      localStorage.setItem(STORAGE_KEY_ACTIVE_THREAD, threadId);
    } else {
      localStorage.removeItem(STORAGE_KEY_ACTIVE_THREAD);
    }
  } catch (error) {
    console.error("Failed to save active thread to storage:", error);
  }
}

export function useChatStream(userId: string = "demo-user"): UseChatStreamResult {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(() => 
    loadActiveThreadFromStorage()
  );
  const [threads, setThreads] = useState<ThreadSummary[]>(() => 
    loadThreadsFromStorage()
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatModel, setChatModelState] = useState<string>(() => {
    const saved = localStorage.getItem(STORAGE_KEY_CHAT_MODEL);
    return saved || "qwen-plus-latest";
  });

  const wsRef = useRef<WebSocket | null>(null);

  // 当 threads 变化时，保存到 localStorage
  useEffect(() => {
    saveThreadsToStorage(threads);
  }, [threads]);

  // 当 activeThreadId 变化时，保存到 localStorage
  useEffect(() => {
    saveActiveThreadToStorage(activeThreadId);
  }, [activeThreadId]);

  // 初始化时，如果有 activeThreadId，加载历史记录
  useEffect(() => {
    if (activeThreadId) {
      loadThreadHistory(activeThreadId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在组件挂载时执行一次

  const ensureThread = useCallback(async () => {
    if (activeThreadId) {
      return activeThreadId;
    }
    const id = `thread_${userId}_${Date.now()}`;
    const title = "New Chat";
    const now = Date.now();
    setThreads((prev) => {
      const updated = [{ id, title, lastUpdated: now }, ...prev];
      saveThreadsToStorage(updated);
      return updated;
    });
    setActiveThreadId(id);
    setMessages([]);
    return id;
  }, [activeThreadId, userId]);

  const loadThreadHistory = useCallback(async (threadId: string) => {
    try {
      const response = await fetch(`${API_BASE}/chat/threads/${encodeURIComponent(threadId)}/history`);
      if (!response.ok) {
        if (response.status === 404) {
          // 线程不存在，清空消息
          setMessages([]);
          return;
        }
        throw new Error(`Failed to load history: ${response.statusText}`);
      }
      const data = await response.json();
      
      // 将历史消息转换为 ChatMessage 格式
      const historyMessages: ChatMessage[] = data.messages.map((msg: any, index: number) => ({
        id: `${threadId}_history_${index}`,
        threadId: threadId,
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp || Date.now() - (data.messages.length - index) * 1000,
      }));
      
      setMessages(historyMessages);
    } catch (error) {
      console.error("Failed to load thread history:", error);
      // 如果加载失败，至少清空当前消息
      setMessages([]);
    }
  }, []);

  const switchThread = useCallback(
    async (threadId: string) => {
      setActiveThreadId(threadId);
      setMessages([]); // 先清空，避免显示旧消息
      // 加载该线程的历史记录
      await loadThreadHistory(threadId);
    },
    [loadThreadHistory]
  );

  const createThread = useCallback(() => {
    const id = `thread_${userId}_${Date.now()}`;
    const title = "New Chat";
    const now = Date.now();
    setThreads((prev) => {
      const updated = [{ id, title, lastUpdated: now }, ...prev];
      saveThreadsToStorage(updated);
      return updated;
    });
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

          if (messageType === "complete") {
            return;
          }

          // 处理 token 级别的流式消息
          if (messageType === "token") {
            const token = rawData.token || "";
            if (token) {
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                // 如果最后一条消息是 assistant 消息，追加 token
                if (lastMsg?.role === "assistant") {
                  return prev.map((msg, idx) =>
                    idx === prev.length - 1
                      ? { ...msg, content: msg.content + token }
                      : msg,
                  );
                } else {
                  // 否则创建新的 assistant 消息
                  return [
                    ...prev,
                    {
                      id: `${Date.now()}_ai_${Math.random().toString(36).slice(2)}`,
                      threadId: threadIdFromData,
                      role: "assistant" as const,
                      content: token,
                      timestamp: Date.now(),
                    },
                  ];
                }
              });
            }
            return;
          }

          // 处理节点输出和错误消息（不再提取 AI 消息，因为 token 流已经处理了）
          if (messageType === "error") {
            const nodeMsg: ChatMessage = {
              id: `${Date.now()}_node_${Math.random().toString(36).slice(2)}`,
              threadId: threadIdFromData,
              role: "node",
              content: `Error: ${rawData.error || "Unknown error"}`,
              nodeName: nodeName || "workflow",
              messageType: "error",
              timestamp: Date.now(),
            };
            setMessages((prev) => [...prev, nodeMsg]);
            return;
          }

          // 处理节点输出（output/start）：只显示节点信息，不提取 AI 消息
          if (nodeName && nodeName !== "workflow" && messageType !== "token") {
            const nodeContent = JSON.stringify(rawData, null, 2);
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

          // 更新线程时间戳
          const updateTime = Date.now();
          setThreads((prev) => {
            const updated = prev.map((t) =>
              t.id === threadIdFromData ? { ...t, lastUpdated: updateTime } : t,
            );
            saveThreadsToStorage(updated);
            return updated;
          });
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

  const setChatModel = useCallback((model: string) => {
    setChatModelState(model);
    localStorage.setItem(STORAGE_KEY_CHAT_MODEL, model);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      const threadId = await ensureThread();
      const userMessage: ChatMessage = {
        id: `${Date.now()}_user`,
        threadId,
        role: "user",
        content,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setThreads((prev) => {
        const updated = prev.map((t) =>
          t.id === threadId ? { ...t, lastUpdated: userMessage.timestamp } : t,
        );
        saveThreadsToStorage(updated);
        return updated;
      });

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
          chat_model: chatModel,
        }),
      });
    },
    [ensureThread, attachWebSocket, userId, chatModel],
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
    chatModel,
    setChatModel,
  };
}


