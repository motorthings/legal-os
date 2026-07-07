'use client';

import { useState, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { logger } from '@/lib/logger';

interface ChatMessageProps {
  content: string
  role: 'user' | 'assistant'
  timestamp: string
}

// Code block component with copy button
function CodeBlock({ language, value }: { language: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);

  const handleCopy = async () => {
    try {
      // Check if Clipboard API is available
      if (!navigator.clipboard) {
        throw new Error('Clipboard API not available');
      }

      await navigator.clipboard.writeText(value);
      setCopied(true);
      setCopyError(false);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      logger.error('Failed to copy:', err);
      setCopyError(true);
      setTimeout(() => setCopyError(false), 2000);
    }
  };

  return (
    <div className="relative group">
      <button
        onClick={handleCopy}
        className={`absolute right-2 top-2 px-3 py-1 text-xs font-medium text-white rounded opacity-0 group-hover:opacity-100 transition-opacity ${
          copyError ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-700 hover:bg-gray-600'
        }`}
        title={copyError ? 'Copy failed' : 'Copy code'}
      >
        {copied ? '✓ Copied!' : copyError ? '✗ Failed' : 'Copy'}
      </button>
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: '0.5rem',
          fontSize: '0.875rem',
          padding: '1rem',
        }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
}

function ChatMessage({ content, role, timestamp }: ChatMessageProps) {
  // Format timestamp for display
  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  return (
    <div className={`mb-4 flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={role === 'user' ? 'message-user' : 'message-assistant'}>
        {role === 'assistant' ? (
          <div className="text-sm md:text-base prose prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-headings:my-3">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  const value = String(children).replace(/\n$/, '');

                  return !inline && match ? (
                    <CodeBlock language={match[1]} value={value} />
                  ) : (
                    <code className="bg-gray-200 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                      {children}
                    </code>
                  );
                },
                a({ children, href }: any) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-teal-600 hover:text-teal-700 underline"
                    >
                      {children}
                    </a>
                  );
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="text-sm md:text-base whitespace-pre-wrap break-words">
            {content}
          </div>
        )}
        <div className="message-timestamp" title={timestamp}>
          {formatTime(timestamp)}
        </div>
      </div>
    </div>
  )
}

export default memo(ChatMessage);
