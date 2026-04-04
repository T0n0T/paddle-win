"use client";

type SessionLauncherProps = {
  imagePath: string;
  ocrJsonPath: string;
  isSubmitting: boolean;
  onImagePathChange: (value: string) => void;
  onOcrJsonPathChange: (value: string) => void;
  onSubmit: () => void;
};

export function SessionLauncher({
  imagePath,
  ocrJsonPath,
  isSubmitting,
  onImagePathChange,
  onOcrJsonPathChange,
  onSubmit,
}: SessionLauncherProps) {
  const isDisabled = isSubmitting || !imagePath.trim() || !ocrJsonPath.trim();

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
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-900">
          OCR 输入
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
            表单图片路径
          </span>
          <input
            aria-label="表单图片路径"
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            placeholder="/data/forms/customer.png"
            value={imagePath}
            onChange={(event) => onImagePathChange(event.target.value)}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-slate-700">
            OCR JSON 路径
          </span>
          <input
            aria-label="OCR JSON 路径"
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-950 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100"
            placeholder="/data/forms/customer.ocr.json"
            value={ocrJsonPath}
            onChange={(event) => onOcrJsonPathChange(event.target.value)}
          />
        </label>

        <button
          type="submit"
          className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={isDisabled}
        >
          {isSubmitting ? "创建中..." : "创建会话"}
        </button>
      </form>
    </section>
  );
}
