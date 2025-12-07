import type { FC } from "react";
import { useEffect, useRef, useMemo, useState } from "react";
import type { ChatMessage, NodeStep } from "../types";
import TurnView from "./TurnView";
import blackholeIcon from "../../icon/黑洞.png";

const AVAILABLE_MODELS = [
  { value: "qwen-plus-latest", label: "Qwen Plus" },
  { value: "qwen-max-latest", label: "Qwen Max" },
  { value: "qwen-flash", label: "Qwen Flash" },
] as const;

interface SettingsMenuProps {
  chatModel: string;
  onChatModelChange: (model: string) => void;
}

const SettingsMenu: FC<SettingsMenuProps> = ({ chatModel, onChatModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = localStorage.getItem("theme");
    return (saved as "dark" | "light") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChatModelChange(e.target.value);
  };

  return (
    <div className="settings-menu-wrapper">
      <button
        className="chat-settings-btn"
        onClick={() => setIsOpen(!isOpen)}
        title="Settings"
        aria-label="Settings"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24" />
        </svg>
      </button>
      {isOpen && (
        <div className="settings-dropdown">
          <div className="settings-section">
            <div className="settings-section-title">外观</div>
            <div className="settings-item">
              <label className="settings-label">主题模式</label>
              <div className="settings-control">
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={theme === "light"}
                    onChange={toggleTheme}
                  />
                  <span className="toggle-slider"></span>
                </label>
                <span className="settings-value">{theme === "dark" ? "暗黑模式" : "浅色模式"}</span>
              </div>
            </div>
          </div>
          <div className="settings-section">
            <div className="settings-section-title">模型设置</div>
            <div className="settings-item">
              <label className="settings-label">Chat Model</label>
              <div className="settings-control">
                <select
                  className="settings-select"
                  value={chatModel}
                  onChange={handleModelChange}
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <option key={model.value} value={model.value}>
                      {model.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

interface ChatWindowProps {
  messages: ChatMessage[];
  onNewThread?: () => void;
  onToggleSidebar?: () => void;
  chatModel: string;
  onChatModelChange: (model: string) => void;
}

const ChatWindow: FC<ChatWindowProps> = ({ 
  messages, 
  onNewThread, 
  onToggleSidebar, 
  chatModel, 
  onChatModelChange,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 组织消息为 Turn 结构
  const turns = useMemo(() => {
    const turns: Array<{
      userMessage: ChatMessage;
      nodeSteps: NodeStep[];
      assistantMessage: ChatMessage | null;
    }> = [];

    // 简化 Turn 组织逻辑：
    // 1. 用户消息作为 Turn 起点
    // 2. 节点消息根据时间戳分配到对应的 Turn
    // 3. 助手消息匹配对应的 Turn
    
    const userMessages = messages.filter(m => m.role === 'user');
    const nodeMessages = messages.filter(m => m.role === 'node');
    const assistantMessages = messages.filter(m => m.role === 'assistant');
    
    for (let i = 0; i < userMessages.length; i++) {
      const userMsg = userMessages[i];
      const nextUserMsg = userMessages[i + 1];
      
      // 根据时间戳找到属于这个 Turn 的节点消息
      const turnNodeMessages = nodeMessages.filter(msg => {
        if (nextUserMsg) {
          // 在当前用户消息和下一个用户消息之间的节点
          return msg.timestamp >= userMsg.timestamp && msg.timestamp < nextUserMsg.timestamp;
        } else {
          // 最后一个 Turn，包含当前用户消息之后的所有节点
          return msg.timestamp >= userMsg.timestamp;
        }
      });
      
      const nodeSteps: NodeStep[] = [];
      
      for (const msg of turnNodeMessages) {
        let parsedData = null;
        try {
          if (msg.content.trim().startsWith("{")) {
            parsedData = JSON.parse(msg.content);
          }
        } catch (e) {
          // Ignore parse errors
        }

        const step: NodeStep = {
          id: msg.id,
          nodeName: msg.nodeName || "unknown",
          status:
            msg.messageType === "start"
              ? "start"
              : msg.messageType === "error"
              ? "error"
              : msg.messageType === "token"
              ? "running"
              : msg.messageType === "custom"
              ? "running"
              : "completed",
          messageType: (msg.messageType as any) || "output",
          timestamp: msg.timestamp,
          data: parsedData,
        };
        
        nodeSteps.push(step);
      }
      
      // 找到对应的 assistant 消息（同样按索引匹配）
      const assistantMessage = assistantMessages[i] || null;
      
      // 保存这个 turn
      turns.push({
        userMessage: userMsg,
        nodeSteps: nodeSteps,
        assistantMessage: assistantMessage,
      });
    }

    return turns;
  }, [messages]);

  return (
    <main className="chat-window">
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="chat-brand-logo">
            <img src={blackholeIcon} alt="GravAIty" className="blackhole-icon" width="24" height="24" />
          </div>
          <div className="chat-brand-name">GravAIty</div>
        </div>
        <div className="chat-header-center">
          {/* 主对话框区域，可以留空或添加其他内容 */}
        </div>
        <div className="chat-header-right">
          {/* 留空 */}
        </div>
        <div className="chat-header-actions">
          <SettingsMenu chatModel={chatModel} onChatModelChange={onChatModelChange} />
          <button className="chat-new-thread-btn" onClick={onNewThread}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L14.5 8.5L21 11L14.5 13.5L12 20L9.5 13.5L3 11L9.5 8.5L12 2Z" />
            </svg>
            New Chat
          </button>
        </div>
      </header>
      <div className="chat-messages">
        {turns.map((turn, idx) => (
          <TurnView
            key={turn.userMessage.id}
            userMessage={turn.userMessage}
            nodeSteps={turn.nodeSteps}
            assistantMessage={turn.assistantMessage}
          />
        ))}
        <div ref={messagesEndRef} />
        {turns.length === 0 && (
          <div className="chat-empty-hint">
            Start a conversation by typing in the box below.
          </div>
        )}
      </div>
    </main>
  );
};

export default ChatWindow;


