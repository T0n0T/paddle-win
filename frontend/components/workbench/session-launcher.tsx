"use client";

type SessionLauncherProps = {
  selectedFileName: string | null;
  isSubmitting: boolean;
  onFileChange: (file: File | null) => void;
  onSubmit: () => void;
};

export function SessionLauncher({
  selectedFileName,
  isSubmitting,
  onFileChange,
  onSubmit,
}: SessionLauncherProps) {
  const isDisabled = isSubmitting || !selectedFileName;

  return (
    <section className="rounded-[28px] border border-white/70 bg-white/75 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
            Session Launcher
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">
            创建编辑会话
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            当前阶段通过上传图片创建会话；创建成功后，请优先使用 run id 和源图文件名识别当前工作对象。
          </p>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-900">
          图片上传
        </span>
      </div>

      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-slate-700">
            选择表单图片
          </span>
          <input
            aria-label="选择表单图片"
            type="file"
            accept="image/*"
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          {selectedFileName ?? "尚未选择图片文件"}
        </div>

        <button
          type="submit"
          className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={isDisabled}
        >
          {isSubmitting ? "正在分析图片并重建表单..." : "创建会话"}
        </button>
      </form>
    </section>
  );
}
