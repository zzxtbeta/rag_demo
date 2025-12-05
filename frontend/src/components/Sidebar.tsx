import type { FC } from "react";
import { useState } from "react";
import type { ThreadSummary } from "../types";

interface SidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNewThread: () => void;
  userId?: string;
  onToggleSidebar?: () => void;
}

const Sidebar: FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelect,
  onNewThread,
  userId = "zzxt",
  onToggleSidebar,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [visibleThreadIds, setVisibleThreadIds] = useState<Set<string>>(new Set());

  const formatTime = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes} min${minutes > 1 ? "s" : ""} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
    return `${days} day${days > 1 ? "s" : ""} ago`;
  };

  const toggleThreadIdVisibility = (threadId: string) => {
    setVisibleThreadIds((prev) => {
      const next = new Set(prev);
      if (next.has(threadId)) {
        next.delete(threadId);
      } else {
        next.add(threadId);
      }
      return next;
    });
  };

  const filteredThreads = threads.filter((thread) =>
    thread.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const todayThreads = filteredThreads.filter((thread) => {
    const threadDate = new Date(thread.lastUpdated);
    const today = new Date();
    return (
      threadDate.getDate() === today.getDate() &&
      threadDate.getMonth() === today.getMonth() &&
      threadDate.getFullYear() === today.getFullYear()
    );
  });

  const olderThreads = filteredThreads.filter((thread) => {
    const threadDate = new Date(thread.lastUpdated);
    const today = new Date();
    return !(
      threadDate.getDate() === today.getDate() &&
      threadDate.getMonth() === today.getMonth() &&
      threadDate.getFullYear() === today.getFullYear()
    );
  });

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-header-content">
          <span className="sidebar-threads-label">THREADS</span>
          {onToggleSidebar && (
            <button className="sidebar-toggle-btn" onClick={onToggleSidebar} title="Toggle Sidebar" aria-label="Toggle Sidebar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          )}
        </div>
      </div>
      <div className="sidebar-search">
        <input
          type="text"
          className="sidebar-search-input"
          placeholder="Q Search threads..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      <div className="sidebar-list">
        {filteredThreads.length === 0 ? (
          <div className="sidebar-empty">No threads found</div>
        ) : (
          <>
            {todayThreads.length > 0 && (
              <>
                <div className="sidebar-section-title">TODAY</div>
                {todayThreads.map((thread) => (
                  <div
                    key={thread.id}
                    className={`sidebar-thread-wrapper ${
                      thread.id === activeThreadId ? "sidebar-thread-active" : ""
                    }`}
                  >
                    <button
                      className="sidebar-thread"
                      onClick={() => onSelect(thread.id)}
                    >
                      <div className="sidebar-thread-title">{thread.title}</div>
                      <div className="sidebar-thread-time">{formatTime(thread.lastUpdated)}</div>
                    </button>
                    <button
                      className="sidebar-thread-id-toggle"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleThreadIdVisibility(thread.id);
                      }}
                      title={visibleThreadIds.has(thread.id) ? "隐藏 Thread ID" : "显示 Thread ID"}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        {visibleThreadIds.has(thread.id) ? (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                            <path d="M9 9l6 6M15 9l-6 6" />
                          </>
                        ) : (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </>
                        )}
                      </svg>
                    </button>
                    {visibleThreadIds.has(thread.id) && (
                      <div className="sidebar-thread-id">{thread.id}</div>
                    )}
                  </div>
                ))}
              </>
            )}
            {olderThreads.length > 0 && (
              <>
                {todayThreads.length > 0 && (
                  <div className="sidebar-section-title">OLDER</div>
                )}
                {olderThreads.map((thread) => (
                  <div
                    key={thread.id}
                    className={`sidebar-thread-wrapper ${
                      thread.id === activeThreadId ? "sidebar-thread-active" : ""
                    }`}
                  >
                    <button
                      className="sidebar-thread"
                      onClick={() => onSelect(thread.id)}
                    >
                      <div className="sidebar-thread-title">{thread.title}</div>
                      <div className="sidebar-thread-time">{formatTime(thread.lastUpdated)}</div>
                    </button>
                    <button
                      className="sidebar-thread-id-toggle"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleThreadIdVisibility(thread.id);
                      }}
                      title={visibleThreadIds.has(thread.id) ? "隐藏 Thread ID" : "显示 Thread ID"}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        {visibleThreadIds.has(thread.id) ? (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                            <path d="M9 9l6 6M15 9l-6 6" />
                          </>
                        ) : (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </>
                        )}
                      </svg>
                    </button>
                    {visibleThreadIds.has(thread.id) && (
                      <div className="sidebar-thread-id">{thread.id}</div>
                    )}
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">
            {userId.charAt(0).toUpperCase()}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{userId}</div>
            <div className="sidebar-user-email">yrgu.example@gmail.com</div>
          </div>
          <button className="sidebar-user-menu" aria-label="User menu">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm0 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
