import React from 'react'
import { UploadedDocument } from '../hooks/useDocumentUpload'

interface DocumentUploadProps {
  documents: UploadedDocument[]
  onRemoveDocument: (docId: string) => void
}

export function DocumentUpload({
  documents,
  onRemoveDocument,
}: DocumentUploadProps) {
  const getFileIcon = (format: string) => {
    const fmt = format.toLowerCase()
    if (['pdf'].includes(fmt)) return '📄'
    if (['pptx', 'ppt'].includes(fmt)) return '🎯'
    if (['docx', 'doc'].includes(fmt)) return '📝'
    if (['xlsx', 'xls', 'csv'].includes(fmt)) return '📊'
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fmt)) return '🖼️'
    if (['mp3', 'wav', 'm4a'].includes(fmt)) return '🎵'
    if (['html', 'htm'].includes(fmt)) return '🌐'
    if (['json', 'xml', 'txt'].includes(fmt)) return '📋'
    if (['zip'].includes(fmt)) return '📦'
    if (['epub'].includes(fmt)) return '📚'
    return '📎'
  }

  if (documents.length === 0) return null

  return (
    <div className="document-list-inline">
      {documents.map((doc) => (
        <div key={doc.id} className="document-item-inline">
          <span className="document-icon">{getFileIcon(doc.format)}</span>
          <div className="document-info-inline">
            <div className="document-name-and-status">
              <p className="document-name-inline">{doc.filename}</p>
              {doc.status === 'loading' && (
                <span className="document-status-inline loading">⏳ 转换中...</span>
              )}
              {doc.status === 'success' && (
                <span className="document-status-inline success">✅ 已完成</span>
              )}
              {doc.status === 'error' && (
                <span className="document-status-inline error">
                  ⚠️ {doc.error || '转换失败'}
                </span>
              )}
            </div>
          </div>
          <button
            className="document-remove-inline"
            onClick={() => onRemoveDocument(doc.id)}
            title="移除"
            disabled={doc.status === 'loading'}
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
