import type { FC } from "react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import NodeTimeline from "./NodeTimeline";
import ImageModal from "./ImageModal";
import type { ChatMessage, NodeStep } from "../types";

interface TurnViewProps {
  userMessage: ChatMessage;
  nodeSteps: NodeStep[];
  assistantMessage: ChatMessage | null;
}

const TurnView: FC<TurnViewProps> = ({ 
  userMessage, 
  nodeSteps, 
  assistantMessage,
}) => {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [selectedImage, setSelectedImage] = useState<{ src: string; alt: string } | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<{filename: string; format: string; markdown_content: string} | null>(null);

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  const handleCopy = async () => {
    if (assistantMessage) {
      try {
        await navigator.clipboard.writeText(assistantMessage.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (error) {
        console.error("Failed to copy:", error);
      }
    }
  };

  const handleLike = () => {
    setLiked(!liked);
    if (disliked) setDisliked(false);
  };

  const handleDislike = () => {
    setDisliked(!disliked);
    if (liked) setLiked(false);
  };

  return (
    <div className="turn-view">
      {/* User Message */}
      <div className="turn-user-message">
        <div className="message-avatar message-avatar-user">U</div>
        <div className="message-content-wrapper">
          <div className="message-header">
            <span className="message-role">You</span>
            <span className="message-time">{formatTime(userMessage.timestamp)}</span>
          </div>
          <div className="message-bubble message-bubble-user">
            {(() => {
              // Extract user message content and documents
              const content = userMessage.content
              const docMarkerIndex = content.indexOf('<uploaded_documents>')
              const userContent = docMarkerIndex >= 0 ? content.substring(0, docMarkerIndex).trim() : content
              
              // Extract document metadata from content if no documents field
              const extractedDocs: Array<{filename: string; format: string; markdown_content: string}> = []
              if ((!userMessage.documents || userMessage.documents.length === 0) && docMarkerIndex >= 0) {
                const docSection = content.substring(docMarkerIndex)
                const docRegex = /<document index="\d+" filename="([^"]*)" format="([^"]*)">[\s\S]*?<\/document>/g
                const contentRegex = /<document[^>]*>([\s\S]*?)<\/document>/g
                
                let match
                let contentMatch
                const docMatches: Array<{filename: string; format: string}> = []
                const contentMatches: string[] = []
                
                while ((match = docRegex.exec(docSection)) !== null) {
                  docMatches.push({filename: match[1], format: match[2]})
                }
                
                while ((contentMatch = contentRegex.exec(docSection)) !== null) {
                  contentMatches.push(contentMatch[1].trim())
                }
                
                // Combine metadata with content
                docMatches.forEach((doc, idx) => {
                  extractedDocs.push({
                    filename: doc.filename,
                    format: doc.format,
                    markdown_content: contentMatches[idx] || ''
                  })
                })
              }
              
              const docsToDisplay: Array<{filename: string; format: string; markdown_content: string}> = userMessage.documents && userMessage.documents.length > 0 
                ? userMessage.documents.map(doc => ({
                    filename: doc.filename || '',
                    format: doc.format || '',
                    markdown_content: doc.markdown_content || ''
                  }))
                : extractedDocs
              
              return (
                <>
                  {userContent.split("\n").map((line, idx) => (
                    <div key={idx}>{line}</div>
                  ))}
                  
                  {/* Display uploaded documents as tags */}
                  {docsToDisplay.length > 0 && (
                    <div className="user-documents-section">
                      {docsToDisplay.map((doc, idx) => (
                        <div 
                          key={idx} 
                          className="document-tag"
                          onClick={() => setSelectedDocument(doc)}
                          style={{cursor: 'pointer'}}
                        >
                          <span className="document-tag-icon">📎</span>
                          <span className="document-tag-name">
                            {doc.filename || `Document ${idx + 1}`}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )
            })()}
          </div>
        </div>
      </div>

      {/* Node Timeline */}
      {nodeSteps.length > 0 && (
        <div className="turn-node-timeline">
          <NodeTimeline steps={nodeSteps} />
        </div>
      )}

      {/* Assistant Message */}
      {assistantMessage && (
        <div className="turn-assistant-message">
          <div className="message-avatar message-avatar-assistant">AI</div>
          <div className="message-content-wrapper">
            <div className="message-header">
              <span className="message-role">Assistant</span>
              <span className="message-time">{formatTime(assistantMessage.timestamp)}</span>
            </div>
            <div className="message-bubble message-bubble-assistant markdown-content">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  img: (props: any) => (
                    <img 
                      {...props} 
                      onClick={() => setSelectedImage({ src: props.src, alt: props.alt || "Image" })}
                      style={{
                        maxWidth: "100%",
                        height: "auto",
                        borderRadius: "8px",
                        cursor: "pointer",
                        transition: "transform 0.2s ease-in-out",
                      }}
                      onMouseEnter={(e) => {
                        (e.target as HTMLImageElement).style.transform = "scale(1.02)";
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLImageElement).style.transform = "scale(1)";
                      }}
                    />
                  ),
                  p: (props: any) => <p {...props} />,
                  h1: (props: any) => <h1 {...props} />,
                  h2: (props: any) => <h2 {...props} />,
                  h3: (props: any) => <h3 {...props} />,
                  h4: (props: any) => <h4 {...props} />,
                  h5: (props: any) => <h5 {...props} />,
                  h6: (props: any) => <h6 {...props} />,
                  ul: (props: any) => <ul {...props} />,
                  ol: (props: any) => <ol {...props} />,
                  li: (props: any) => <li {...props} />,
                  code: (props: any) => 
                    props.inline ? (
                      <code {...props} style={{backgroundColor: "rgba(0,0,0,0.1)", padding: "2px 4px", borderRadius: "3px", fontSize: "0.95em"}} />
                    ) : (
                      <code {...props} style={{display: "block", backgroundColor: "rgba(0,0,0,0.1)", padding: "10px", borderRadius: "6px", overflow: "auto", fontSize: "0.9em"}} />
                    ),
                  pre: (props: any) => <pre {...props} />,
                  blockquote: (props: any) => <blockquote {...props} style={{paddingLeft: "12px", borderLeft: "3px solid #666"}} />,
                  table: (props: any) => <table {...props} style={{borderCollapse: "collapse", width: "100%", fontSize: "0.95em"}} />,
                  th: (props: any) => <th {...props} style={{border: "1px solid #666", padding: "4px", textAlign: "left"}} />,
                  td: (props: any) => <td {...props} style={{border: "1px solid #666", padding: "4px"}} />,
                  hr: (props: any) => <hr {...props} />,
                  strong: (props: any) => <strong {...props} />,
                  em: (props: any) => <em {...props} />,
                }}
              >
                {assistantMessage.content}
              </ReactMarkdown>
            </div>
            <div className="message-actions-row">
              {/* 左侧：操作按钮 */}
              <div className="message-actions">
                <button
                  className={`message-action-btn ${copied ? "message-action-btn-active" : ""}`}
                  onClick={handleCopy}
                  title={copied ? "已复制" : "复制"}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {copied ? (
                      <>
                        <path d="M20 6L9 17l-5-5" />
                      </>
                    ) : (
                      <>
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </>
                    )}
                  </svg>
                  {copied ? "已复制" : "复制"}
                </button>
                <button
                  className={`message-action-btn ${liked ? "message-action-btn-active" : ""}`}
                  onClick={handleLike}
                  title={liked ? "取消点赞" : "点赞"}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill={liked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                  </svg>
                  点赞
                </button>
                <button
                  className={`message-action-btn ${disliked ? "message-action-btn-active" : ""}`}
                  onClick={handleDislike}
                  title={disliked ? "取消点踩" : "点踩"}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill={disliked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
                  </svg>
                  点踩
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Image Modal */}
      {selectedImage && (
        <ImageModal
          src={selectedImage.src}
          alt={selectedImage.alt}
          isOpen={!!selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}

      {/* Document Modal */}
      {selectedDocument && (
        <div className="document-modal-overlay" onClick={() => setSelectedDocument(null)}>
          <div className="document-modal" onClick={(e) => e.stopPropagation()}>
            <div className="document-modal-header">
              <h2>{selectedDocument.filename}</h2>
              <button 
                className="document-modal-close"
                onClick={() => setSelectedDocument(null)}
              >
                ✕
              </button>
            </div>
            <div className="document-modal-content markdown-content">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
              >
                {selectedDocument.markdown_content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TurnView;

