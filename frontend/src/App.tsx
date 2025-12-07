import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import MessageInput from "./components/MessageInput";
import MessageDebugger from "./components/MessageDebugger";
import { useChatStream } from "./hooks/useChatStream";

function App() {
  const {
    activeThreadId,
    threads,
    messages,
    isStreaming,
    sendMessage,
    switchThread,
    createThread,
    deleteThread,
    updateThreadTitle,
    chatModel,
    setChatModel,
  } = useChatStream("zzxt");

  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [showDebugger, setShowDebugger] = useState(false);

  const toggleSidebar = () => {
    setSidebarVisible((prev) => !prev);
  };

  return (
    <div className="app-root">
      {sidebarVisible && (
        <Sidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelect={switchThread}
          onNewThread={createThread}
          onDeleteThread={deleteThread}
          userId="zzxt"
          onToggleSidebar={toggleSidebar}
        />
      )}
      <div className="app-main">
        <ChatWindow
          messages={messages}
          onNewThread={createThread}
          onToggleSidebar={toggleSidebar}
          chatModel={chatModel}
          onChatModelChange={setChatModel}
        />
        <MessageInput onSend={sendMessage} disabled={false} />
        {isStreaming && <div className="stream-indicator">Streaming...</div>}
      </div>
      {showDebugger && activeThreadId && (
        <MessageDebugger threadId={activeThreadId} messages={messages} />
      )}
      <button
        onClick={() => setShowDebugger(!showDebugger)}
        style={{
          position: "fixed",
          bottom: "20px",
          right: showDebugger ? "420px" : "20px",
          padding: "8px 16px",
          background: "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          zIndex: 10001,
        }}
      >
        {showDebugger ? "Hide Debugger" : "Show Debugger"}
      </button>
    </div>
  );
}

export default App;


