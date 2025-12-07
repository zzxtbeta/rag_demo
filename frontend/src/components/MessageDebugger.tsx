import { useState, useEffect, type FC } from "react";
import type { ChatMessage } from "../types";

interface MessageDebuggerProps {
  threadId: string;
  messages: ChatMessage[];
}

const MessageDebugger: FC<MessageDebuggerProps> = ({ threadId, messages }) => {
  const [storedMessages, setStoredMessages] = useState<ChatMessage[]>([]);
  const [storageKey, setStorageKey] = useState<string>("");

  useEffect(() => {
    const key = `chat_messages_${threadId}`;
    setStorageKey(key);
    try {
      const stored = localStorage.getItem(key);
      if (stored) {
        const parsed = JSON.parse(stored);
        setStoredMessages(parsed);
      }
    } catch (error) {
      console.error("Failed to load from storage:", error);
    }
  }, [threadId]);

  const nodeMessages = messages.filter((msg) => msg.role === "node");
  const storedNodeMessages = storedMessages.filter((msg) => msg.role === "node");

  return (
    <div style={{ 
      position: "fixed", 
      bottom: 0, 
      right: 0, 
      width: "400px", 
      maxHeight: "500px", 
      overflow: "auto",
      background: "#1a1a1a",
      color: "#fff",
      padding: "16px",
      fontSize: "12px",
      zIndex: 10000,
      border: "1px solid #333"
    }}>
      <h3 style={{ marginTop: 0 }}>Message Debugger</h3>
      
      <div style={{ marginBottom: "16px" }}>
        <strong>Thread ID:</strong> {threadId}
      </div>
      
      <div style={{ marginBottom: "16px" }}>
        <strong>Storage Key:</strong> {storageKey}
      </div>

      <div style={{ marginBottom: "16px" }}>
        <strong>Current Messages:</strong> {messages.length}
        <br />
        <strong>Node Messages:</strong> {nodeMessages.length}
        <br />
        <strong>Stored Messages:</strong> {storedMessages.length}
        <br />
        <strong>Stored Node Messages:</strong> {storedNodeMessages.length}
      </div>

      <div style={{ marginBottom: "16px" }}>
        <strong>Node Messages in State:</strong>
        <ul style={{ margin: "8px 0", paddingLeft: "20px" }}>
          {nodeMessages.map((msg) => (
            <li key={msg.id} style={{ marginBottom: "4px" }}>
              <div>ID: {msg.id}</div>
              <div>Node: {msg.nodeName || "N/A"}</div>
              <div>Type: {msg.messageType || "N/A"}</div>
              <div>Time: {new Date(msg.timestamp).toLocaleTimeString()}</div>
            </li>
          ))}
        </ul>
      </div>

      <div style={{ marginBottom: "16px" }}>
        <strong>Node Messages in Storage:</strong>
        <ul style={{ margin: "8px 0", paddingLeft: "20px" }}>
          {storedNodeMessages.map((msg) => (
            <li key={msg.id} style={{ marginBottom: "4px" }}>
              <div>ID: {msg.id}</div>
              <div>Node: {msg.nodeName || "N/A"}</div>
              <div>Type: {msg.messageType || "N/A"}</div>
              <div>Time: {new Date(msg.timestamp).toLocaleTimeString()}</div>
            </li>
          ))}
        </ul>
      </div>

      <div style={{ marginBottom: "16px" }}>
        <strong>All Messages (sorted by timestamp):</strong>
        <ul style={{ margin: "8px 0", paddingLeft: "20px", maxHeight: "200px", overflow: "auto" }}>
          {messages
            .sort((a, b) => a.timestamp - b.timestamp)
            .map((msg) => (
              <li key={msg.id} style={{ marginBottom: "4px", fontSize: "11px" }}>
                [{msg.role}] {msg.nodeName || ""} {msg.messageType || ""} - {new Date(msg.timestamp).toLocaleTimeString()}
              </li>
            ))}
        </ul>
      </div>

      <button
        onClick={() => {
          const key = `chat_messages_${threadId}`;
          const stored = localStorage.getItem(key);
          console.log("Storage key:", key);
          console.log("Stored data:", stored);
          console.log("Parsed:", stored ? JSON.parse(stored) : null);
          console.log("Current messages:", messages);
        }}
        style={{
          padding: "8px 16px",
          background: "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer"
        }}
      >
        Log to Console
      </button>
    </div>
  );
};

export default MessageDebugger;

