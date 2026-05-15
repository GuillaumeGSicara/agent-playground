"use client";

import { useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "copilotkit-threads";
const SIDEBAR_WIDTH = 260;

interface ThreadMeta {
  id: string;
  title: string;
  createdAt: number;
}

function loadThreads(): ThreadMeta[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveThreads(threads: ThreadMeta[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(threads));
}

export function useThreadManager(activeThreadId: string | undefined) {
  const [threads, setThreads] = useState<ThreadMeta[]>([]);

  useEffect(() => {
    setThreads(loadThreads());
  }, []);

  const createThread = useCallback((): string => {
    const id = crypto.randomUUID();
    const next: ThreadMeta[] = [
      { id, title: "New conversation", createdAt: Date.now() },
      ...loadThreads(),
    ];
    saveThreads(next);
    setThreads(next);
    return id;
  }, []);

  const renameThread = useCallback((id: string, title: string): void => {
    const next = loadThreads().map((t) =>
      t.id === id ? { ...t, title } : t,
    );
    saveThreads(next);
    setThreads(next);
  }, []);

  const deleteThread = useCallback((id: string): void => {
    const next = loadThreads().filter((t) => t.id !== id);
    saveThreads(next);
    setThreads(next);
  }, []);

  useEffect(() => {
    if (!activeThreadId) return;
    const existing = loadThreads().find((t) => t.id === activeThreadId);
    if (!existing) {
      const next: ThreadMeta[] = [
        { id: activeThreadId, title: "New conversation", createdAt: Date.now() },
        ...loadThreads(),
      ];
      saveThreads(next);
      setThreads(next);
    }
  }, [activeThreadId]);

  return { threads, createThread, renameThread, deleteThread };
}

const sidebarStyle: React.CSSProperties = {
  width: SIDEBAR_WIDTH,
  minWidth: SIDEBAR_WIDTH,
  borderRight: "1px solid #e5e7eb",
  display: "flex",
  flexDirection: "column",
  background: "#f9fafb",
  overflow: "hidden",
};

const threadItemStyle = (active: boolean): React.CSSProperties => ({
  padding: "10px 14px",
  cursor: "pointer",
  borderRadius: 6,
  margin: "2px 8px",
  background: active ? "#e0e7ff" : "transparent",
  fontWeight: active ? 600 : 400,
  fontSize: 14,
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
  color: "#111827",
});

export function ThreadSidebar({
  activeThreadId,
  onSelectThread,
}: {
  activeThreadId: string | undefined;
  onSelectThread: (id: string | undefined) => void;
}) {
  const { threads, createThread, deleteThread } = useThreadManager(activeThreadId);

  const handleNew = (): void => {
    const id = createThread();
    onSelectThread(id);
  };

  return (
    <div style={sidebarStyle}>
      <div style={{ padding: "12px 8px" }}>
        <button
          onClick={handleNew}
          style={{
            width: "100%",
            padding: "8px 12px",
            background: "#4f46e5",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          + New conversation
        </button>
      </div>

      <div style={{ overflowY: "auto", flex: 1 }}>
        {threads.map((thread) => (
          <div
            key={thread.id}
            style={{
              display: "flex",
              alignItems: "center",
              margin: "2px 8px",
            }}
          >
            <div
              style={threadItemStyle(thread.id === activeThreadId)}
              onClick={() => onSelectThread(thread.id)}
              title={thread.title}
              role="button"
            >
              {thread.title}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (thread.id === activeThreadId) onSelectThread(undefined);
                deleteThread(thread.id);
              }}
              style={{
                flexShrink: 0,
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#9ca3af",
                fontSize: 16,
                lineHeight: 1,
                padding: "0 4px",
              }}
              title="Delete"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
