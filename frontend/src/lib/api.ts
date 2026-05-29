const BASE = import.meta.env.VITE_API_URL ?? ''

export interface DocumentInfo {
  filename: string
  chunks: number
  file_hash: string
}

export interface Source {
  file: string
  chunk: number
  score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  model: string
  chunks_used: number
}

export async function uploadDocument(file: File): Promise<DocumentInfo & { chars: number }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/documents/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail ?? 'Upload failed')
  }
  return res.json()
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${BASE}/documents/`)
  if (!res.ok) throw new Error('Failed to list documents')
  return res.json()
}

export async function deleteDocument(filename: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete document')
}

export async function chat(
  question: string,
  history: ChatMessage[],
  source_filter?: string
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history, source_filter: source_filter ?? null }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail ?? 'Chat request failed')
  }
  return res.json()
}

export async function healthCheck(): Promise<{ status: string; documents_indexed: number }> {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error('Backend unreachable')
  return res.json()
}
