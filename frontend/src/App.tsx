import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import { ChatInputWithUpload } from "./components/ChatInputWithUpload";
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
    enableWebsearch,
    setEnableWebsearch,
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
        <ChatInputWithUpload 
          onSendMessage={sendMessage} 
          isLoading={isStreaming}
          chatModel={chatModel}
          onChatModelChange={setChatModel}
          enableWebsearch={enableWebsearch}
          onEnableWebsearchChange={setEnableWebsearch}
        />
        {isStreaming && <div className="stream-indicator">Streaming...</div>}
      </div>
    </div>
  );
}

export default App;


