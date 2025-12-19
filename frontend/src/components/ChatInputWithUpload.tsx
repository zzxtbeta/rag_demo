import React, { useState, useRef } from 'react'
import { DocumentUpload } from './DocumentUpload'
import { RetrievalToggle } from './RetrievalToggle'
import { WebSearchToggle } from './WebSearchToggle'
import { useDocumentUpload } from '../hooks/useDocumentUpload'

export interface DocumentMetadata {
  filename: string
  format: string
  markdown_content: string
}

interface ChatInputWithUploadProps {
  onSendMessage: (message: string, documents?: DocumentMetadata[]) => void
  isLoading?: boolean
  chatModel?: string
  onChatModelChange?: (model: string) => void
  enableWebsearch?: boolean
  onEnableWebsearchChange?: (enabled: boolean) => void
  enableRetrieval?: boolean
  onEnableRetrievalChange?: (enabled: boolean) => void
}

export function ChatInputWithUpload({
  onSendMessage,
  isLoading = false,
  chatModel = 'qwen-plus-latest',
  onChatModelChange,
  enableWebsearch = false,
  onEnableWebsearchChange,
  enableRetrieval = true,
  onEnableRetrievalChange,
}: ChatInputWithUploadProps) {
  const [message, setMessage] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { documents, isUploading, uploadFile, removeDocument, clearDocuments } =
    useDocumentUpload()

  const handleSendMessage = async () => {
    if (!message.trim() || isLoading || isUploading) return

    // 收集已上传的文档元数据
    const uploadedDocs: DocumentMetadata[] = documents
      .filter((doc) => doc.status === 'success' && doc.markdown_content)
      .map((doc) => ({
        filename: doc.filename,
        format: doc.format,
        markdown_content: doc.markdown_content!,
      }))

    onSendMessage(message, uploadedDocs.length > 0 ? uploadedDocs : undefined)

    // 清空输入和已上传文件
    setMessage('')
    clearDocuments()

    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Shift+Enter 换行，Enter 发送
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      // 逐个上传文件
      files.forEach((file) => uploadFile(file))
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    files.forEach((file) => uploadFile(file))
    // 重置 input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div
      className={`chat-input-wrapper ${dragOver ? 'drag-over' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* 拖拽提示 */}
      {dragOver && (
        <div className="drag-overlay">
          <div className="drag-hint">
            <span className="drag-icon">📁</span>
            <p>拖拽文件到这里上传</p>
          </div>
        </div>
      )}

      {/* 已上传文件列表 */}
      {documents.length > 0 && (
        <div className="documents-section">
          <DocumentUpload
            documents={documents}
            onRemoveDocument={removeDocument}
          />
        </div>
      )}

      {/* 输入框和控制区 */}
      <div className="input-section">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileInputChange}
          style={{ display: 'none' }}
          accept=".pdf,.pptx,.docx,.xlsx,.xls,.jpg,.jpeg,.png,.gif,.webp,.mp3,.wav,.m4a,.html,.htm,.csv,.json,.xml,.txt,.zip,.epub"
        />

        <div className="input-box">
          <textarea
            ref={textareaRef}
            className="message-input"
            placeholder="输入消息... (Shift+Enter 换行，Enter 发送) 或拖拽文件上传"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />

          <div className="input-controls-inline">
            {/* ChatModel 选择器 - 在输入框内部 */}
            {onChatModelChange && (
              <select
                value={chatModel}
                onChange={(e) => onChatModelChange(e.target.value)}
                className="model-select-inline"
                title="选择 AI 模型"
              >
                <option value="qwen-plus-latest">Qwen Plus</option>
                <option value="qwen-turbo-latest">Qwen Turbo</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-4-turbo">GPT-4 Turbo</option>
              </select>
            )}

            {onEnableWebsearchChange && (
              <WebSearchToggle
                enabled={enableWebsearch}
                onChange={onEnableWebsearchChange}
                disabled={isLoading || isUploading}
              />
            )}

            {onEnableRetrievalChange && (
              <RetrievalToggle
                enabled={enableRetrieval}
                onChange={onEnableRetrievalChange}
                disabled={isLoading || isUploading}
              />
            )}

            <button
              className="upload-button-inline"
              onClick={handleUploadClick}
              disabled={isLoading || isUploading}
              title="上传文件"
            >
              📎
              {documents.length > 0 && (
                <span className="doc-count">{documents.length}</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
