import type { FC } from "react";
import type { ThreadSummary } from "../types";

interface SidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  onSelect: (id: string) => void;
  onNewThread: () => void;
}

const Sidebar: FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelect,
  onNewThread,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-thread-btn" onClick={onNewThread}>
          + New Chat
        </button>
      </div>
      <div className="sidebar-list">
        {threads.map((thread) => (
          <button
            key={thread.id}
            className={
              "sidebar-thread" +
              (thread.id === activeThreadId ? " sidebar-thread-active" : "")
            }
            onClick={() => onSelect(thread.id)}
          >
            <div className="sidebar-thread-title">{thread.title}</div>
            <div className="sidebar-thread-time">
              {new Date(thread.lastUpdated).toLocaleTimeString()}
            </div>
          </button>
        ))}
        {threads.length === 0 && (
          <div className="sidebar-empty">No threads yet</div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;


