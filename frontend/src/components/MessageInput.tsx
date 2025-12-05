import type { FC, FormEvent } from "react";
import { useState } from "react";
import type React from "react";

interface MessageInputProps {
  onSend: (content: string) => Promise<void>;
  disabled?: boolean;
}

const MessageInput: FC<MessageInputProps> = ({ onSend, disabled }) => {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e: FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const content = value.trim();
    if (!content || disabled || sending) return;
    setSending(true);
    try {
      await onSend(content);
      setValue("");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // 自动调整高度
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  return (
    <div className="chat-input-container">
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          placeholder="Ask me anything about LangChain..."
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled || sending}
          rows={1}
        />
      </form>
      <div className="chat-input-hint">
        <span className="hint-key">Enter</span> to send • <span className="hint-key">Shift+Enter</span> new line
      </div>
    </div>
  );
};

export default MessageInput;


