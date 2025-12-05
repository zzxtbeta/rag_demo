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
      case "start":
        return "▶";
      case "running":
        return "⏳";
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
      case "start":
        return "#3b82f6";
      case "running":
        return "#f59e0b";
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

