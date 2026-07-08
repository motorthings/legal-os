"use client";

import { useState, useCallback, DragEvent } from "react";
import { useAuth } from "@/lib/auth";

interface FileUploadProps {
  projectId: string;
  onUploadComplete: () => void;
}

export default function FileUpload({ projectId, onUploadComplete }: FileUploadProps) {
  const { session } = useAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback((newFiles: FileList | File[]) => {
    const accepted = Array.from(newFiles).filter((f) => {
      const ext = f.name.split(".").pop()?.toLowerCase();
      return ["pdf", "docx", "doc", "txt", "xlsx", "xls"].includes(ext || "");
    });
    setFiles((prev) => [...prev, ...accepted]);
  }, []);

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setUploading(true);
    setError("");

    try {
      const token = session?.access_token;
      const formData = new FormData();
      formData.append("project_id", projectId);
      files.forEach((f) => formData.append("files", f));

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/due-diligence/projects/${projectId}/upload`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );

      if (!res.ok) {
        const body = await res.text();
        throw new Error(body);
      }

      const data = await res.json();
      if (data.uploaded > 0) {
        setFiles([]);
        onUploadComplete();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
          dragOver
            ? "border-[var(--secondary)] bg-[var(--secondary-dim)]"
            : "border-[var(--border)] hover:border-[var(--border-bright)]"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("fileInput")?.click()}
      >
        <input
          id="fileInput"
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt,.xlsx,.xls"
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        <p className="text-sm text-[var(--text-dim)] mb-1">
          Drop documents here or click to browse
        </p>
        <p className="text-[11px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
          PDF, DOCX, TXT, XLSX
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-4">
          <div className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-2">
            {files.length} file{files.length > 1 ? "s" : ""} selected
          </div>
          <div className="grid gap-2 mb-4">
            {files.map((f, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-[var(--surface2)] rounded-lg px-3 py-2"
              >
                <span className="text-sm text-[var(--text)]">{f.name}</span>
                <span className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-[var(--text-muted)]">
                    {(f.size / 1024).toFixed(0)} KB
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(i);
                    }}
                    className="text-[var(--text-muted)] hover:text-[var(--rose)] bg-transparent border-0 cursor-pointer text-sm"
                  >
                    &#10005;
                  </button>
                </span>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn-primary"
          >
            {uploading ? "Uploading..." : `Upload ${files.length} file${files.length > 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {error && (
        <div className="mt-3 text-sm text-[var(--rose)]">{error}</div>
      )}
    </div>
  );
}
