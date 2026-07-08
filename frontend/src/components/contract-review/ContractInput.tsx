'use client';

import { useState, useRef } from 'react';
import { Send, Upload, FileText, X } from 'lucide-react';
import { uploadContract } from '@/lib/contract-review-api';

interface Props {
  onSubmit: (text: string) => void;
  disabled: boolean;
}

export default function ContractInput({ onSubmit, disabled }: Props) {
  const [value, setValue] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const text = extractedText || value.trim();
    if (!text || disabled) return;
    onSubmit(text);
    setValue('');
    setFile(null);
    setExtractedText('');
    setUploadError('');
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setUploadError('');
    setUploading(true);
    try {
      const result = await uploadContract(selected);
      setExtractedText(result.text);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
      setExtractedText('');
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setExtractedText('');
    setUploadError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="card p-6">
      {/* Upload or paste */}
      {!file && (
        <>
          <textarea
            rows={12}
            disabled={disabled}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={`Paste a contract clause or full contract text here...

Or click below to upload a document (PDF, DOCX, etc.)`}
            className="w-full rounded-lg border border-[var(--border)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 focus:border-transparent resize-y disabled:opacity-50 font-mono"
            style={{ background: 'var(--surface2)' }}
          />
          <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--text-dim)] border border-[var(--border)] hover:border-[var(--primary)] transition-colors disabled:opacity-50"
              >
                <Upload className="w-3.5 h-3.5" />
                Upload Document
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md,.rtf,.html"
                onChange={handleFileChange}
                className="hidden"
              />
              <span className="text-xs text-[var(--text-muted)] font-mono">{value.length.toLocaleString()} chars</span>
            </div>
            <button
              onClick={handleSubmit}
              disabled={disabled || !value.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
              Analyze Contract
            </button>
          </div>
        </>
      )}

      {/* Uploading */}
      {uploading && (
        <div className="flex items-center justify-center py-12 gap-3">
          <div className="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-[var(--text-dim)]">Extracting text...</span>
        </div>
      )}

      {/* Upload error */}
      {uploadError && (
        <div className="bg-[var(--rose)]/10 border border-[var(--rose)] rounded-lg p-4 text-sm text-[var(--rose)]">
          {uploadError}
          <button onClick={clearFile} className="ml-3 underline text-xs">Dismiss</button>
        </div>
      )}

      {/* Extracted text preview */}
      {file && extractedText && (
        <>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-[var(--primary)]" />
              <span className="text-sm text-[var(--text)] font-medium">{file.name}</span>
              <span className="text-xs text-[var(--text-muted)]">({extractedText.length.toLocaleString()} chars)</span>
            </div>
            <button onClick={clearFile} className="p-1 text-[var(--text-dim)] hover:text-[var(--text)] transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="rounded-lg border border-[var(--border)] p-3 max-h-64 overflow-y-auto" style={{ background: 'var(--surface2)' }}>
            <p className="text-sm text-[var(--text)] whitespace-pre-wrap font-mono leading-relaxed">
              {extractedText.length > 3000 ? extractedText.slice(0, 3000) + '...' : extractedText}
            </p>
          </div>
          <div className="flex justify-end mt-3">
            <button
              onClick={handleSubmit}
              disabled={disabled || !extractedText.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 transition-colors"
            >
              <Send className="w-4 h-4" />
              Analyze Contract
            </button>
          </div>
        </>
      )}
    </div>
  );
}
