'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import {
  X, Plus, Send, MessageSquare,
  ThumbsUp, ThumbsDown,
  ChevronDown, ChevronRight, FileText,
} from 'lucide-react';
import { useHelpChat, HelpSource } from '@/contexts/HelpChatContext';

// ---------------------------------------------------------------------------
// Sources display
// ---------------------------------------------------------------------------

function SourcesSection({ sources }: { sources: HelpSource[] }) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-1.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-dim)] transition-colors"
      >
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <FileText className="w-3 h-3" />
        {sources.length} source{sources.length !== 1 ? 's' : ''}
      </button>
      {expanded && (
        <div className="mt-1 space-y-1">
          {sources.map((source, i) => (
            <div
              key={i}
              className="text-xs text-[var(--text-muted)] pl-4 border-l-2 border-[var(--border)]"
            >
              <span className="font-medium text-[var(--text-dim)]">{source.title}</span>
              {source.heading && (
                <span className="opacity-70">{' › '}{source.heading}</span>
              )}
              <span className="ml-1 opacity-50">
                ({Math.round(source.similarity * 100)}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Suggested questions
// ---------------------------------------------------------------------------

const SUGGESTED_QUESTIONS = [
  'How do I run a Harvey evaluation?',
  'How is the final score calculated?',
  'What is drift detection?',
  'How does the ROI framework work?',
  'What are the POC Pipeline stages?',
];

// ---------------------------------------------------------------------------
// HelpPanel
// ---------------------------------------------------------------------------

export default function HelpPanel() {
  const {
    isOpen, toggleOpen, messages,
    sendMessage, clearMessages, isTyping,
    submitFeedback,
  } = useHelpChat();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isTyping) return;
    setInput('');
    sendMessage(text);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  return (
    <>
      {/* FAB button */}
      {!isOpen && (
        <button
          onClick={toggleOpen}
          className="fixed bottom-5 right-5 z-50 w-12 h-12 rounded-full bg-[var(--primary)] text-white shadow-lg hover:opacity-90 transition-opacity flex items-center justify-center"
          title="Help"
        >
          <MessageSquare className="w-5 h-5" />
        </button>
      )}

      {/* Panel */}
      {isOpen && (
        <div className="fixed bottom-5 right-5 z-50 w-96 h-[560px] max-h-[calc(100vh-40px)] rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] shrink-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-[var(--primary)]" />
              <span className="text-sm font-semibold text-[var(--text)]">Help</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={clearMessages}
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text)] rounded-lg hover:bg-[var(--surface2)] transition-colors"
                title="New conversation"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={toggleOpen}
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text)] rounded-lg hover:bg-[var(--surface2)] transition-colors"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-xs text-[var(--text-muted)]">
                  Ask me anything about Legal AI OS. Here are some suggestions:
                </p>
                {SUGGESTED_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(q); inputRef.current?.focus(); }}
                    className="block w-full text-left text-xs text-[var(--text-dim)] hover:text-[var(--text)] px-3 py-2 rounded-lg border border-[var(--border)] hover:bg-[var(--surface2)] transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-[var(--primary)] text-white'
                      : 'bg-[var(--surface2)] text-[var(--text)] border border-[var(--border)]'
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                  {msg.sources && msg.sources.length > 0 && (
                    <SourcesSection sources={msg.sources} />
                  )}

                  {/* Feedback buttons (assistant messages only) */}
                  {msg.role === 'assistant' && !msg.id.includes('fallback') && (
                    <div className="flex items-center gap-2 mt-2 pt-1.5 border-t border-[var(--border)]">
                      <button
                        onClick={() => submitFeedback(msg.messageDbId || '', 1)}
                        className={`p-0.5 rounded transition-colors ${
                          msg.feedback === 1
                            ? 'text-green-400'
                            : 'text-[var(--text-muted)] hover:text-green-400'
                        }`}
                        title="Helpful"
                      >
                        <ThumbsUp className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => submitFeedback(msg.messageDbId || '', -1)}
                        className={`p-0.5 rounded transition-colors ${
                          msg.feedback === -1
                            ? 'text-red-400'
                            : 'text-[var(--text-muted)] hover:text-red-400'
                        }`}
                        title="Not helpful"
                      >
                        <ThumbsDown className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-[var(--surface2)] border border-[var(--border)] rounded-lg px-3 py-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="px-3 py-2 border-t border-[var(--border)] shrink-0">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about Legal AI OS..."
                className="flex-1 bg-[var(--bg)] text-[var(--text)] text-sm px-3 py-2 rounded-lg border border-[var(--border)] outline-none focus:border-[var(--primary)] placeholder:text-[var(--text-muted)]"
                disabled={isTyping}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isTyping}
                className="p-2 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-30 transition-opacity shrink-0"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
