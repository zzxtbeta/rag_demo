import { useState, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export interface UploadedDocument {
  id: string
  filename: string
  format: string
  status: 'loading' | 'success' | 'error'
  markdown_content?: string
  error?: string
}

export function useDocumentUpload() {
  const [documents, setDocuments] = useState<UploadedDocument[]>([])
  const [isUploading, setIsUploading] = useState(false)

  // 上传单个文件
  const uploadFile = useCallback(async (file: File): Promise<string | null> => {
    const docId = `${Date.now()}-${Math.random()}`
    
    setIsUploading(true)
    setDocuments((prev) => [
      ...prev,
      {
        id: docId,
        filename: file.name,
        format: file.name.split('.').pop()?.toLowerCase() || '',
        status: 'loading',
      },
    ])

    const formData = new FormData()
    formData.append('files', file)

    try {
      const response = await fetch(`${API_BASE}/documents/process-markitdown`, {
        method: 'POST',
        body: formData,
      })

      if (!response.body) {
        throw new Error('无响应体')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let markdownContent: string | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.status === 'success') {
                markdownContent = data.markdown_content
                setDocuments((prev) =>
                  prev.map((doc) =>
                    doc.id === docId
                      ? {
                          ...doc,
                          status: 'success',
                          markdown_content: data.markdown_content,
                        }
                      : doc
                  )
                )
              } else {
                setDocuments((prev) =>
                  prev.map((doc) =>
                    doc.id === docId
                      ? {
                          ...doc,
                          status: 'error',
                          error: data.error,
                        }
                      : doc
                  )
                )
              }
            } catch (e) {
              console.error('解析 SSE 数据失败:', e)
            }
          }
        }
      }

      return markdownContent
    } catch (error) {
      console.error('文件上传失败:', error)
      setDocuments((prev) =>
        prev.map((doc) =>
          doc.id === docId
            ? {
                ...doc,
                status: 'error',
                error: error instanceof Error ? error.message : '上传失败',
              }
            : doc
        )
      )
      return null
    } finally {
      setIsUploading(false)
    }
  }, [])

  // 删除已上传的文件
  const removeDocument = useCallback((docId: string) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId))
  }, [])

  // 清空所有文档
  const clearDocuments = useCallback(() => {
    setDocuments([])
  }, [])

  return {
    documents,
    isUploading,
    uploadFile,
    removeDocument,
    clearDocuments,
  }
}
