"use client";

import type { ChangeSummary, SessionTurn } from "@/lib/workbench-types";

type ChatPanelProps = {
  turns: SessionTurn[];
  summary: ChangeSummary | null;
  message: string;
  isSubmitting: boolean;
  hasSession: boolean;
  onMessageChange: (value: string) => void;
  onSubmit: () => void;
};

function SummaryList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "neutral" | "warn" | "muted";
}) {
  if (!items.length) {
    return null;
  }

  const toneClassName =
    tone === "warn"
      ? "bg-amber-50 text-amber-900 ring-amber-200"
      : tone === "muted"
        ? "bg-slate-100 text-slate-700 ring-slate-200"
        : "bg-teal-50 text-teal-900 ring-teal-200";

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
        {title}
      </p>
      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={`${title}-${item}`}
            className={`rounded-2xl px-3 py-2 text-sm ring-1 ${toneClassName}`}
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ChatPanel({
  turns,
  summary,
  message,
  isSubmitting,
  hasSession,
  onMessageChange,
  onSubmit,
}: ChatPanelProps) {
  const isDisabled = isSubmitting || !hasSession || !message.trim();

  return (
    <section className="rounded-[28px] border border-white/70 bg-white/82 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
            Conversation
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            对话与变更历史
          </h2>
        </div>
        <span className="rounded-full bg-teal-100 px-3 py-1 text-xs font-medium text-teal-900">
          {hasSession ? `${turns.length} 条记录` : "等待会话"}
        </span>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <div className="min-h-[260px] space-y-3 rounded-[24px] border border-slate-200/80 bg-slate-50/85 p-4">
          {turns.length ? (
            turns.map((turn, index) => (
              <article
                key={`${turn.user_message ?? "assistant"}-${index}`}
                className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-900">
                    版本 {index + 1}
                  </p>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
                    {turn.summary.user_intent}
                  </p>
                </div>
                {turn.user_message ? (
                  <p className="mt-3 text-sm leading-6 text-slate-700">
                    <span className="font-medium text-slate-950">用户：</span>
                    {turn.user_message}
                  </p>
                ) : null}
                {turn.assistant_message ? (
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    <span className="font-medium text-slate-900">助手：</span>
                    {turn.assistant_message}
                  </p>
                ) : null}
              </article>
            ))
          ) : (
            <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/70 px-6 text-center text-sm leading-6 text-slate-500">
              先创建会话，再通过自然语言逐轮调整表单结构与 HTML 预览。
            </div>
          )}
        </div>

        <aside className="space-y-4 rounded-[24px] border border-slate-200/80 bg-white p-4 ring-1 ring-white/80">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
              变更摘要
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-950">
              {summary?.user_intent ?? "尚未生成摘要"}
            </p>
          </div>

          <SummaryList
            title="已应用"
            items={summary?.applied ?? []}
            tone="neutral"
          />
          <SummaryList
            title="警告"
            items={summary?.warnings ?? []}
            tone="warn"
          />
          <SummaryList
            title="未解决"
            items={summary?.unresolved ?? []}
            tone="muted"
          />

          <div className="rounded-2xl bg-slate-950 px-4 py-3 text-sm text-white">
            <span className="font-semibold">触达字段：</span>
            {(summary?.touched_field_ids ?? []).join("、") || "无"}
          </div>
        </aside>
      </div>

      <form
        className="mt-5 flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-slate-700">
            请输入修改指令
          </span>
          <textarea
            aria-label="请输入修改指令"
            className="min-h-28 w-full rounded-[24px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            placeholder="例如：把姓名和手机号放在同一行，并追加备注多行输入框"
            value={message}
            onChange={(event) => onMessageChange(event.target.value)}
          />
        </label>

        <button
          type="submit"
          className="inline-flex items-center justify-center self-start rounded-2xl bg-teal-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:cursor-not-allowed disabled:bg-teal-300"
          disabled={isDisabled}
        >
          {isSubmitting ? "发送中..." : "发送修改"}
        </button>
      </form>
    </section>
  );
}
