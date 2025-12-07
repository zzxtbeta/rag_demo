import type { FC } from "react";
import { useState } from "react";
import type { NodeStep as NodeStepType } from "../types";

interface NodeStepProps {
  step: NodeStepType;
  isLast: boolean;
}

const NodeStep: FC<NodeStepProps> = ({ step, isLast }) => {
  const [isExpanded, setIsExpanded] = useState(step.isExpanded || false);

  const getStatusIcon = () => {
    switch (step.status) {
      case "completed":
        return "✓";
      case "error":
        return "✗";
      default:
        return "○";
    }
  };

  const getStatusColor = () => {
    switch (step.status) {
      case "completed":
        return "#10b981";
      case "error":
        return "#ef4444";
      default:
        return "#6b7280";
    }
  };

  const formatNodeName = (name: string) => {
    return name
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  return (
    <div className="node-step">
      <div className="node-step-line" style={{ borderColor: getStatusColor() }}>
        {!isLast && <div className="node-step-line-connector" />}
      </div>
      <div className="node-step-content">
        <div
          className="node-step-header"
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ cursor: step.data ? "pointer" : "default" }}
        >
          <div className="node-step-icon" style={{ color: getStatusColor() }}>
            {getStatusIcon()}
          </div>
          <div className="node-step-info">
            <div className="node-step-name">{formatNodeName(step.nodeName)}</div>
            <div className="node-step-meta">
              <span className="node-step-status" style={{ color: getStatusColor() }}>
                {step.status}
              </span>
              {step.executionTimeMs && (
                <span className="node-step-time">
                  {step.executionTimeMs.toFixed(0)}ms
                </span>
              )}
            </div>
          </div>
          {step.data && (
            <div className="node-step-toggle">
              {isExpanded ? "▼" : "▶"}
            </div>
          )}
        </div>
        {isExpanded && step.data && (
          <div className="node-step-details">
            {/* 关键信息摘要 */}
            {(step.data.token_usage || step.data.summary || step.data.execution_time_ms) && (
              <div className="node-step-summary">
                {step.data.execution_time_ms && (
                  <div className="summary-item">
                    <strong>Execution Time:</strong> {step.data.execution_time_ms.toFixed(1)}ms
                  </div>
                )}
                {step.data.token_usage && (
                  <div className="summary-item">
                    <strong>Tokens:</strong>{" "}
                    {step.data.token_usage.total_tokens > 0 ? (
                      <>
                        {step.data.token_usage.total_tokens} total 
                        ({step.data.token_usage.prompt_tokens} prompt + {step.data.token_usage.completion_tokens} completion)
                      </>
                    ) : (
                      <span style={{ color: "#9ca3af" }}>Not recorded</span>
                    )}
                  </div>
                )}
                {step.data.summary?.model && (
                  <div className="summary-item">
                    <strong>Model:</strong> {step.data.summary.model}
                  </div>
                )}
              </div>
            )}
            
            {/* 完整 JSON 数据 */}
            <pre className="node-step-json">
              {JSON.stringify(step.data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default NodeStep;

