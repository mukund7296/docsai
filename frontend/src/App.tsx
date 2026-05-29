import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import ReactMarkdown from 'react-markdown';
import { Trash2, Upload, Send, X, Loader2, AlertCircle, Sparkles } from 'lucide-react';
import * as api from './lib/api';
import type { DocumentInfo, ChatMessage, Source } from './lib/api';

// ── Types ───────────────────────────────────────────────────────────────────
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  error?: boolean;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function fileExt(name: string) {
  return name.split('.').pop()?.toUpperCase() ?? 'FILE';
}

function uid() {
  return Math.random().toString(36).slice(2);
}

// ── Components ───────────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <span key={i} className="typing-dot w-1.5 h-1.5 rounded-full bg-indigo-600" />
      ))}
    </div>
  );
}

function SourcePill({ source }: { source: Source }) {
  return (
    <span className="inline-flex items-center gap-1 font-mono text-[9px] text-zinc-500 bg-white border border-zinc-200 px-2 py-0.5 rounded-full">
      📄 {source.file} · chunk {source.chunk}
      <span className="text-indigo-600">{(source.score * 100).toFixed(0)}%</span>
    </span>
  );
}

function DocItem({
  doc,
  onDelete,
  active,
  onClick,
}: {
  doc: DocumentInfo;
  onDelete: () => void;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`group flex items-start gap-2 p-3 rounded-xl border cursor-pointer transition-all ${
        active
          ? 'bg-indigo-50 border-indigo-200'
          : 'bg-white border-zinc-200 hover:border-zinc-300'
      }`}
    >
      <span className="font-mono text-[10px] font-medium bg-zinc-100 text-zinc-600 border border-zinc-200 px-1.5 py-px rounded mt-0.5 shrink-0">
        {fileExt(doc.filename)}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-900 truncate">{doc.filename}</p>
        <p className="text-xs text-zinc-500">{doc.chunks} chunks</p>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-red-500 transition-all"
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState(true);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.listDocuments().then(setDocs).catch(() => setBackendOk(false));
    api.healthCheck().then(() => setBackendOk(true)).catch(() => setBackendOk(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const onDrop = useCallback(async (accepted: File[]) => {
    for (const file of accepted) {
      setUploadError(null);
      setUploading(file.name);
      try {
        await api.uploadDocument(file);
        const updated = await api.listDocuments();
        setDocs(updated);
      } catch (e: any) {
        setUploadError(e.message);
      } finally {
        setUploading(null);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'text/plain': ['.txt'], 'text/markdown': ['.md'] },
    maxSize: 20 * 1024 * 1024,
  });

  const handleDelete = async (filename: string) => {
    await api.deleteDocument(filename).catch(() => {});
    setDocs((prev) => prev.filter((d) => d.filename !== filename));
    if (activeFilter === filename) setActiveFilter(null);
  };

  const sendMessage = async () => {
    const q = input.trim();
    if (!q || loading) return;

    setInput('');
    const userMsg: Message = { id: uid(), role: 'user', content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const history: ChatMessage[] = messages
      .filter((m) => !m.error)
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await api.chat(q, history, activeFilter ?? undefined);
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: 'assistant', content: res.answer, sources: res.sources },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: 'assistant', content: `Error: ${e.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const totalChunks = docs.reduce((s, d) => s + d.chunks, 0);

  return (
    <div className="h-screen flex flex-col bg-zinc-50 text-zinc-900 font-sans overflow-hidden">
      {/* Header */}
      <header className="shrink-0 h-12 bg-white border-b border-zinc-200 flex items-center justify-between px-5">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <span className="font-serif text-xl tracking-tight">
            Docs<span className="text-indigo-600">AI</span>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${backendOk ? 'bg-emerald-500' : 'bg-red-500'}`} />
          <span className="text-xs text-zinc-500 font-mono">{docs.length} docs</span>

          {activeFilter && (
            <button
              onClick={() => setActiveFilter(null)}
              className="flex items-center gap-1 text-xs bg-white border border-zinc-200 px-3 py-1 rounded-full hover:bg-zinc-100 transition-colors"
            >
              {activeFilter} <X size={12} />
            </button>
          )}

          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="text-xs flex items-center gap-1.5 bg-white hover:bg-zinc-100 border border-zinc-200 px-3 py-1 rounded-lg transition-colors"
            >
              <X size={13} /> Clear
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 shrink-0 bg-white border-r border-zinc-200 flex flex-col">
          <p className="px-5 pt-4 pb-2 text-xs uppercase tracking-widest text-zinc-500 font-medium">
            Documents
          </p>

          <div
            {...getRootProps()}
            className={`mx-4 mb-4 border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
              isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-zinc-300 hover:border-zinc-400 bg-white'
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="flex items-center justify-center gap-2 text-sm text-zinc-600">
                <Loader2 size={18} className="animate-spin text-indigo-600" />
                Uploading...
              </div>
            ) : (
              <>
                <Upload size={28} className="mx-auto mb-3 text-indigo-600" />
                <p className="text-sm text-zinc-700">Drop files or click</p>
                <p className="text-xs text-zinc-500 mt-1">PDF, TXT, MD • 20MB max</p>
              </>
            )}
          </div>

          {uploadError && (
            <div className="mx-4 mb-3 p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl flex gap-2">
              <AlertCircle size={18} className="shrink-0 mt-0.5" />
              {uploadError}
            </div>
          )}

          <div className="flex-1 overflow-y-auto px-4 space-y-2 pb-4">
            {docs.length === 0 ? (
              <p className="text-center text-zinc-500 mt-10 text-sm">
                No documents yet.<br />Upload to begin.
              </p>
            ) : (
              docs.map((doc) => (
                <DocItem
                  key={doc.file_hash}
                  doc={doc}
                  active={activeFilter === doc.filename}
                  onClick={() => setActiveFilter((f) => (f === doc.filename ? null : doc.filename))}
                  onDelete={() => handleDelete(doc.filename)}
                />
              ))
            )}
          </div>

          <div className="border-t border-zinc-200 p-4 text-xs text-zinc-500">
            <div><span className="text-zinc-700">{docs.length}</span> documents</div>
            <div><span className="text-zinc-700">{totalChunks}</span> chunks indexed</div>
          </div>
        </aside>

        {/* Chat Area */}
        <div className="flex-1 flex flex-col bg-zinc-50">
          <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-violet-500 rounded-2xl flex items-center justify-center mb-6">
                  <Sparkles size={32} className="text-white" />
                </div>
                <p className="text-2xl font-serif text-zinc-800">Ask anything about your documents</p>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : ''} gap-4`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-2xl bg-white border border-zinc-200 flex items-center justify-center shrink-0">
                    <Sparkles size={16} className="text-indigo-600" />
                  </div>
                )}

                <div
                  className={`max-w-[75%] rounded-2xl px-5 py-3.5 text-[15px] leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-tr-none'
                      : msg.error
                      ? 'bg-red-50 border border-red-200 text-red-700'
                      : 'bg-white border border-zinc-200'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <p>{msg.content}</p>
                  ) : (
                    <ReactMarkdown className="prose prose-zinc max-w-none">
                      {msg.content}
                    </ReactMarkdown>
                  )}

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-zinc-100">
                      {msg.sources.map((s, i) => (
                        <SourcePill key={i} source={s} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-2xl bg-white border border-zinc-200 flex items-center justify-center">
                  <Sparkles size={16} className="text-indigo-600" />
                </div>
                <TypingIndicator />
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input Bar */}
          <div className="p-6 bg-white border-t border-zinc-200">
            <div className="flex items-end gap-2 bg-zinc-100 border border-zinc-200 focus-within:border-indigo-400 rounded-2xl px-4 py-2 transition-colors">
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
                }}
                onKeyDown={handleKeyDown}
                placeholder={
                  docs.length === 0
                    ? 'Upload a document first...'
                    : activeFilter
                    ? `Ask about ${activeFilter}...`
                    : 'Ask a question about your documents...'
                }
                className="flex-1 bg-transparent text-[15px] placeholder-zinc-500 outline-none resize-y min-h-[42px] max-h-[140px]"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="shrink-0 w-9 h-9 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl flex items-center justify-center transition-all"
              >
                {loading ? <Loader2 size={18} className="animate-spin text-white" /> : <Send size={18} className="text-white" />}
              </button>
            </div>
            <p className="text-center text-[10px] text-zinc-500 mt-3">
              Enter to send • Shift+Enter for newline
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}