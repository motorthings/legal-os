"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, X, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import type { MaturityDocument } from "@/lib/maturity-types";
import { uploadDocuments } from "@/lib/maturity-api";

interface Props {
  onDocumentsUploaded: (docs: MaturityDocument[]) => void;
  existingDocs: MaturityDocument[];
  onRunAssessment: (docIds: string[]) => void;
  isAssessing: boolean;
}

const ACCEPTED_TYPES =
  ".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.pptx,.rtf,.html,.xml";
const MAX_FILES = 20;
const MAX_SIZE_MB = 10;

export default function DocumentUpload({
  onDocumentsUploaded,
  existingDocs,
  onRunAssessment,
  isAssessing,
}: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (newFiles: FileList | null) => {
      if (!newFiles) return;
      setUploadError(null);
      const selected = Array.from(newFiles);

      // Validate
      if (selected.length + files.length > MAX_FILES) {
        setUploadError(`Maximum ${MAX_FILES} files per batch`);
        return;
      }
      const oversized = selected.filter(
        (f) => f.size > MAX_SIZE_MB * 1024 * 1024
      );
      if (oversized.length > 0) {
        setUploadError(
          `Files exceed ${MAX_SIZE_MB}MB: ${oversized.map((f) => f.name).join(", ")}`
        );
        return;
      }

      setFiles((prev) => [...prev, ...selected]);
    },
    [files.length]
  );

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadDocuments(files);
      if (result.errors.length > 0) {
        setUploadError(
          `${result.errors.length} file(s) failed: ${result.errors
            .map((e) => e.filename)
            .join(", ")}`
        );
      }
      if (result.uploaded.length > 0) {
        onDocumentsUploaded(result.uploaded);
        setFiles([]);
      }
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const allDocIds = existingDocs.map((d) => d.id);

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 mb-6">
      <h3 className="text-lg font-semibold text-[var(--text)] mb-4">
        Upload Documents
      </h3>
      <p className="text-sm text-[var(--text-muted)] mb-4">
        Upload policies, playbooks, org charts, technology docs, training
        materials, process maps, and any other operational documents. The more
        context you provide, the more accurate the maturity assessment.
      </p>

      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center mb-4 transition-colors cursor-pointer ${
          dragOver
            ? "border-[var(--primary)] bg-[var(--primary-dim)]"
            : "border-[var(--border)] hover:border-[var(--text-muted)]"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="w-8 h-8 mx-auto mb-2 text-[var(--text-muted)]" />
        <p className="text-sm text-[var(--text-dim)] mb-1">
          Drop files here or click to browse
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          PDF, DOCX, TXT, MD, XLSX, PPTX, CSV, HTML, XML — max{" "}
          {MAX_SIZE_MB}MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-[var(--text-dim)] mb-2">
            Pending ({files.length})
          </p>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {files.map((file, i) => (
              <div
                key={`${file.name}-${i}`}
                className="flex items-center gap-2 text-sm text-[var(--text)] py-1 px-2 rounded hover:bg-[var(--surface2)]"
              >
                <FileText className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                <span className="truncate flex-1">{file.name}</span>
                <span className="text-xs text-[var(--text-muted)] shrink-0">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(i);
                  }}
                  className="p-0.5 text-[var(--text-muted)] hover:text-red-500 shrink-0"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-3 px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: "var(--primary)" }}
          >
            {uploading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Uploading...
              </span>
            ) : (
              `Upload ${files.length} file${files.length > 1 ? "s" : ""}`
            )}
          </button>
        </div>
      )}

      {/* Error */}
      {uploadError && (
        <div className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400 mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Existing documents */}
      {existingDocs.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-[var(--text-dim)] mb-2">
            Uploaded ({existingDocs.length})
          </p>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {existingDocs.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-2 text-sm text-[var(--text)] py-1 px-2 rounded"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                <span className="truncate flex-1">{doc.title}</span>
                <span className="text-xs text-[var(--text-muted)] shrink-0">
                  {doc.document_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Run assessment button */}
      {allDocIds.length > 0 && (
        <button
          onClick={() => onRunAssessment(allDocIds)}
          disabled={isAssessing}
          className="w-full px-4 py-3 rounded-lg text-sm font-semibold text-white transition-colors disabled:opacity-50"
          style={{ backgroundColor: "var(--primary)" }}
        >
          {isAssessing ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing {existingDocs.length} document
              {existingDocs.length > 1 ? "s" : ""}...
            </span>
          ) : (
            `Run Maturity Assessment (${existingDocs.length} document${existingDocs.length > 1 ? "s" : ""})`
          )}
        </button>
      )}
    </div>
  );
}
