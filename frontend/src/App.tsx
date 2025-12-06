import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import MessageInput from "./components/MessageInput";
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
    chatModel,
    setChatModel,
  } = useChatStream("zzxt");

  const [sidebarVisible, setSidebarVisible] = useState(true);

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
    </div>
  );
}

export default App;


