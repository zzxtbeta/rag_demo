import type { FC } from "react";
import NodeStep from "./NodeStep";
import type { NodeStep as NodeStepType } from "../types";

interface NodeTimelineProps {
  steps: NodeStepType[];
}

const NodeTimeline: FC<NodeTimelineProps> = ({ steps }) => {
  if (steps.length === 0) {
    return null;
  }

  return (
    <div className="node-timeline">
      <div className="node-timeline-header">
        <span className="node-timeline-title">Execution Process</span>
      </div>
      <div className="node-timeline-steps">
        {steps.map((step, index) => (
          <NodeStep key={step.id} step={step} isLast={index === steps.length - 1} />
        ))}
      </div>
    </div>
  );
};

export default NodeTimeline;

