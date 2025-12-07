import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, ThreadSummary } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const STORAGE_KEY_THREADS = "chat_threads";
const STORAGE_KEY_ACTIVE_THREAD = "chat_active_thread";
const STORAGE_KEY_CHAT_MODEL = "chat_model";

// 生成消息存储的 key
function getMessagesStorageKey(threadId: string): string {
  return `chat_messages_${threadId}`;
}

interface UseChatStreamResult {
  activeThreadId: string | null;
  threads: ThreadSummary[];
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  switchThread: (threadId: string) => Promise<void>;
  createThread: () => void;
  deleteThread: (threadId: string) => Promise<void>;
  updateThreadTitle: (threadId: string, title: string) => void;
  chatModel: string;
  setChatModel: (model: string) => void;
  traceStats: TraceStats | null;
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

// 从 localStorage 加载消息
function loadMessagesFromStorage(threadId: string): ChatMessage[] {
  try {
    const key = getMessagesStorageKey(threadId);
    const stored = localStorage.getItem(key);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error("Failed to load messages from storage:", error);
  }
  return [];
}

// 保存消息到 localStorage
function saveMessagesToStorage(threadId: string, messages: ChatMessage[]): void {
  try {
    const key = getMessagesStorageKey(threadId);
    localStorage.setItem(key, JSON.stringify(messages));
  } catch (error) {
    console.error("Failed to save messages to storage:", error);
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

  // 注意：不再自动保存节点消息到 LocalStorage
  // 因为节点消息现在完全由后端 API（LangSmith Trace）重构
  // 只在流式执行时临时保存，刷新时会从后端重新加载
  // useEffect(() => {
  //   if (activeThreadId && messages.length > 0) {
  //     saveMessagesToStorage(activeThreadId, messages);
  //   }
  // }, [messages, activeThreadId]);

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

  // 从第一条用户消息提取标题（前30个字符）
  const generateTitleFromMessage = useCallback((content: string): string => {
    const trimmed = content.trim();
    if (!trimmed) return "New Chat";
    // 移除换行和多余空格
    const singleLine = trimmed.replace(/\s+/g, " ").substring(0, 30);
    return singleLine || "New Chat";
  }, []);

  const loadThreadHistory = useCallback(async (threadId: string) => {
    // 添加 Loading 占位消息
    setMessages([{
      id: 'loading',
      threadId,
      role: 'system',
      content: '正在加载历史记录...',
      timestamp: Date.now(),
    }]);
    
    try {
      const response = await fetch(`${API_BASE}/chat/threads/${encodeURIComponent(threadId)}/history-with-trace`);
      if (!response.ok) {
        if (response.status === 404) {
          setMessages([]);
          return;
        }
        throw new Error(`Failed to load history: ${response.statusText}`);
      }
      const data = await response.json();
      
      // 简化历史消息重构：只加载用户和助手消息
      // 实时节点执行过程不会持久化，刷新后不显示
      const reconstructedMessages: ChatMessage[] = [];
      
      // 直接加载用户和助手消息（使用数据库中的时间戳）
      data.messages.forEach((msg: any, index: number) => {
        const baseId = msg.id || `${threadId}_history_${index}`;
        
        // 使用数据库中保存的时间戳（秒 → 毫秒）
        const timestamp = msg.timestamp ? msg.timestamp * 1000 : Date.now() - (data.messages.length - index) * 1000;

        if (msg.role === 'user') {
          reconstructedMessages.push({
            id: baseId,
            threadId,
            role: 'user',
            content: msg.content,
            timestamp
          });
        } else if (msg.role === 'assistant') {
          reconstructedMessages.push({
            id: baseId,
            threadId,
            role: 'assistant',
            content: msg.content,
            timestamp
          });
        }
        // 忽略其他类型的消息（如 tool、system）
      });
      
      // 按时间戳排序确保正确的执行顺序
      reconstructedMessages.sort((a, b) => a.timestamp - b.timestamp);
      setMessages(reconstructedMessages);

      // 更新标题（如果需要）
      const firstUserMessage = reconstructedMessages.find((msg) => msg.role === "user");
      if (firstUserMessage) {
        setThreads((prev) => {
          const thread = prev.find((t) => t.id === threadId);
          if (thread && thread.title === "New Chat") {
            const newTitle = generateTitleFromMessage(firstUserMessage.content);
            const updated = prev.map((t) =>
              t.id === threadId ? { ...t, title: newTitle } : t,
            );
            saveThreadsToStorage(updated);
            return updated;
          }
          return prev;
        });
      }
    } catch (error) {
      console.error("Failed to load thread history:", error);
      setMessages([]);
    }
  }, [generateTitleFromMessage]);

  const switchThread = useCallback(
    async (threadId: string) => {
      setActiveThreadId(threadId);
      setMessages([]); // 先清空，避免显示旧消息
      // 清除 LocalStorage 中的旧数据（确保从后端重新加载）
      localStorage.removeItem(getMessagesStorageKey(threadId));
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


          // 处理 token 级别的流式消息（messages 模式）
          if (messageType === "token") {
            const token = rawData.token || "";
            if (token) {
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                
                // ✅ 关键修复:判断是否需要创建新的 assistant 消息
                // 如果当前节点是 generate(最终答案),需要:
                // 1. 移除当前轮次中 query_or_respond 创建的临时 assistant 消息
                // 2. 创建新的 assistant 消息用于显示最终答案
                if (nodeName === "generate") {
                  // 找到最后一个 user 消息的索引
                  let lastUserIdx = -1;
                  for (let i = prev.length - 1; i >= 0; i--) {
                    if (prev[i].role === "user") {
                      lastUserIdx = i;
                      break;
                    }
                  }
                  
                  // 只移除最后一个 user 消息之后的、没有 nodeName 的 assistant 消息
                  const filteredMessages = prev.filter((msg, idx) => {
                    // 保留所有非 assistant 消息
                    if (msg.role !== "assistant") return true;
                    // 保留最后一个 user 消息之前的所有消息
                    if (idx <= lastUserIdx) return true;
                    // 保留已经有 nodeName='generate' 的 assistant 消息
                    if (msg.nodeName === "generate") return true;
                    // 移除当前轮次中没有 nodeName 的 assistant 消息(来自 query_or_respond)
                    return false;
                  });
                  
                  // 检查最后一条消息是否是当前 generate 节点的 assistant 消息
                  const lastFiltered = filteredMessages[filteredMessages.length - 1];
                  if (lastFiltered?.role === "assistant" && lastFiltered.nodeName === "generate") {
                    // 追加 token 到现有的 generate 消息
                    return filteredMessages.map((msg, idx) =>
                      idx === filteredMessages.length - 1
                        ? { ...msg, content: msg.content + token }
                        : msg,
                    );
                  } else {
                    // 创建新的 generate 消息
                    return [
                      ...filteredMessages,
                      {
                        id: `${Date.now()}_ai_${Math.random().toString(36).slice(2)}`,
                        threadId: threadIdFromData,
                        role: "assistant" as const,
                        content: token,
                        timestamp: Date.now(),
                        nodeName: "generate",
                      },
                    ];
                  }
                }
                
                // 非 generate 节点:正常处理 token 累积
                // 流式追加 token：如果最后一条是 assistant 消息,追加 token
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

          // 处理节点输出和错误消息
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

          // 处理节点完成事件（只显示 output）
          // 忽略 start 事件和 workflow 节点
          if (nodeName && nodeName !== "workflow" && messageType === "output") {
            const nodeMsg: ChatMessage = {
              id: `${Date.now()}_node_${Math.random().toString(36).slice(2)}`,
              threadId: threadIdFromData,
              role: "node",
              content: JSON.stringify(rawData, null, 2),
              nodeName: nodeName,
              messageType: "output",
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

  const updateThreadTitle = useCallback((threadId: string, title: string) => {
    setThreads((prev) => {
      const updated = prev.map((t) =>
        t.id === threadId ? { ...t, title } : t,
      );
      saveThreadsToStorage(updated);
      return updated;
    });
  }, []);

  const deleteThread = useCallback(
    async (threadId: string) => {
      try {
        // 调用后端 API 删除 checkpoint
        const response = await fetch(
          `${API_BASE}/chat/threads/${encodeURIComponent(threadId)}`,
          {
            method: "DELETE",
          },
        );
        if (!response.ok) {
          throw new Error(`Failed to delete thread: ${response.statusText}`);
        }

        // 删除 localStorage 中的消息
        try {
          const key = getMessagesStorageKey(threadId);
          localStorage.removeItem(key);
        } catch (error) {
          console.error("Failed to remove messages from storage:", error);
        }

        // 从本地状态中移除
        setThreads((prev) => {
          const updated = prev.filter((t) => t.id !== threadId);
          saveThreadsToStorage(updated);
          return updated;
        });

        // 如果删除的是当前活动线程，切换到其他线程或清空
        if (activeThreadId === threadId) {
          setThreads((prev) => {
            if (prev.length > 0) {
              setActiveThreadId(prev[0].id);
              return prev;
            } else {
              setActiveThreadId(null);
              setMessages([]);
              return prev;
            }
          });
        }
      } catch (error) {
        console.error("Failed to delete thread:", error);
        throw error;
      }
    },
    [activeThreadId],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const threadId = await ensureThread();
      
      // 清理之前实时流遗留的节点消息（保留用户和助手消息）
      // 这样可以避免新的流式消息与旧的节点消息混淆
      setMessages((prev) => prev.filter(msg => msg.role !== 'node'));
      
      const userMessage: ChatMessage = {
        id: `${Date.now()}_user`,
        threadId,
        role: "user",
        content,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // 如果是第一条用户消息，更新标题
      setThreads((prev) => {
        const thread = prev.find((t) => t.id === threadId);
        if (thread && thread.title === "New Chat") {
          const newTitle = generateTitleFromMessage(content);
          const updated = prev.map((t) =>
            t.id === threadId
              ? { ...t, title: newTitle, lastUpdated: userMessage.timestamp }
              : t,
          );
          saveThreadsToStorage(updated);
          return updated;
        } else {
          const updated = prev.map((t) =>
            t.id === threadId ? { ...t, lastUpdated: userMessage.timestamp } : t,
          );
          saveThreadsToStorage(updated);
          return updated;
        }
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
    [ensureThread, attachWebSocket, userId, chatModel, generateTitleFromMessage],
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
    deleteThread,
    updateThreadTitle,
    chatModel,
    setChatModel,
  };
}


