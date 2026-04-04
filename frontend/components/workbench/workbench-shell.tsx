"use client";

import { useState } from "react";

import { ChatPanel } from "@/components/workbench/chat-panel";
import { PreviewPanel } from "@/components/workbench/preview-panel";
import { SessionLauncher } from "@/components/workbench/session-launcher";
import {
  createSession,
  rollbackSession,
  sendMessage,
} from "@/lib/workbench-api";
import type { SessionSnapshot } from "@/lib/workbench-types";

export function WorkbenchShell() {
  const [imagePath, setImagePath] = useState("");
  const [ocrJsonPath, setOcrJsonPath] = useState("");
  const [message, setMessage] = useState("");
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);

  async function handleCreateSession() {
    if (!imagePath.trim() || !ocrJsonPath.trim()) {
      return;
    }

    try {
      setIsCreating(true);
      setError(null);
      const snapshot = await createSession({
        imagePath,
        ocrJsonPath,
      });
      setSession(snapshot);
      setMessage("");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error ? caughtError.message : "创建会话失败",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSendMessage() {
    if (!session || !message.trim()) {
      return;
    }

    try {
      setIsSending(true);
      setError(null);
      const nextSession = await sendMessage({
        sessionId: session.session_id,
        message: message.trim(),
      });
      setSession(nextSession);
      setMessage("");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error ? caughtError.message : "发送修改失败",
      );
    } finally {
      setIsSending(false);
    }
  }

  async function handleRollback() {
    if (!session || session.turns.length < 2) {
      return;
    }

    try {
      setIsRollingBack(true);
      setError(null);
      const nextSession = await rollbackSession(session.session_id);
      setSession(nextSession);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error ? caughtError.message : "回滚失败",
      );
    } finally {
      setIsRollingBack(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(45,212,191,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(251,191,36,0.18),_transparent_30%),linear-gradient(180deg,_#f8fafc_0%,_#e2e8f0_100%)] px-4 py-8 text-slate-950 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-52 bg-[linear-gradient(90deg,rgba(15,23,42,0.08),rgba(255,255,255,0))]" />

      <div className="relative mx-auto flex w-full max-w-[1600px] flex-col gap-6">
        <header className="grid gap-4 rounded-[36px] border border-white/70 bg-white/68 px-6 py-6 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">
              Paddle Win Workbench
            </p>
            <h1 className="mt-3 max-w-4xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
              OCR 重建与多轮编辑并排工作台
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              左侧负责会话创建、对话历史和变更摘要，右侧始终保持当前 HTML
              版本预览，便于快速检查每轮修改结果。
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <span className="rounded-full border border-slate-200 bg-white px-4 py-2 shadow-sm">
              Session {session?.session_id ?? "未创建"}
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-4 py-2 shadow-sm">
              {session ? `版本 ${session.version}` : "等待输入源文件"}
            </span>
          </div>
        </header>

        {error ? (
          <div className="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-800 shadow-sm">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.94fr)_minmax(420px,0.86fr)]">
          <div className="space-y-6">
            <SessionLauncher
              imagePath={imagePath}
              ocrJsonPath={ocrJsonPath}
              isSubmitting={isCreating}
              onImagePathChange={setImagePath}
              onOcrJsonPathChange={setOcrJsonPath}
              onSubmit={handleCreateSession}
            />

            <ChatPanel
              turns={session?.turns ?? []}
              summary={session?.summary ?? null}
              message={message}
              isSubmitting={isSending}
              hasSession={Boolean(session)}
              onMessageChange={setMessage}
              onSubmit={handleSendMessage}
            />
          </div>

          <PreviewPanel
            version={session?.version ?? null}
            html={session?.current_html ?? ""}
            formTitle={session?.current_form_json.title ?? null}
            canRollback={(session?.turns.length ?? 0) > 1}
            isRollingBack={isRollingBack}
            onRollback={handleRollback}
          />
        </div>
      </div>
    </main>
  );
}
