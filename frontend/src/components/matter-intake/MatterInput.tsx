"use client";

import { useState, useRef } from "react";
import { Send, Upload, FileText, X, ClipboardPaste } from "lucide-react";
import { uploadFile } from "@/lib/matter-intake-api";

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
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-6">
      {/* Mode tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-[var(--border)]">
        <button
          onClick={() => setMode("paste")}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
            mode === "paste"
              ? "border-[var(--primary)] text-[var(--primary)]"
              : "border-transparent text-[var(--text-dim)] hover:text-[var(--text)]"
          }`}
        >
          <ClipboardPaste className="w-3.5 h-3.5" />
          Paste Text
        </button>
        <button
          onClick={() => setMode("upload")}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm transition-colors border-b-2 -mb-px ${
            mode === "upload"
              ? "border-[var(--primary)] text-[var(--primary)]"
              : "border-transparent text-[var(--text-dim)] hover:text-[var(--text)]"
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
            className="w-full rounded-lg border border-[var(--border-bright)] bg-[var(--surface2)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-var(--primary)/50 focus:border-transparent resize-y disabled:opacity-50 disabled:cursor-not-allowed font-mono"
          />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-[var(--text-muted)] font-mono">
              {value.length.toLocaleString()} characters · ⌘+Enter to submit
            </span>
            <button
              onClick={handleSubmit}
              disabled={disabled || !value.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-[#0a0e14] bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-lg shadow-[var(--primary)]/10"
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
              className="border-2 border-dashed border-[var(--border-bright)] rounded-lg p-8 text-center cursor-pointer hover:border-[var(--primary)]/30 hover:bg-[var(--primary)]/5 transition-colors"
            >
              <Upload className="w-8 h-8 text-[var(--text-dim)] mx-auto mb-3" />
              <p className="text-sm text-[var(--text)] font-medium mb-1">
                Drop your matter document here or click to browse
              </p>
              <p className="text-xs text-[var(--text-dim)]">
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
              <div className="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-[var(--text-dim)]">Extracting text…</span>
            </div>
          )}

          {/* Upload error */}
          {uploadError && (
            <div className="bg-var(--rose)/20 border border-[var(--rose)] rounded-lg p-4 text-sm text-[var(--rose)]">
              {uploadError}
            </div>
          )}

          {/* Extracted text preview */}
          {file && extractedText && (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[var(--primary)]" />
                  <span className="text-sm text-[var(--text)] font-medium">{file.name}</span>
                  <span className="text-xs text-[var(--text-dim)]">
                    ({extractedText.length.toLocaleString()} chars)
                  </span>
                </div>
                <button
                  onClick={clearFile}
                  className="p-1 text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="bg-[var(--surface2)] rounded-lg border border-[var(--border)] p-3 max-h-64 overflow-y-auto">
                <p className="text-sm text-[var(--text)] whitespace-pre-wrap font-mono leading-relaxed">
                  {extractedText.length > 3000
                    ? extractedText.slice(0, 3000) + "…"
                    : extractedText}
                </p>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={handleSubmit}
                  disabled={disabled || !extractedText.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-[#0a0e14] bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-lg shadow-[var(--primary)]/10"
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
