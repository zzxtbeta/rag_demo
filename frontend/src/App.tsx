import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import { ChatInputWithUpload } from "./components/ChatInputWithUpload";
import KnowledgeBase from "./components/KnowledgeBase";
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
    enableRetrieval,
    setEnableRetrieval,
  } = useChatStream("zzxt");

  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [activeView, setActiveView] = useState<"chat" | "kb">("chat");

  const toggleSidebar = () => {
    setSidebarVisible((prev) => !prev);
  };

  return (
    <div className="app-root">
      {sidebarVisible && (
        <Sidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelect={async (threadId) => {
            setActiveView("chat");
            await switchThread(threadId);
          }}
          onNewThread={createThread}
          onDeleteThread={deleteThread}
          userId="zzxt"
          onToggleSidebar={toggleSidebar}
          activeView={activeView}
          onChangeView={setActiveView}
        />
      )}
      <div className="app-main">
        {activeView === "chat" ? (
          <>
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
              enableRetrieval={enableRetrieval}
              onEnableRetrievalChange={setEnableRetrieval}
            />
            {isStreaming && <div className="stream-indicator">Streaming...</div>}
          </>
        ) : (
          <KnowledgeBase />
        )}
      </div>
    </div>
  );
}

export default App;


