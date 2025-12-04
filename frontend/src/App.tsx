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
  } = useChatStream("demo-user");

  return (
    <div className="app-root">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelect={switchThread}
        onNewThread={createThread}
      />
      <div className="app-main">
        <ChatWindow messages={messages} />
        <MessageInput onSend={sendMessage} disabled={false} />
        {isStreaming && <div className="stream-indicator">Streaming...</div>}
      </div>
    </div>
  );
}

export default App;


