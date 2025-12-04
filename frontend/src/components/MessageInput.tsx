import type { FC, FormEvent } from "react";
import { useState } from "react";

interface MessageInputProps {
  onSend: (content: string) => Promise<void>;
  disabled?: boolean;
}

const MessageInput: FC<MessageInputProps> = ({ onSend, disabled }) => {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
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

  return (
    <form className="chat-input-bar" onSubmit={handleSubmit}>
      <input
        className="chat-input"
        placeholder="Ask me anything about your documents..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled || sending}
      />
      <button
        className="chat-send-btn"
        type="submit"
        disabled={disabled || sending}
      >
        {sending ? "Sending..." : "Send"}
      </button>
    </form>
  );
};

export default MessageInput;


