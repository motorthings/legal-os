"use client";

import { useState, useRef } from "react";
import { Send, Upload, FileText, X, ClipboardPaste } from "lucide-react";
import { uploadFile } from "@/lib/api";

interface MatterInputProps {
  onSubmit: (summary: string) => void;
  disabled: boolean;
}

type InputMode = "paste" | "upload";

export default function MatterInput({ onSubmit, disabled }: MatterInputProps) {
  const [value, setValue] = useState("");
  const [mode, setMode] = useState<InputMode>("paste");
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const text = mode === "paste" ? value.trim() : extractedText.trim();
    if (!text || disabled) return;
    onSubmit(text);
    setValue("");
    setFile(null);
    setExtractedText("");
    setUploadError("");
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setUploadError("");
    setUploading(true);
    try {
      const result = await uploadFile(selected);
      setExtractedText(result.text);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
      setExtractedText("");
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setExtractedText("");
    setUploadError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6">
      {/* Mode tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-[var(--border-default)]">
        <button
          onClick={() => setMode("paste")}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
            mode === "paste"
              ? "border-primary-500 text-primary-800 dark:text-primary-400"
              : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          <ClipboardPaste className="w-3.5 h-3.5" />
          Paste Text
        </button>
        <button
          onClick={() => setMode("upload")}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
            mode === "upload"
              ? "border-primary-500 text-primary-800 dark:text-primary-400"
              : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          }`}
        >
          <Upload className="w-3.5 h-3.5" />
          Upload Document
        </button>
      </div>

      {mode === "paste" ? (
        <>
          <textarea
            id="matter-summary"
            rows={12}
            disabled={disabled}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={`Paste the matter summary here...

Example:
"Proposed acquisition of TargetCo, Inc. by Acme Corp. Stock-for-stock transaction valued at approximately $500M. TargetCo is a Delaware corporation with operations in 12 states. Requires HSR filing and shareholder approval from both entities..."`}
            className="w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-transparent resize-y disabled:opacity-50 disabled:cursor-not-allowed font-mono"
          />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-[var(--text-tertiary)] font-mono">
              {value.length.toLocaleString()} characters · ⌘+Enter to submit
            </span>
            <button
              onClick={handleSubmit}
              disabled={disabled || !value.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-[#0a0e14] bg-primary-500 hover:bg-primary-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-lg shadow-primary-500/10"
            >
              <Send className="w-4 h-4" />
              Evaluate Matter
            </button>
          </div>
        </>
      ) : (
        <div className="space-y-4">
          {/* File drop zone */}
          {!file && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-[var(--border-strong)] rounded-lg p-8 text-center cursor-pointer hover:border-primary-500/30 hover:bg-primary-500/5 transition-colors"
            >
              <Upload className="w-8 h-8 text-[var(--text-secondary)] mx-auto mb-3" />
              <p className="text-sm text-[var(--text-primary)] font-medium mb-1">
                Drop your matter document here or click to browse
              </p>
              <p className="text-xs text-[var(--text-secondary)]">
                PDF, DOCX, XLSX, PPTX, EPUB, HTML, TXT — max 20 MB
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.epub,.html,.htm,.txt,.md,.rtf,.csv"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          )}

          {/* Uploading spinner */}
          {uploading && (
            <div className="flex items-center justify-center py-8 gap-3">
              <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-[var(--text-secondary)]">Extracting text…</span>
            </div>
          )}

          {/* Upload error */}
          {uploadError && (
            <div className="bg-red-950/20 border border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-400">
              {uploadError}
            </div>
          )}

          {/* Extracted text preview */}
          {file && extractedText && (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary-800 dark:text-primary-400" />
                  <span className="text-sm text-[var(--text-primary)] font-medium">{file.name}</span>
                  <span className="text-xs text-[var(--text-secondary)]">
                    ({extractedText.length.toLocaleString()} chars)
                  </span>
                </div>
                <button
                  onClick={clearFile}
                  className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="bg-[var(--bg-input)] rounded-lg border border-[var(--border-default)] p-3 max-h-64 overflow-y-auto">
                <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap font-mono leading-relaxed">
                  {extractedText.length > 3000
                    ? extractedText.slice(0, 3000) + "…"
                    : extractedText}
                </p>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={handleSubmit}
                  disabled={disabled || !extractedText.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-[#0a0e14] bg-primary-500 hover:bg-primary-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-lg shadow-primary-500/10"
                >
                  <Send className="w-4 h-4" />
                  Evaluate Matter
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
