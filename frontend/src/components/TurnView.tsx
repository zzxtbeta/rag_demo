import type { FC } from "react";
import NodeTimeline from "./NodeTimeline";
import type { ChatMessage, NodeStep } from "../types";

interface TurnViewProps {
  userMessage: ChatMessage;
  nodeSteps: NodeStep[];
  assistantMessage: ChatMessage | null;
}

const TurnView: FC<TurnViewProps> = ({ userMessage, nodeSteps, assistantMessage }) => {
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
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
          </div>
        </div>
      )}
    </div>
  );
};

export default TurnView;

