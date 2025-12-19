import React, { useMemo, useRef, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "https://www.gravaity-cybernaut.top/agent";
const STORAGE_KEY_ACCESS_TOKEN = "access_token";

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem(STORAGE_KEY_ACCESS_TOKEN);
  if (token) {
    return {
      Authorization: `Bearer ${token}`,
    };
  }
  return {};
}

type TabKey = "embed" | "mineru";

type EmbedFileStatus = "embedded" | "skipped" | "error";

interface EmbedFileResult {
  index: number;
  filename: string;
  format: string;
  status: EmbedFileStatus;
  file_hash: string;
  chunks_created: number;
  message?: string | null;
  error?: string | null;
}

interface EmbedDocumentsResponse {
  status: string;
  message: string;
  collection_name: string;
  total_chunks_embedded: number;
  results: EmbedFileResult[];
}

interface MineruResponse {
  status: string;
  message: string;
  images_copied: number;
  chunks_created: number;
  embedded: boolean;
  collection_name: string;
}

const EMBED_ACCEPT = ".pdf,.txt,.md,.docx,.pptx,.xlsx,.xls";

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

export function KnowledgeBase() {
  const [activeTab, setActiveTab] = useState<TabKey>("embed");

  const [collectionName, setCollectionName] = useState<string>("");

  const [embedFiles, setEmbedFiles] = useState<File[]>([]);
  const [isEmbedding, setIsEmbedding] = useState(false);
  const [embedResponse, setEmbedResponse] = useState<EmbedDocumentsResponse | null>(null);
  const [embedError, setEmbedError] = useState<string | null>(null);

  const embedFileInputRef = useRef<HTMLInputElement | null>(null);
  const [isEmbedDragging, setIsEmbedDragging] = useState(false);

  const [mineruSourcePath, setMineruSourcePath] = useState<string>("");
  const [mineruEmbed, setMineruEmbed] = useState<boolean>(true);
  const [isMineruSubmitting, setIsMineruSubmitting] = useState(false);
  const [mineruResponse, setMineruResponse] = useState<MineruResponse | null>(null);
  const [mineruError, setMineruError] = useState<string | null>(null);

  const embedFilesLabel = useMemo(() => {
    if (embedFiles.length === 0) return "未选择文件";
    if (embedFiles.length === 1) return embedFiles[0].name;
    return `${embedFiles.length} files selected`;
  }, [embedFiles]);

  const onPickEmbedFiles = (files: FileList | null) => {
    if (!files) return;
    const arr = Array.from(files);
    setEmbedResponse(null);
    setEmbedError(null);

    if (arr.length > 4) {
      setEmbedError("最多只能选择 4 个文件");
      setEmbedFiles(arr.slice(0, 4));
      return;
    }
    setEmbedFiles(arr);
  };

  const removeEmbedFile = (index: number) => {
    setEmbedFiles((prev) => prev.filter((_, i) => i !== index));
    setEmbedResponse(null);
    setEmbedError(null);
  };

  const onDropEmbedFiles = (files: FileList | null) => {
    if (!files) return;
    onPickEmbedFiles(files);
  };

  const submitEmbed = async () => {
    setEmbedResponse(null);
    setEmbedError(null);

    if (embedFiles.length === 0) {
      setEmbedError("请先选择文件");
      return;
    }
    if (embedFiles.length > 4) {
      setEmbedError("最多只能上传 4 个文件");
      return;
    }

    const formData = new FormData();
    for (const f of embedFiles) {
      formData.append("files", f);
    }
    if (collectionName.trim()) {
      formData.append("collection_name", collectionName.trim());
    }

    try {
      setIsEmbedding(true);
      const resp = await fetch(`${API_BASE}/documents/embed`, {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
        },
        body: formData,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Embedding failed: ${resp.status} ${resp.statusText} ${text}`);
      }

      const data = (await resp.json()) as EmbedDocumentsResponse;
      setEmbedResponse(data);
    } catch (e) {
      setEmbedError(e instanceof Error ? e.message : "Embedding failed");
    } finally {
      setIsEmbedding(false);
    }
  };

  const submitMineru = async () => {
    setMineruResponse(null);
    setMineruError(null);

    if (!mineruSourcePath.trim()) {
      setMineruError("请填写 source_path（MinerU 输出目录）");
      return;
    }

    const payload: any = {
      source_path: mineruSourcePath.trim(),
      embed: mineruEmbed,
    };
    if (collectionName.trim()) {
      payload.collection_name = collectionName.trim();
    }

    try {
      setIsMineruSubmitting(true);
      const resp = await fetch(`${API_BASE}/documents/process-mineru`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`MinerU failed: ${resp.status} ${resp.statusText} ${text}`);
      }

      const data = (await resp.json()) as MineruResponse;
      setMineruResponse(data);
    } catch (e) {
      setMineruError(e instanceof Error ? e.message : "MinerU failed");
    } finally {
      setIsMineruSubmitting(false);
    }
  };

  return (
    <main className="chat-window">
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="chat-brand-name">Knowledge Base</div>
        </div>
        <div className="chat-header-center" />
        <div className="chat-header-right" />
        <div className="chat-header-actions" />
      </header>

      <div className="kb-content">
        <div className="kb-toolbar">
          <div className="kb-tabs">
            <button
              className={`kb-tab ${activeTab === "embed" ? "active" : ""}`}
              onClick={() => setActiveTab("embed")}
              type="button"
            >
              Embed Upload
            </button>
            <button
              className={`kb-tab ${activeTab === "mineru" ? "active" : ""}`}
              onClick={() => setActiveTab("mineru")}
              type="button"
            >
              MinerU Import
            </button>
          </div>

          <div className="kb-collection">
            <label className="kb-label">collection_name</label>
            <input
              className="kb-input"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="默认使用后端 VECTOR_COLLECTION"
            />
          </div>
        </div>

        {activeTab === "embed" && (
          <div className="kb-panel">
            <div className="kb-panel-header">
              <div>
                <div className="kb-panel-title">Embed Upload</div>
                <div className="kb-panel-desc">
                  直接上传文件并写入向量库。支持多格式解析，重复上传会自动去重。
                </div>
              </div>
              <div className="kb-panel-meta">
                <span className="kb-muted">最多 4 个文件</span>
                <span className="kb-muted">支持 {EMBED_ACCEPT}</span>
              </div>
            </div>

            <div className="kb-section">
              <div
                className={`kb-dropzone ${isEmbedDragging ? "dragging" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => embedFileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    embedFileInputRef.current?.click();
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsEmbedDragging(true);
                }}
                onDragLeave={() => setIsEmbedDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsEmbedDragging(false);
                  onDropEmbedFiles(e.dataTransfer.files);
                }}
                aria-disabled={isEmbedding}
              >
                <div className="kb-dropzone-title">拖拽文件到这里，或点击选择</div>
                <div className="kb-dropzone-hint">{embedFilesLabel}</div>
                <input
                  ref={embedFileInputRef}
                  className="kb-hidden-input"
                  type="file"
                  multiple
                  accept={EMBED_ACCEPT}
                  onChange={(e) => onPickEmbedFiles(e.target.files)}
                  disabled={isEmbedding}
                />
              </div>

              {embedFiles.length > 0 && (
                <div className="kb-file-list">
                  {embedFiles.map((f, idx) => (
                    <div className="kb-file-item" key={`${f.name}-${f.size}-${idx}`}>
                      <div className="kb-file-main">
                        <div className="kb-file-name">{f.name}</div>
                        <div className="kb-file-meta">{formatBytes(f.size)}</div>
                      </div>
                      <button
                        type="button"
                        className="kb-file-remove"
                        onClick={() => removeEmbedFile(idx)}
                        disabled={isEmbedding}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="kb-row">
                <button
                  type="button"
                  className="kb-primary"
                  onClick={submitEmbed}
                  disabled={isEmbedding || embedFiles.length === 0}
                >
                  {isEmbedding ? "Embedding..." : "Start Embedding"}
                </button>
                <button
                  type="button"
                  className="kb-secondary"
                  onClick={() => {
                    setEmbedFiles([]);
                    setEmbedResponse(null);
                    setEmbedError(null);
                  }}
                  disabled={isEmbedding}
                >
                  Clear
                </button>
              </div>

              {embedError && <div className="kb-error">{embedError}</div>}

              {embedResponse && (
                <div className="kb-result">
                  <div className="kb-callout kb-success">
                    <div className="kb-result-summary">
                      <div>
                        <strong>collection</strong>: {embedResponse.collection_name}
                      </div>
                      <div>
                        <strong>total_chunks_embedded</strong>: {embedResponse.total_chunks_embedded}
                      </div>
                    </div>
                  </div>

                  <div className="kb-table">
                    <div className="kb-table-header">
                      <div>File</div>
                      <div>Status</div>
                      <div>Chunks</div>
                      <div>Message</div>
                    </div>
                    {embedResponse.results.map((r) => (
                      <div key={`${r.file_hash}-${r.index}`} className="kb-table-row">
                        <div className="kb-mono">{r.filename}</div>
                        <div className={`kb-pill ${r.status}`}>{r.status}</div>
                        <div>{r.chunks_created}</div>
                        <div className="kb-muted">{r.message || r.error || ""}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "mineru" && (
          <div className="kb-panel">
            <div className="kb-panel-header">
              <div>
                <div className="kb-panel-title">MinerU Import</div>
                <div className="kb-panel-desc">
                  导入 MinerU 输出目录（含 Markdown + 图片），并按需写入向量库。
                </div>
              </div>
              <div className="kb-panel-meta">
                <span className="kb-muted">source_path 指向 MinerU 输出目录</span>
              </div>
            </div>

            <div className="kb-section">
              <div className="kb-row">
                <label className="kb-label">source_path</label>
                <input
                  className="kb-input"
                  value={mineruSourcePath}
                  onChange={(e) => setMineruSourcePath(e.target.value)}
                  placeholder="例如: D:/code/gravaity/data/ocr/xxx"
                  disabled={isMineruSubmitting}
                />
              </div>

              <div className="kb-help">
                Windows 路径建议使用正斜杠：<span className="kb-mono">D:/path/to/mineru/output</span>
              </div>

              <div className="kb-row">
                <label className="kb-checkbox">
                  <input
                    type="checkbox"
                    checked={mineruEmbed}
                    onChange={(e) => setMineruEmbed(e.target.checked)}
                    disabled={isMineruSubmitting}
                  />
                  <span>embed</span>
                </label>
              </div>

              <div className="kb-row">
                <button
                  type="button"
                  className="kb-primary"
                  onClick={submitMineru}
                  disabled={isMineruSubmitting}
                >
                  {isMineruSubmitting ? "Processing..." : "Start MinerU Import"}
                </button>
                <button
                  type="button"
                  className="kb-secondary"
                  onClick={() => {
                    setMineruResponse(null);
                    setMineruError(null);
                  }}
                  disabled={isMineruSubmitting}
                >
                  Clear
                </button>
              </div>

              {mineruError && <div className="kb-error">{mineruError}</div>}

              {mineruResponse && (
                <div className="kb-result">
                  <div className="kb-callout kb-success">
                    <div className="kb-result-summary">
                      <div>
                        <strong>images_copied</strong>: {mineruResponse.images_copied}
                      </div>
                      <div>
                        <strong>chunks_created</strong>: {mineruResponse.chunks_created}
                      </div>
                      <div>
                        <strong>embedded</strong>: {String(mineruResponse.embedded)}
                      </div>
                      <div>
                        <strong>collection</strong>: {mineruResponse.collection_name}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default KnowledgeBase;
