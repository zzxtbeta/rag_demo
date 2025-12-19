import React from "react";

interface RetrievalToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
}

export function RetrievalToggle({
  enabled,
  onChange,
  disabled = false,
}: RetrievalToggleProps) {
  return (
    <button
      type="button"
      className={`retrieval-toggle-inline ${enabled ? "active" : ""}`}
      onClick={() => onChange(!enabled)}
      disabled={disabled}
      title={enabled ? "Retrieval: ON" : "Retrieval: OFF"}
      aria-pressed={enabled}
    >
      <span className="retrieval-toggle-icon" aria-hidden="true">
        🔎
      </span>
      <span className="retrieval-toggle-label">KB</span>
    </button>
  );
}

export default RetrievalToggle;
