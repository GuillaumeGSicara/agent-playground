"use client";

import { defineToolCallRenderer } from "@copilotkit/react-core/v2";
import { ToolCallStatus } from "@copilotkit/core";

function formatToolName(name: string): string {
  if (name === "web_search") return "Searching the web";
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function ToolCallIndicator({
  name,
  args,
  status,
}: {
  name: string;
  args: Record<string, unknown>;
  status: ToolCallStatus;
}) {
  const label = formatToolName(name);
  const rawQuery = typeof args?.query === "string" ? args.query : undefined;
  const query = rawQuery
    ? rawQuery.length > 30
      ? rawQuery.slice(0, 30) + "…"
      : rawQuery
    : undefined;

  if (status === ToolCallStatus.Complete) {
    return (
      <div style={styles.pill}>
        <span style={styles.checkmark}>✓</span>
        <span style={styles.labelDone}>{label}{query ? `: "${query}"` : ""}</span>
      </div>
    );
  }

  return (
    <div style={styles.pill}>
      <span
        className="cpk:animate-spin"
        style={styles.spinner}
        aria-hidden="true"
      />
      <span style={styles.label}>
        {label}
        {query ? `: "${query}"` : "…"}
      </span>
    </div>
  );
}

const styles = {
  pill: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 10px",
    borderRadius: 999,
    background: "var(--cpk-color-gray-100, #f3f4f6)",
    fontSize: 13,
    margin: "2px 0",
  },
  spinner: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    border: "2px solid var(--cpk-color-gray-400, #9ca3af)",
    borderTopColor: "transparent",
    display: "inline-block",
    flexShrink: 0,
  },
  checkmark: {
    color: "var(--cpk-color-gray-400, #9ca3af)",
    fontWeight: 600,
    lineHeight: 1,
  },
  label: { color: "var(--cpk-color-gray-600, #4b5563)" },
  labelDone: { color: "var(--cpk-color-gray-400, #9ca3af)" },
} as const;

export const toolCallRenderer = defineToolCallRenderer({
  name: "*",
  render: ({ name, args, status }) => (
    <ToolCallIndicator
      name={name}
      args={args as Record<string, unknown>}
      status={status}
    />
  ),
});
