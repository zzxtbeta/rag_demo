import type { FC } from "react";
import { useState } from "react";
import type { ThreadSummary } from "../types";

interface SidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNewThread: () => void;
  onDeleteThread: (threadId: string) => Promise<void>;
  userId?: string;
  onToggleSidebar?: () => void;
}

const Sidebar: FC<SidebarProps> = ({
  threads,
  activeThreadId,
  onSelect,
  onNewThread,
  onDeleteThread,
  userId = "zzxt",
  onToggleSidebar,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredThreadId, setHoveredThreadId] = useState<string | null>(null);
  const [menuOpenThreadId, setMenuOpenThreadId] = useState<string | null>(null);
  const [copiedThreadId, setCopiedThreadId] = useState<string | null>(null);
  const [showCopyToast, setShowCopyToast] = useState(false);

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

  const copyThreadId = async (threadId: string) => {
    try {
      await navigator.clipboard.writeText(threadId);
      setCopiedThreadId(threadId);
      setShowCopyToast(true);
      setTimeout(() => {
        setCopiedThreadId(null);
        setShowCopyToast(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to copy thread ID:", error);
      // 降级方案：使用传统方法
      const textArea = document.createElement("textarea");
      textArea.value = threadId;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        setCopiedThreadId(threadId);
        setShowCopyToast(true);
        setTimeout(() => {
          setCopiedThreadId(null);
          setShowCopyToast(false);
        }, 1000);
      } catch (err) {
        console.error("Fallback copy failed:", err);
      }
      document.body.removeChild(textArea);
    }
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
                    onMouseEnter={() => setHoveredThreadId(thread.id)}
                    onMouseLeave={() => setHoveredThreadId(null)}
                  >
                    <button
                      className="sidebar-thread"
                      onClick={() => onSelect(thread.id)}
                    >
                      <div className="sidebar-thread-title">{thread.title}</div>
                      <div className="sidebar-thread-time">{formatTime(thread.lastUpdated)}</div>
                    </button>
                    {hoveredThreadId === thread.id && (
                      <div className="sidebar-thread-menu-wrapper">
                        <button
                          className="sidebar-thread-menu-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenThreadId(menuOpenThreadId === thread.id ? null : thread.id);
                          }}
                          title="更多选项"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="19" r="2" />
                          </svg>
                        </button>
                        {menuOpenThreadId === thread.id && (
                          <div className="sidebar-thread-menu">
                            <button
                              className="sidebar-thread-menu-item"
                              onClick={(e) => {
                                e.stopPropagation();
                                copyThreadId(thread.id);
                                setMenuOpenThreadId(null);
                              }}
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                {copiedThreadId === thread.id ? (
                                  <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                                ) : (
                                  <>
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                  </>
                                )}
                              </svg>
                              {copiedThreadId === thread.id ? "已复制" : "复制 ID"}
                            </button>
                            <button
                              className="sidebar-thread-menu-item sidebar-thread-menu-item-danger"
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (confirm("确定要删除这个会话吗？此操作无法撤销。")) {
                                  try {
                                    await onDeleteThread(thread.id);
                                  } catch (error) {
                                    console.error("Failed to delete thread:", error);
                                    alert("删除失败，请重试");
                                  }
                                }
                                setMenuOpenThreadId(null);
                              }}
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              </svg>
                              删除
                            </button>
                          </div>
                        )}
                      </div>
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
                    onMouseEnter={() => setHoveredThreadId(thread.id)}
                    onMouseLeave={() => setHoveredThreadId(null)}
                  >
                    <button
                      className="sidebar-thread"
                      onClick={() => onSelect(thread.id)}
                    >
                      <div className="sidebar-thread-title">{thread.title}</div>
                      <div className="sidebar-thread-time">{formatTime(thread.lastUpdated)}</div>
                    </button>
                    {hoveredThreadId === thread.id && (
                      <div className="sidebar-thread-menu-wrapper">
                        <button
                          className="sidebar-thread-menu-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenThreadId(menuOpenThreadId === thread.id ? null : thread.id);
                          }}
                          title="更多选项"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <circle cx="12" cy="5" r="2" />
                            <circle cx="12" cy="12" r="2" />
                            <circle cx="12" cy="19" r="2" />
                          </svg>
                        </button>
                        {menuOpenThreadId === thread.id && (
                          <div className="sidebar-thread-menu">
                            <button
                              className="sidebar-thread-menu-item"
                              onClick={(e) => {
                                e.stopPropagation();
                                copyThreadId(thread.id);
                                setMenuOpenThreadId(null);
                              }}
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                {copiedThreadId === thread.id ? (
                                  <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                                ) : (
                                  <>
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                  </>
                                )}
                              </svg>
                              {copiedThreadId === thread.id ? "已复制" : "复制 ID"}
                            </button>
                            <button
                              className="sidebar-thread-menu-item sidebar-thread-menu-item-danger"
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (confirm("确定要删除这个会话吗？此操作无法撤销。")) {
                                  try {
                                    await onDeleteThread(thread.id);
                                  } catch (error) {
                                    console.error("Failed to delete thread:", error);
                                    alert("删除失败，请重试");
                                  }
                                }
                                setMenuOpenThreadId(null);
                              }}
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              </svg>
                              删除
                            </button>
                          </div>
                        )}
                      </div>
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
        {showCopyToast && (
          <div className="sidebar-copy-toast">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            已复制到剪贴板
          </div>
        )}
      </aside>
    );
  };

export default Sidebar;
