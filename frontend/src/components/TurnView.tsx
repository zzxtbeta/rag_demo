import type { FC } from "react";
import { useState } from "react";
import NodeTimeline from "./NodeTimeline";
import type { ChatMessage, NodeStep } from "../types";

interface TurnViewProps {
  userMessage: ChatMessage;
  nodeSteps: NodeStep[];
  assistantMessage: ChatMessage | null;
}

const TurnView: FC<TurnViewProps> = ({ userMessage, nodeSteps, assistantMessage }) => {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  const handleCopy = async () => {
    if (assistantMessage) {
      try {
        await navigator.clipboard.writeText(assistantMessage.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (error) {
        console.error("Failed to copy:", error);
      }
    }
  };

  const handleLike = () => {
    setLiked(!liked);
    if (disliked) setDisliked(false);
  };

  const handleDislike = () => {
    setDisliked(!disliked);
    if (liked) setLiked(false);
  };

  return (
    <div className="turn-view">
      {/* User Message */}
      <div className="turn-user-message">
        <div className="message-avatar message-avatar-user">U</div>
        <div className="message-content-wrapper">
          <div className="message-header">
            <span className="message-role">You</span>
            <span className="message-time">{formatTime(userMessage.timestamp)}</span>
          </div>
          <div className="message-bubble message-bubble-user">
            {userMessage.content.split("\n").map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
          </div>
        </div>
      </div>

      {/* Node Timeline */}
      {nodeSteps.length > 0 && (
        <div className="turn-node-timeline">
          <NodeTimeline steps={nodeSteps} />
        </div>
      )}

      {/* Assistant Message */}
      {assistantMessage && (
        <div className="turn-assistant-message">
          <div className="message-avatar message-avatar-assistant">AI</div>
          <div className="message-content-wrapper">
            <div className="message-header">
              <span className="message-role">Assistant</span>
              <span className="message-time">{formatTime(assistantMessage.timestamp)}</span>
            </div>
            <div className="message-bubble message-bubble-assistant">
              {assistantMessage.content.split("\n").map((line, idx) => (
                <div key={idx}>{line}</div>
              ))}
            </div>
            <div className="message-actions">
              <button
                className={`message-action-btn ${copied ? "message-action-btn-active" : ""}`}
                onClick={handleCopy}
                title={copied ? "已复制" : "复制"}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {copied ? (
                    <>
                      <path d="M20 6L9 17l-5-5" />
                    </>
                  ) : (
                    <>
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </>
                  )}
                </svg>
                {copied ? "已复制" : "复制"}
              </button>
              <button
                className={`message-action-btn ${liked ? "message-action-btn-active" : ""}`}
                onClick={handleLike}
                title={liked ? "取消点赞" : "点赞"}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill={liked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                </svg>
                点赞
              </button>
              <button
                className={`message-action-btn ${disliked ? "message-action-btn-active" : ""}`}
                onClick={handleDislike}
                title={disliked ? "取消点踩" : "点踩"}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill={disliked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
                </svg>
                点踩
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TurnView;

