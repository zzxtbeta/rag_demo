import React from "react";

interface WebSearchToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
}

export function WebSearchToggle({
  enabled,
  onChange,
  disabled = false,
}: WebSearchToggleProps) {
  return (
    <button
      type="button"
      className={`websearch-toggle-inline ${enabled ? "active" : ""}`}
      onClick={() => onChange(!enabled)}
      disabled={disabled}
      title={enabled ? "Web Search: ON" : "Web Search: OFF"}
      aria-pressed={enabled}
    >
      <span className="websearch-toggle-icon" aria-hidden="true">
        🌐
      </span>
      <span className="websearch-toggle-label">Web</span>
    </button>
  );
}

export default WebSearchToggle;
