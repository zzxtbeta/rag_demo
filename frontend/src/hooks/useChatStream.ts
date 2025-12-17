import { useCallback, useEffect, useRef, useState } from "react";
import { ChatMessage, ThreadSummary, TraceStats } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "https://www.gravaity-cybernaut.top/agent";

const STORAGE_KEY_THREADS = "chat_threads";
const STORAGE_KEY_ACTIVE_THREAD = "chat_active_thread";
const STORAGE_KEY_CHAT_MODEL = "chat_model";
const STORAGE_KEY_WEBSEARCH = "enable_websearch";

// 生成消息存储的 key
function getMessagesStorageKey(threadId: string): string {
  return `chat_messages_${threadId}`;
}

// 生成 last_id 存储的 key（用于 Redis Stream 续订）
function getLastIdStorageKey(threadId: string): string {
  return `stream_last_id_${threadId}`;
}

// 从 localStorage 加载 last_id
function loadLastIdFromStorage(threadId: string): string | null {
  try {
    return localStorage.getItem(getLastIdStorageKey(threadId));
  } catch (error) {
    console.error("Failed to load last_id from storage:", error);
  }
  return null;
}

// 保存 last_id 到 localStorage
function saveLastIdToStorage(threadId: string, lastId: string): void {
  try {
    localStorage.setItem(getLastIdStorageKey(threadId), lastId);
  } catch (error) {
    console.error("Failed to save last_id to storage:", error);
  }
}

interface UseChatStreamResult {
  activeThreadId: string | null;
  threads: ThreadSummary[];
  messages: ChatMessage[];
  isStreaming: boolean;
  sendMessage: (content: string, documents?: Array<{filename: string; format: string; markdown_content: string}>) => Promise<void>;
  switchThread: (threadId: string) => Promise<void>;
  createThread: () => void;
  deleteThread: (threadId: string) => Promise<void>;
  updateThreadTitle: (threadId: string, title: string) => void;
  chatModel: string;
  setChatModel: (model: string) => void;
  enableWebsearch: boolean;
  setEnableWebsearch: (enabled: boolean) => void;
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
  const [enableWebsearch, setEnableWebsearchState] = useState<boolean>(() => {
    const saved = localStorage.getItem(STORAGE_KEY_WEBSEARCH);
    return saved ? JSON.parse(saved) : false;
  });
  const [traceStats, setTraceStats] = useState<TraceStats | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // 当 threads 变化时，保存到 localStorage
  useEffect(() => {
    saveThreadsToStorage(threads);
  }, [threads]);

  // 当 activeThreadId 变化时，保存到 localStorage
  useEffect(() => {
    saveActiveThreadToStorage(activeThreadId);
  }, [activeThreadId]);

  // 自动保存消息到 localStorage（用于刷新恢复）
  // 只保存用户和助手消息，节点消息由后端 API 重构
  useEffect(() => {
    if (activeThreadId && messages.length > 0) {
      // 过滤出用户和助手消息（排除节点消息）
      const chatMessages = messages.filter(
        (msg) => msg.role === "user" || msg.role === "assistant"
      );
      if (chatMessages.length > 0) {
        saveMessagesToStorage(activeThreadId, chatMessages);
      }
    }
  }, [messages, activeThreadId]);

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
    try {
      const response = await fetch(`${API_BASE}/chat/threads/${encodeURIComponent(threadId)}/history`);
      if (!response.ok) {
        if (response.status === 404) {
          setMessages([]);
          return;
        }
        throw new Error(`Failed to load history: ${response.statusText}`);
      }
      const data = await response.json();
      
      const reconstructedMessages: ChatMessage[] = data.messages
        .filter((msg: any) => msg.role === 'user' || msg.role === 'assistant')
        .map((msg: any, index: number) => {
          const timestamp = msg.timestamp
            ? msg.timestamp * 1000
            : Date.now() - (data.messages.length - index) * 1000;
          return {
            id: msg.id || `${threadId}_history_${index}`,
            threadId,
            role: msg.role,
            content: msg.content || '',
            timestamp,
          } as ChatMessage;
        })
        .sort((a: ChatMessage, b: ChatMessage) => a.timestamp - b.timestamp);

      setMessages(reconstructedMessages);
      saveMessagesToStorage(threadId, reconstructedMessages);

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
      
      // 从 localStorage 恢复 last_id（用于 Redis Stream 续订）
      const lastId = loadLastIdFromStorage(threadId);
      const wsUrl = lastId 
        ? API_BASE.replace(/^http/, "ws") + `/ws/${encodeURIComponent(threadId)}?last_id=${encodeURIComponent(lastId)}`
        : API_BASE.replace(/^http/, "ws") + `/ws/${encodeURIComponent(threadId)}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // 保存 message_id 用于续订（Redis Stream 功能）
          if (data.message_id) {
            saveLastIdToStorage(threadId, data.message_id);
          }
          
          const threadIdFromData = data.thread_id ?? threadId;
          const nodeName = data.node_name;
          const messageType = data.message_type;
          const rawData = data.data ?? {};
          const isHistory = data.is_history === true;  // 标志是否为历史消息

          // 忽略历史消息（它们已经从 loadThreadHistory 加载了）
          // 只处理新的实时消息
          if (isHistory) {
            return;
          }

          if (messageType === "complete" || nodeName === "workflow") {
            // 工作流完成，关闭 WebSocket 连接
            if (wsRef.current) {
              wsRef.current.close();
            }
            return;
          }


          // 处理 token 级别的流式消息（messages 模式）
          if (messageType === "token") {
            const token = rawData.token || "";
            if (token) {
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];

                // 将 token 流式输出绑定到对应节点，便于后续在“工具决策阶段”回滚草稿内容。
                // 当前 graph 结构（Scheme A）没有 generate 节点；最终答案来自最后一次 query_or_respond。

                // 流式追加 token：只有当最后一条 assistant 与当前节点一致时才拼接
                if (lastMsg?.role === "assistant" && lastMsg.nodeName === nodeName) {
                  return prev.map((msg, idx) =>
                    idx === prev.length - 1
                      ? { ...msg, content: msg.content + token }
                      : msg,
                  );
                }

                // 否则创建新的 assistant 消息
                return [
                  ...prev,
                  {
                    id: data.id || data.message_id || `${Date.now()}_ai_${Math.random().toString(36).slice(2)}`,
                    threadId: threadIdFromData,
                    role: "assistant" as const,
                    content: token,
                    timestamp: Date.now(),
                    nodeName: nodeName || undefined,
                  },
                ];
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
            // query_or_respond 节点可能会先输出“需要调用工具”的草稿，再在下一次 query_or_respond 输出最终答案。
            // 为避免 Turn 结构按索引拿到“第一条 assistant（草稿）”，这里基于 tool_calls 判定是否回滚草稿。
            if (nodeName === "query_or_respond") {
              try {
                const firstMsg = rawData?.messages?.[0];
                const toolCalls =
                  firstMsg?.data?.tool_calls ||
                  firstMsg?.tool_calls ||
                  firstMsg?.data?.additional_kwargs?.tool_calls ||
                  [];
                const hasToolCalls = Array.isArray(toolCalls) && toolCalls.length > 0;

                // 找到最后一个 user 消息位置（当前 turn 的起点）
                setMessages((prev) => {
                  let lastUserIdx = -1;
                  for (let i = prev.length - 1; i >= 0; i--) {
                    if (prev[i].role === "user") {
                      lastUserIdx = i;
                      break;
                    }
                  }

                  // 仅处理当前轮次（最后一个 user 之后）的 assistant 消息
                  const currentTurnAssistantIdxs: number[] = [];
                  for (let i = lastUserIdx + 1; i < prev.length; i++) {
                    if (prev[i].role === "assistant") {
                      currentTurnAssistantIdxs.push(i);
                    }
                  }

                  if (hasToolCalls) {
                    // 这次 query_or_respond 是“决定调用工具”的中间输出：删除该轮次的草稿 assistant
                    return prev.filter((msg, idx) => {
                      if (idx <= lastUserIdx) return true;
                      if (msg.role !== "assistant") return true;
                      // 删除属于 query_or_respond token 流的草稿
                      return msg.nodeName !== "query_or_respond";
                    });
                  }

                  // 没有 tool_calls：这是最终回答。
                  // 确保该轮次只保留一个 assistant（如果有多个，保留最后一个；如果没有 token，直接用 output 内容补齐）。
                  const finalContent =
                    firstMsg?.data?.content ||
                    firstMsg?.content ||
                    "";

                  if (currentTurnAssistantIdxs.length === 0) {
                    if (!finalContent) return prev;
                    return [
                      ...prev,
                      {
                        id: firstMsg?.data?.id || firstMsg?.id || `${Date.now()}_ai_${Math.random().toString(36).slice(2)}`,
                        threadId: threadIdFromData,
                        role: "assistant" as const,
                        content: finalContent,
                        timestamp: Date.now(),
                        nodeName: "query_or_respond",
                      },
                    ];
                  }

                  const lastAssistantIdx = currentTurnAssistantIdxs[currentTurnAssistantIdxs.length - 1];
                  const filtered = prev.filter((msg, idx) => {
                    if (idx <= lastUserIdx) return true;
                    if (msg.role !== "assistant") return true;
                    return idx === lastAssistantIdx;
                  });

                  // 如果最后一条 assistant 是 token 拼出来的，但 output 有更完整 content，可用 output 覆盖（避免丢字）
                  if (finalContent) {
                    return filtered.map((m, idx) => {
                      if (idx !== filtered.length - 1) return m;
                      if (m.role !== "assistant") return m;
                      // 只有当 output 明显更长时才覆盖，避免闪烁
                      if ((finalContent as string).length > (m.content || "").length) {
                        return { ...m, content: finalContent };
                      }
                      return m;
                    });
                  }

                  return filtered;
                });
              } catch {
                // ignore parse errors
              }
            }

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

  const setEnableWebsearch = useCallback((enabled: boolean) => {
    setEnableWebsearchState(enabled);
    localStorage.setItem(STORAGE_KEY_WEBSEARCH, JSON.stringify(enabled));
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
    async (content: string, documents?: Array<{filename: string; format: string; markdown_content: string}>) => {
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
        documents: documents && documents.length > 0 ? documents : undefined,
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

      const requestBody: any = {
        thread_id: threadId,
        user_id: userId,
        message: content,
        chat_model: chatModel,
        enable_websearch: enableWebsearch,
      };

      // 如果有上传的文档，传递完整的文档元数据给后端
      if (documents && documents.length > 0) {
        requestBody.documents = documents;
      }

      await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });
    },
    [ensureThread, attachWebSocket, userId, chatModel, enableWebsearch, generateTitleFromMessage],
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
    enableWebsearch,
    setEnableWebsearch,
    traceStats,
  };
}


