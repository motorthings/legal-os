'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import ChatMessage from './ChatMessage'
import LoadingSpinner from './LoadingSpinner'
import { authenticatedFetch, apiGet, apiPost } from '@/lib/api'
import { API_BASE_URL } from '@/lib/config'
import { logger } from '@/lib/logger'

interface Message {
  content: string
  role: 'user' | 'assistant'
  timestamp: string
}

interface ChatInterfaceProps {
  clientId?: string  // Optional - backend auto-assigns default client
  userId: string
  conversationId?: string
  apiBaseUrl?: string
  initialPromptText?: string | null
  onPromptUsed?: () => void
  onConversationCreated?: () => void
}

// Generate a cryptographically secure UUID v4
function generateUUID(): string {
  return crypto.randomUUID()
}

export default function ChatInterface({
  clientId,
  userId,
  conversationId,
  apiBaseUrl = API_BASE_URL,
  initialPromptText,
  onPromptUsed,
  onConversationCreated
}: ChatInterfaceProps) {
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(conversationId || null)
  const [attachedFiles, setAttachedFiles] = useState<File[]>([])
  const [uploadingFiles, setUploadingFiles] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<number[]>([])
  const [currentSearchIndex, setCurrentSearchIndex] = useState(0)
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null)
  const [isOnline, setIsOnline] = useState(true)
  const [streamingEnabled, setStreamingEnabled] = useState(true) // Enable streaming by default
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const searchResultRefs = useRef<(HTMLDivElement | null)[]>([])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Handle changes to conversationId prop (e.g., when clicking "New Chat" or selecting a different conversation)
  // This also handles initial mount
  useEffect(() => {
    // Update internal state when prop changes
    setCurrentConversationId(conversationId || null)

    // If there's a conversation ID, load it
    if (conversationId) {
      loadConversation(conversationId)
    } else {
      // No conversation ID means start fresh (new chat)
      setMessages([])
      setError(null)
    }
  }, [conversationId]) // Run when conversationId prop changes

  // Handle prompt text from sidebar
  useEffect(() => {
    if (initialPromptText) {
      setInput(initialPromptText)
      onPromptUsed?.()
    }
  }, [initialPromptText, onPromptUsed])

  async function loadConversation(convId?: string) {
    const idToLoad = convId || currentConversationId
    if (!idToLoad) return

    try {

      const data = await apiGet<{ messages: any[] }>(`/api/conversations/${idToLoad}/messages`)

      // Convert database messages to our Message format
      const loadedMessages: Message[] = data.messages.map((msg: any) => ({
        content: msg.content,
        role: msg.role as 'user' | 'assistant',
        timestamp: msg.timestamp
      }))

      setMessages(loadedMessages)
    } catch (err) {
      logger.error('Error loading conversation:', err)
      // Don't show error to user, just start with empty conversation
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || [])
    setAttachedFiles(prev => [...prev, ...files])
  }

  function removeAttachment(index: number) {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
  }

  async function uploadAttachments() {
    if (attachedFiles.length === 0) return []

    const uploadedDocIds: string[] = []

    try {
      setUploadingFiles(true)

      for (const file of attachedFiles) {
        // Upload file
        const formData = new FormData()
        formData.append('file', file)
        // client_id auto-assigned by backend

        const uploadResponse = await authenticatedFetch('/api/documents/upload', {
          method: 'POST',
          body: formData
        })

        if (!uploadResponse.ok) throw new Error(`Failed to upload ${file.name}`)

        const uploadData = await uploadResponse.json()
        const documentId = uploadData.document_id

        // Process file
        const processResponse = await authenticatedFetch(
          `/api/documents/${documentId}/process`,
          { method: 'POST' }
        )

        if (!processResponse.ok) throw new Error(`Failed to process ${file.name}`)

        uploadedDocIds.push(documentId)
      }

      return uploadedDocIds
    } finally {
      setUploadingFiles(false)
    }
  }

  async function sendMessage() {
    if ((!input.trim() && attachedFiles.length === 0) || loading) return

    let messageContent = input

    // Upload attachments first if any
    let uploadedDocs: string[] = []
    if (attachedFiles.length > 0) {
      try {
        uploadedDocs = await uploadAttachments()
        messageContent += `\n\nAttached: ${attachedFiles.map(f => f.name).join(', ')}`
      } catch (err) {
        setError('Failed to upload attachments')
        return
      }
    }

    const userMessage: Message = {
      content: messageContent,
      role: 'user',
      timestamp: new Date().toISOString()
    }

    // Add user message immediately
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setAttachedFiles([])
    setLoading(true)
    setError(null)

    try {
      // Create conversation if this is the first message
      let conversationIdToUse = currentConversationId

      if (!conversationIdToUse) {
        const createData = await apiPost<{ conversation_id: string }>('/api/conversations/create', {
          client_id: clientId,
          user_id: userId,
          title: 'New Conversation'
        })

        conversationIdToUse = createData.conversation_id
        setCurrentConversationId(conversationIdToUse)

        // Update URL to include the conversation ID
        router.push(`/chat?id=${conversationIdToUse}`)

        // Notify parent that a new conversation was created
        onConversationCreated?.()
      }

      // Ensure we have a conversation ID at this point
      if (!conversationIdToUse) {
        throw new Error('Failed to create or retrieve conversation ID')
      }

      if (streamingEnabled) {
        // Use streaming endpoint for better UX
        await handleStreamingResponse(userMessage.content, conversationIdToUse)
      } else {
        // Use regular endpoint for backward compatibility
        const data = await apiPost<{ message?: string; response?: string }>('/api/chat', {
          message: userMessage.content,
          client_id: clientId,
          conversation_id: conversationIdToUse,
          use_rag: true
        })

        const assistantMessage: Message = {
          content: data.message || data.response || '',
          role: 'assistant',
          timestamp: new Date().toISOString()
        }

        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      setLastFailedMessage(userMessage.content)
      logger.error('Chat error:', err)

      const errorMsg: Message = {
        content: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
        role: 'assistant',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  async function handleStreamingResponse(userContent: string, conversationIdToUse: string) {
    // Create placeholder message for streaming content
    const placeholderMessage: Message = {
      content: '',
      role: 'assistant',
      timestamp: new Date().toISOString()
    }

    // Add placeholder immediately
    let messageIndex = -1
    setMessages(prev => {
      messageIndex = prev.length
      return [...prev, placeholderMessage]
    })

    let fullResponse = ''

    try {
      const response = await authenticatedFetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userContent,
          client_id: clientId,
          conversation_id: conversationIdToUse,
          use_rag: true
        })
      })

      if (!response.ok) {
        throw new Error(`Streaming failed: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Stream not available')
      }

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true })

        // Parse SSE events (format: "data: {...}\n\n")
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6))

              if (data.type === 'token') {
                // Append token to response
                fullResponse += data.content

                // Update message in place
                setMessages(prev => {
                  const updated = [...prev]
                  if (updated[messageIndex]) {
                    updated[messageIndex] = {
                      ...updated[messageIndex],
                      content: fullResponse
                    }
                  }
                  return updated
                })
              } else if (data.type === 'done') {
                logger.debug('Stream complete:', data.tokens)
              } else if (data.type === 'error') {
                throw new Error(data.error)
              } else if (data.type === 'context') {
                logger.debug(`Using ${data.count} context chunks`)
              }
            } catch (parseError) {
              logger.warn('Failed to parse SSE data:', line, parseError)
            }
          }
        }
      }
    } catch (streamError) {
      logger.error('Streaming error:', streamError)
      throw streamError
    }
  }

  function retryLastMessage() {
    if (!lastFailedMessage) return

    setInput(lastFailedMessage)
    setLastFailedMessage(null)
    setError(null)

    // Automatically send after a brief delay
    setTimeout(() => {
      sendMessage()
    }, 100)
  }

  function handleKeyPress(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function exportConversation(format: 'markdown' | 'txt') {
    if (messages.length === 0) return

    try {
      const formatDate = (iso: string) => {
        const date = new Date(iso)
        return date.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        })
      }

      let content = ''

      if (format === 'markdown') {
        content = '# Conversation Export\n\n'
        content += `**Exported:** ${formatDate(new Date().toISOString())}\n\n`
        content += `**Messages:** ${messages.length}\n\n`
        content += '---\n\n'

        messages.forEach((msg) => {
          const role = msg.role === 'user' ? 'You' : 'Assistant'
          content += `### ${role}\n`
          content += `*${formatDate(msg.timestamp)}*\n\n`
          content += `${msg.content}\n\n`
          content += '---\n\n'
        })
      } else {
        content = 'CONVERSATION EXPORT\n'
        content += '='.repeat(50) + '\n\n'
        content += `Exported: ${formatDate(new Date().toISOString())}\n`
        content += `Messages: ${messages.length}\n\n`
        content += '='.repeat(50) + '\n\n'

        messages.forEach((msg) => {
          const role = msg.role === 'user' ? 'YOU' : 'ASSISTANT'
          content += `${role}\n`
          content += `${formatDate(msg.timestamp)}\n\n`
          content += `${msg.content}\n\n`
          content += '-'.repeat(50) + '\n\n'
        })
      }

      // Create download
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `conversation-${new Date().toISOString().split('T')[0]}.${format === 'markdown' ? 'md' : 'txt'}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      logger.error('Export failed:', err)
      setError(`Failed to export conversation. Please try again.`)
    }
  }

  // Search functionality
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setCurrentSearchIndex(0)
      return
    }

    const query = searchQuery.toLowerCase()
    const results: number[] = []

    messages.forEach((msg, index) => {
      if (msg.content.toLowerCase().includes(query)) {
        results.push(index)
      }
    })

    setSearchResults(results)
    setCurrentSearchIndex(0)

    // Scroll to first result
    if (results.length > 0) {
      setTimeout(() => {
        searchResultRefs.current[results[0]]?.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        })
      }, 100)
    }
  }, [searchQuery, messages])

  function navigateSearch(direction: 'next' | 'prev') {
    if (searchResults.length === 0) return

    let newIndex = currentSearchIndex
    if (direction === 'next') {
      newIndex = (currentSearchIndex + 1) % searchResults.length
    } else {
      newIndex = currentSearchIndex === 0 ? searchResults.length - 1 : currentSearchIndex - 1
    }

    setCurrentSearchIndex(newIndex)

    // Scroll to result
    const messageIndex = searchResults[newIndex]
    searchResultRefs.current[messageIndex]?.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    })
  }

  return (
    <div className="flex flex-col h-full page-bg">
      {/* Header with connection status */}
      {messages.length > 0 && (
        <div className="bg-card border-b border-default px-6 py-3">
          <div className="max-w-4xl mx-auto flex items-center gap-4">
            {/* Connection status */}
            <div className="flex items-center gap-1.5" title={isOnline ? 'Connected' : 'Offline'}>
              <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}></div>
            </div>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-secondary text-lg font-medium">
                Start a Conversation
              </p>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isSearchResult = searchResults.includes(index)
              const isCurrentSearchResult = searchResults[currentSearchIndex] === index

              return (
                <div
                  key={index}
                  ref={(el) => { searchResultRefs.current[index] = el }}
                  className={isCurrentSearchResult ? 'ring-2 ring-teal-500 rounded-lg' : ''}
                >
                  <ChatMessage
                    content={msg.content}
                    role={msg.role}
                    timestamp={msg.timestamp}
                  />
                </div>
              )
            })
          )}

          {/* Loading indicator */}
          {loading && (
            <div className="mb-4 flex justify-start">
              <div className="bg-hover rounded-lg px-4 py-3 max-w-[70%]">
                <LoadingSpinner type="dots" />
              </div>
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error display with retry */}
      {error && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-3">
          <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1">
              <span className="text-red-600 text-sm">⚠ {error}</span>
              {lastFailedMessage && (
                <button
                  onClick={retryLastMessage}
                  className="px-3 py-1 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
                  disabled={loading}
                >
                  Retry
                </button>
              )}
            </div>
            <button
              onClick={() => {
                setError(null)
                setLastFailedMessage(null)
              }}
              className="text-red-600 hover:opacity-70 transition-opacity font-bold"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="bg-card border-t border-default px-6 py-4 shadow-lg">
        <div className="max-w-4xl mx-auto">
          {/* Attached Files Preview */}
          {attachedFiles.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {attachedFiles.map((file, index) => (
                <div key={index} className="attachment-pill">
                  <span className="text-primary">{file.name}</span>
                  <button
                    onClick={() => removeAttachment(index)}
                    className="text-xs text-muted hover:opacity-70"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex space-x-3">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.csv,.txt"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />

            {/* Attach button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || uploadingFiles}
              className="btn-icon"
              title="Attach files"
            >
              Attach
            </button>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={loading || uploadingFiles}
              rows={4}
              className="textarea-field flex-1"
            />

            <button
              onClick={sendMessage}
              disabled={loading || uploadingFiles || (!input.trim() && attachedFiles.length === 0)}
              className="btn-primary px-6 py-3"
            >
              {uploadingFiles ? 'Uploading...' : loading ? 'Sending...' : 'Send'}
            </button>
          </div>
          <p className="form-helper">
            Attach files for this conversation • Press Enter to send • Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
