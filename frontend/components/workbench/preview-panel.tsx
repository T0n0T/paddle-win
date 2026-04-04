"use client";

type PreviewPanelProps = {
  version: number | null;
  html: string;
  formTitle: string | null;
  canRollback: boolean;
  isRollingBack: boolean;
  onRollback: () => void;
};

export function PreviewPanel({
  version,
  html,
  formTitle,
  canRollback,
  isRollingBack,
  onRollback,
}: PreviewPanelProps) {
  return (
    <section className="flex h-full min-h-[480px] flex-col rounded-[32px] border border-slate-300/70 bg-[#0f172a] p-5 text-white shadow-[0_30px_100px_rgba(15,23,42,0.25)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-teal-200/80">
            Live Preview
          </p>
          <h2 className="mt-2 text-2xl font-semibold">
            {formTitle ?? "工作台预览"}
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white/90">
            {version ? `版本 ${version}` : "尚未创建会话"}
          </span>
          <button
            type="button"
            className="rounded-full border border-white/15 bg-white/8 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/16 disabled:cursor-not-allowed disabled:text-white/40"
            onClick={onRollback}
            disabled={!canRollback || isRollingBack}
          >
            {isRollingBack ? "回滚中..." : "回滚到上一版"}
          </button>
        </div>
      </div>

      <div className="mt-5 flex flex-1 flex-col rounded-[24px] bg-white/95 p-3">
        {html ? (
          <iframe
            title="表单预览"
            srcDoc={html}
            className="min-h-[520px] w-full flex-1 rounded-[18px] border border-slate-200 bg-white"
            sandbox="allow-same-origin"
          />
        ) : (
          <div className="flex flex-1 items-center justify-center rounded-[18px] border border-dashed border-slate-300 bg-[linear-gradient(135deg,#f8fafc,#eef2ff)] p-8 text-center text-sm leading-6 text-slate-500">
            创建会话后，这里会通过受控 iframe 展示当前版本 HTML，并支持逐版回滚。
          </div>
        )}
      </div>
    </section>
  );
}
