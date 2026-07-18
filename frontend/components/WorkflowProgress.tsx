"use client";

import type { StageInfo, StageStatus } from "@/types";

// ═══════════════════════════════════════════
// Stage Config
// ═══════════════════════════════════════════

const STAGE_LABELS: Record<string, string> = {
  collect: "数据采集",
  clean: "数据清洗",
  classify: "评论分类",
  extract_findings: "发现提取",
  generate_prd: "PRD 生成",
  generate_tests: "测试用例",
};

const STAGE_DESCRIPTIONS: Record<string, string> = {
  collect: "从 App Store 抓取用户评论",
  clean: "去重、过滤无效内容",
  classify: "AI 分类评论情感与主题",
  extract_findings: "提取关键洞察与发现",
  generate_prd: "生成产品需求文档",
  generate_tests: "生成对应测试用例",
};

const STAGE_ORDER = [
  "collect",
  "clean",
  "classify",
  "extract_findings",
  "generate_prd",
  "generate_tests",
];

// ═══════════════════════════════════════════
// Status Icon
// ═══════════════════════════════════════════

function StatusIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "completed":
      return (
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 text-white shadow-sm shadow-emerald-200">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </span>
      );
    case "running":
      return (
        <span className="flex h-7 w-7 items-center justify-center">
          <span className="relative flex h-6 w-6">
            <span className="absolute inset-0 rounded-full border-2 border-amber-200" />
            <span className="absolute inset-0 rounded-full border-2 border-transparent border-t-amber-500 animate-spin" />
          </span>
        </span>
      );
    case "failed":
      return (
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-red-500 text-white shadow-sm shadow-red-200">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </span>
      );
    case "pending":
    default:
      return (
        <span className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-slate-200 bg-white">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
        </span>
      );
  }
}

// ═══════════════════════════════════════════
// Duration Formatter
// ═══════════════════════════════════════════

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

// ═══════════════════════════════════════════
// WorkflowProgress Component
// ═══════════════════════════════════════════

interface WorkflowProgressProps {
  stages: Record<string, StageInfo>;
}

export default function WorkflowProgress({ stages }: WorkflowProgressProps) {
  const completedCount = STAGE_ORDER.filter(
    (k) => stages[k]?.status === "completed"
  ).length;
  const failedCount = STAGE_ORDER.filter(
    (k) => stages[k]?.status === "failed"
  ).length;

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base font-semibold text-slate-800">工作流进度</h3>
        {completedCount > 0 && (
          <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
            {completedCount}/{STAGE_ORDER.length}
          </span>
        )}
        {failedCount > 0 && (
          <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
            {failedCount} 失败
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-slate-100 rounded-full mb-6 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${(completedCount / STAGE_ORDER.length) * 100}%`,
            background: failedCount > 0
              ? "linear-gradient(90deg, #10b981, #f59e0b)"
              : "linear-gradient(90deg, #3b82f6, #8b5cf6)",
          }}
        />
      </div>

      {/* Stage list */}
      <div className="space-y-0">
        {STAGE_ORDER.map((stageKey, index) => {
          const stage = stages[stageKey];
          const isLast = index === STAGE_ORDER.length - 1;
          const isActive = stage?.status === "running";

          return (
            <div
              key={stageKey}
              className={`flex items-stretch group ${isActive ? "animate-pulse-soft" : ""}`}
            >
              {/* Connector line + icon */}
              <div className="flex flex-col items-center">
                <StatusIcon status={stage?.status ?? "pending"} />
                {!isLast && (
                  <div
                    className={`mt-0.5 w-0.5 flex-1 rounded-full transition-colors duration-500 ${
                      stage?.status === "completed"
                        ? "bg-emerald-300"
                        : stage?.status === "running"
                          ? "bg-amber-200"
                          : "bg-slate-200"
                    }`}
                  />
                )}
              </div>

              {/* Stage info */}
              <div className="ml-3 pb-5 flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-sm font-medium transition-colors duration-300 ${
                      stage?.status === "failed"
                        ? "text-red-600"
                        : stage?.status === "running"
                          ? "text-amber-600"
                          : stage?.status === "completed"
                            ? "text-emerald-700"
                            : "text-slate-400"
                    }`}
                  >
                    {STAGE_LABELS[stageKey] ?? stageKey}
                  </span>
                  {stage?.duration_ms != null &&
                    stage.status !== "pending" &&
                    stage.status !== "running" && (
                      <span className="text-[11px] text-slate-400 tabular-nums">
                        {formatDuration(stage.duration_ms)}
                      </span>
                    )}
                </div>

                {/* Description */}
                <p className="text-[11px] text-slate-400 mt-0.5 leading-tight">
                  {STAGE_DESCRIPTIONS[stageKey] ?? ""}
                </p>

                {/* Error */}
                {stage?.error && (
                  <p className="mt-1 text-[11px] text-red-500 bg-red-50 rounded-lg px-2 py-1 border border-red-100">
                    {stage.error}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}