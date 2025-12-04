import type { FC } from "react";
import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";

interface ChatWindowProps {
  messages: ChatMessage[];
}

const ChatWindow: FC<ChatWindowProps> = ({ messages }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const formatNodeContent = (content: string): string => {
    try {
      const parsed = JSON.parse(content);
      // 如果是JSON，尝试提取有意义的信息
      if (parsed.messages && Array.isArray(parsed.messages)) {
        const aiMsg = parsed.messages.find((m: any) => m.type === "ai");
        if (aiMsg?.data?.content) {
          return aiMsg.data.content;
        }
      }
      return content;
    } catch {
      return content;
    }
  };

  return (
    <main className="chat-window">
      <header className="chat-header">
        <div className="chat-title">Chat LangGraph</div>
        <div className="chat-subtitle">
          Streaming RAG Agent with Redis + LangGraph
        </div>
      </header>
      <div className="chat-messages">
        {messages.map((m) => {
          const isUser = m.role === "user";
          const isNode = m.role === "node";
          const isAssistant = m.role === "assistant";

          // 节点消息：只在开发模式下显示，或者显示简化版本
          if (isNode) {
            const isJson = m.content.trim().startsWith("{");
            return (
              <div key={m.id} className="chat-message chat-message-node">
                <div className="chat-message-meta">
                  <span className="node-badge">{m.nodeName ?? "node"}</span>
                  {m.messageType && (
                    <span className="node-type">{m.messageType}</span>
                  )}
                </div>
                {isJson ? (
                  <details className="node-details">
                    <summary className="node-summary">View details</summary>
                    <pre className="node-json">{m.content}</pre>
                  </details>
                ) : (
                  <div className="chat-message-content">{m.content}</div>
                )}
              </div>
            );
          }

          // 用户和助手消息
          return (
            <div
              key={m.id}
              className={
                "chat-message" +
                (isUser
                  ? " chat-message-user"
                  : isAssistant
                  ? " chat-message-assistant"
                  : "")
              }
            >
              <div className="chat-message-meta">
                {isUser ? "You" : "Assistant"}
              </div>
              <div className="chat-message-content">
                {m.content.split("\n").map((line, idx) => (
                  <div key={idx}>{line}</div>
                ))}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
        {messages.length === 0 && (
          <div className="chat-empty-hint">
            Start a conversation by typing in the box below.
          </div>
        )}
      </div>
    </main>
  );
};

export default ChatWindow;


