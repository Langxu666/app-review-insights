"use client";

import { useState, useCallback, useRef, useEffect, type DragEvent, type ChangeEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/services/api";
import { analyzeReviewsStreaming } from "@/services/api";
import type { SSEEvent } from "@/services/api";
import type { AnalyzeResponse, Artifacts, StageStatus } from "@/types";

import WorkflowProgress from "@/components/WorkflowProgress";
import ArtifactTabs from "@/components/ArtifactTabs";

// ═══════════════════════════════════════════
// Types
// ═══════════════════════════════════════════

type DataSource = "appstore" | "import";

// ═══════════════════════════════════════════
// Icons (inline SVGs for zero-dependency)
// ═══════════════════════════════════════════

const Icons = {
  chart: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  ),
  edit: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
  ),
  cog: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
  ),
  document: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  ),
  search: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  ),
  refresh: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  ),
  alert: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  ),
  check: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
  ),
  close: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  ),
  chevronRight: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  ),
  sparkles: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  ),
  upload: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  ),
  fileIcon: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  ),
  trash: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  ),
  paste: (
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
  ),
};

function SvgIcon({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      {children}
    </svg>
  );
}

// ═══════════════════════════════════════════
// Health Badge
// ═══════════════════════════════════════════

function HealthBadge() {
  const { data: healthStatus, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data } = await api.get("/api/health");
      return data;
    },
    refetchInterval: 30_000,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm animate-pulse-soft">
        <span className="w-2 h-2 bg-gray-400 rounded-full" />
        <span className="text-gray-500">检测中...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-red-50 text-red-700 rounded-full text-sm border border-red-200">
        <span className="w-2 h-2 bg-red-500 rounded-full" />
        后端服务离线
      </div>
    );
  }

  if (healthStatus) {
    return (
      <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-sm border border-emerald-200">
        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
        后端服务正常
      </div>
    );
  }

  return null;
}

// ═══════════════════════════════════════════
// Loading State — Stage-aware spinner
// ═══════════════════════════════════════════

const STAGE_LABELS: Record<string, string> = {
  collect: "正在采集评论数据...",
  clean: "正在清洗数据...",
  classify: "正在分类评论...",
  extract_findings: "正在提取关键发现...",
  generate_prd: "正在生成产品需求文档...",
  generate_tests: "正在生成测试用例...",
};

function LoadingState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
      <div className="relative">
        <div className="w-20 h-20 rounded-full border-[3px] border-slate-100" />
        <div className="absolute inset-0 w-20 h-20 rounded-full border-[3px] border-transparent border-t-blue-500 border-r-blue-400 animate-spin" />
        <div className="absolute inset-2 w-16 h-16 rounded-full border-[3px] border-transparent border-b-purple-400 border-l-purple-300 animate-spin-slow" />
        <div className="absolute inset-0 flex items-center justify-center">
          <SvgIcon className="w-7 h-7 text-blue-500 animate-pulse-soft">
            {Icons.sparkles}
          </SvgIcon>
        </div>
      </div>

      <p className="mt-6 text-base font-medium text-slate-700">{message}</p>
      <p className="mt-2 text-sm text-slate-400 max-w-xs text-center">
        分析过程约需 2-5 分钟，请耐心等待
      </p>
    </div>
  );
}

// ═══════════════════════════════════════════
// Empty State — Before any analysis
// ═══════════════════════════════════════════

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
      <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center mb-6">
        <SvgIcon className="w-10 h-10 text-slate-300">
          {Icons.search}
        </SvgIcon>
      </div>
      <h3 className="text-lg font-semibold text-slate-700">准备开始分析</h3>
      <p className="text-sm text-slate-400 mt-1.5 text-center max-w-sm">
        输入 App Store 链接和分析目标，点击「开始分析」即可自动采集评论、分类、提取洞察并生成 PRD
      </p>
      <div className="mt-6 grid grid-cols-3 gap-3 text-center">
        {[
          { icon: Icons.chart, label: "数据采集", desc: "自动抓取评论" },
          { icon: Icons.sparkles, label: "智能分析", desc: "AI 分类洞察" },
          { icon: Icons.document, label: "PRD 生成", desc: "需求文档输出" },
        ].map((item) => (
          <div key={item.label} className="flex flex-col items-center gap-2 p-3 rounded-xl bg-slate-50 border border-slate-100">
            <SvgIcon className="w-5 h-5 text-slate-400">{item.icon}</SvgIcon>
            <span className="text-xs font-medium text-slate-600">{item.label}</span>
            <span className="text-[10px] text-slate-400">{item.desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════
// Error Alert — With retry
// ═══════════════════════════════════════════

function ErrorAlert({
  message,
  onDismiss,
  onRetry,
}: {
  message: string;
  onDismiss: () => void;
  onRetry?: () => void;
}) {
  return (
    <div className="flex items-start gap-4 p-5 bg-red-50 border border-red-200 rounded-2xl animate-slide-up" role="alert">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
        <SvgIcon className="w-5 h-5 text-red-500">{Icons.alert}</SvgIcon>
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-semibold text-red-800">分析出错</h4>
        <p className="mt-1 text-sm text-red-600">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
          >
            <SvgIcon className="w-3.5 h-3.5">{Icons.refresh}</SvgIcon>
            重试
          </button>
        )}
      </div>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors p-1"
        aria-label="关闭"
      >
        <SvgIcon className="w-5 h-5">{Icons.close}</SvgIcon>
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════
// Stat Item
// ═══════════════════════════════════════════

function StatItem({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 text-center border border-slate-100 hover:border-slate-200 transition-colors">
      <div className={`text-xl font-bold ${color ?? "text-slate-800"}`}>{value}</div>
      <div className="text-[11px] text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}min ${seconds}s`;
}

// ═══════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════

function tryParsePreview(data: string): { count: number; preview: string } {
  const trimmed = data.trim();
  if (!trimmed) return { count: 0, preview: "" };

  // Try JSON first
  if (trimmed[0] === "[" || trimmed[0] === "{") {
    try {
      let parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === "object" && "reviews" in parsed && Array.isArray(parsed.reviews)) {
        parsed = parsed.reviews;
      }
      if (Array.isArray(parsed)) {
        const count = parsed.length;
        const preview = JSON.stringify(parsed.slice(0, 3), null, 2);
        return { count, preview };
      }
    } catch { /* fall through */ }
  }

  // Try CSV
  const lines = trimmed.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length > 1) {
    const header = lines[0];
    if (header.includes(",") && header.toLowerCase().includes("content")) {
      return { count: lines.length - 1, preview: lines.slice(0, 4).join("\n") };
    }
  }

  return { count: 0, preview: trimmed.slice(0, 500) };
}

function parseReviewCount(data: string): number {
  return tryParsePreview(data).count;
}

// ═══════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════

export default function Home() {
  // ── Common state ──
  const [url, setUrl] = useState("");
  const [analysisGoal, setAnalysisGoal] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [response, setResponse] = useState<AnalyzeResponse | null>(null);
  const [artifacts, setArtifacts] = useState<Artifacts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stageStates, setStageStates] = useState<Record<string, StageStatus>>({});

  // ── Data source toggle ──
  const [dataSource, setDataSource] = useState<DataSource>("appstore");

  // ── Import states ──
  const [importData, setImportData] = useState("");
  const [importFileName, setImportFileName] = useState("");
  const [importPreview, setImportPreview] = useState<{ count: number; preview: string } | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [isHoverCancel, setIsHoverCancel] = useState(false);

  // ── Cleanup on unmount ──
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ── File handling helpers ──
  const readFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setImportData(text);
      setImportFileName(file.name);
      const parsed = tryParsePreview(text);
      setImportPreview(parsed);
    };
    reader.readAsText(file);
  }, []);

  const handleFileChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) readFile(file);
  }, [readFile]);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) readFile(file);
  }, [readFile]);

  const handleClearImport = useCallback(() => {
    setImportData("");
    setImportFileName("");
    setImportPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // ── Cancel ──
  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // ── Analyze ──
  const handleAnalyze = useCallback(async () => {
    if (dataSource === "import") {
      if (!importData.trim()) {
        setError("请上传文件或粘贴数据后再开始分析");
        return;
      }
    } else {
      if (!url.trim()) return;
    }

    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsAnalyzing(true);
    setResponse(null);
    setArtifacts(null);
    setError(null);
    setStageStates({});

    try {
      const result = await analyzeReviewsStreaming(
        dataSource === "appstore" ? url.trim() : undefined,
        analysisGoal.trim() || undefined,
        dataSource === "import" ? importData : undefined,
        (event: SSEEvent) => {
          if (event.event === "start") {
            // Initialize all stages as pending
            const initial: Record<string, StageStatus> = {};
            for (const key of Object.keys(event.stages)) {
              initial[key] = "pending";
            }
            setStageStates(initial);
          } else if (event.event === "stage_update") {
            setStageStates((prev) => ({
              ...prev,
              [event.stage]: event.status as StageStatus,
            }));
          }
          // 'complete' event is handled by the promise resolution
        },
        controller.signal,
      );
      setResponse(result);
      if (result.artifacts_data) {
        setArtifacts(result.artifacts_data);
      }
      if (result.status === "failed") {
        setError(result.error ?? "分析过程中出现错误，请查看工作流进度了解详情。");
      }
    } catch (err) {
      // Silently ignore cancelled requests
      if (controller.signal.aborted) return;
      const message =
        err instanceof Error ? err.message : "分析请求失败，请检查网络连接后重试。";
      setError(message);
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      setIsAnalyzing(false);
    }
  }, [url, analysisGoal, dataSource, importData]);

  const canSubmit = dataSource === "import" ? !!importData.trim() : !!url.trim();

  const hasResults = response !== null;
  const hasArtifacts = artifacts !== null;

  // Build StageInfo from streaming stageStates for WorkflowProgress
  const streamingStages: Record<string, { status: StageStatus; started_at: null; completed_at: null; duration_ms: null; error: null }> | null =
    isAnalyzing && Object.keys(stageStates).length > 0
      ? Object.fromEntries(
          Object.entries(stageStates).map(([key, status]) => [
            key,
            { status, started_at: null, completed_at: null, duration_ms: null, error: null },
          ]),
        )
      : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
        {/* ── Header ── */}
        <header className="text-center mb-8 sm:mb-12">
          <div className="inline-flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 bg-gradient-to-br from-blue-600 to-violet-600 rounded-2xl mb-4 shadow-lg shadow-blue-200/50">
            <SvgIcon className="w-7 h-7 sm:w-8 sm:h-8 text-white">{Icons.chart}</SvgIcon>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
            App Review Insights
          </h1>
          <p className="text-slate-500 mt-2 text-sm sm:text-base">
            智能分析应用商店评论，提取有价值的洞察信息
          </p>
          <HealthBadge />
        </header>

        {/* ── Input Section ── */}
        <section
          className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 p-6 sm:p-8 mb-6 sm:mb-8 animate-fade-in"
          aria-label="分析输入"
        >
          <h2 className="text-lg sm:text-xl font-semibold text-slate-800 mb-5 flex items-center gap-2">
            <SvgIcon className="w-5 h-5 text-blue-600">{Icons.edit}</SvgIcon>
            输入分析信息
          </h2>

          {/* ── Data Source Toggle ── */}
          <div className="flex bg-slate-100 rounded-xl p-1 mb-5">
            <button
              onClick={() => setDataSource("appstore")}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
                dataSource === "appstore"
                  ? "bg-white text-slate-800 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <SvgIcon className="w-4 h-4">{Icons.search}</SvgIcon>
                从 App Store 采集
              </span>
            </button>
            <button
              onClick={() => setDataSource("import")}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
                dataSource === "import"
                  ? "bg-white text-slate-800 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <SvgIcon className="w-4 h-4">{Icons.upload}</SvgIcon>
                导入数据
              </span>
            </button>
          </div>

          <div className="space-y-4">
            {/* ── App Store mode ── */}
            {dataSource === "appstore" && (
              <>
                <div>
                  <label htmlFor="url" className="block text-sm font-medium text-slate-700 mb-1.5">
                    App Store URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="url"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && url.trim()) handleAnalyze();
                    }}
                    placeholder="https://apps.apple.com/cn/app/xxx/id1234567890"
                    disabled={isAnalyzing}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm
                      focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                      transition-all duration-200 placeholder:text-slate-400
                      disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>

                <div>
                  <label htmlFor="goal" className="block text-sm font-medium text-slate-700 mb-1.5">
                    分析目标
                    <span className="text-slate-400 font-normal ml-1">（可选）</span>
                  </label>
                  <input
                    id="goal"
                    type="text"
                    value={analysisGoal}
                    onChange={(e) => setAnalysisGoal(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && url.trim()) handleAnalyze();
                    }}
                    placeholder="例如：用户反馈分析、功能建议提取、Bug 报告汇总"
                    disabled={isAnalyzing}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm
                      focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                      transition-all duration-200 placeholder:text-slate-400
                      disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>
              </>
            )}

            {/* ── Import mode ── */}
            {dataSource === "import" && (
              <div className="space-y-4">
                {/* File upload area */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={handleDrop}
                  className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer ${
                    isDragOver
                      ? "border-blue-400 bg-blue-50/50"
                      : importData
                        ? "border-emerald-300 bg-emerald-50/30"
                        : "border-slate-300 bg-slate-50/50 hover:border-slate-400"
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,.csv"
                    onChange={handleFileChange}
                    className="hidden"
                    aria-label="选择文件"
                  />

                  {importData ? (
                    <div className="flex items-center justify-center gap-3">
                      <SvgIcon className="w-5 h-5 text-emerald-600">{Icons.check}</SvgIcon>
                      <span className="text-sm font-medium text-emerald-700">
                        {importFileName || "已加载数据"}
                      </span>
                      <span className="text-xs text-emerald-500">
                        ({importPreview?.count ?? 0} 条评论)
                      </span>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleClearImport(); }}
                        className="ml-2 p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="清除"
                      >
                        <SvgIcon className="w-4 h-4">{Icons.trash}</SvgIcon>
                      </button>
                    </div>
                  ) : (
                    <>
                      <SvgIcon className="w-8 h-8 text-slate-400 mx-auto mb-2">{Icons.upload}</SvgIcon>
                      <p className="text-sm text-slate-600 font-medium">
                        拖拽 JSON 或 CSV 文件到此处
                      </p>
                      <p className="text-xs text-slate-400 mt-1">
                        或点击选择文件（.json / .csv）
                      </p>
                    </>
                  )}
                </div>

                {/* Text paste area */}
                <div className="relative">
                  <div className="flex items-center gap-2 mb-1.5">
                    <SvgIcon className="w-4 h-4 text-slate-400">{Icons.paste}</SvgIcon>
                    <span className="text-xs font-medium text-slate-500">或直接粘贴数据</span>
                  </div>
                  <textarea
                    value={importData}
                    onChange={(e) => {
                      setImportData(e.target.value);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                      setImportFileName("");
                      const parsed = tryParsePreview(e.target.value);
                      setImportPreview(parsed);
                    }}
                    placeholder={`粘贴 JSON 或 CSV 格式的评论数据...\n\nJSON 示例：\n[{"id":"1","rating":5,"content":"Great!","author":"User","date":"2024-01-01"}]\n\nCSV 示例：\nid,rating,content,author,date\n1,5,Great!,User,2024-01-01`}
                    rows={8}
                    disabled={isAnalyzing}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono
                      focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                      transition-all duration-200 placeholder:text-slate-400 resize-y
                      disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>

                {/* Preview */}
                {importPreview && importPreview.count > 0 && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 animate-fade-in">
                    <div className="flex items-center gap-2 mb-2">
                      <SvgIcon className="w-4 h-4 text-emerald-600">{Icons.check}</SvgIcon>
                      <span className="text-sm font-medium text-emerald-700">
                        已识别 {importPreview.count} 条评论
                      </span>
                    </div>
                    <pre className="text-xs text-slate-600 bg-white/60 rounded-lg p-3 max-h-40 overflow-auto font-mono whitespace-pre-wrap break-all">
                      {importPreview.preview}
                    </pre>
                  </div>
                )}
                {importPreview && importPreview.count === 0 && importData.trim() && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 animate-fade-in">
                    <div className="flex items-center gap-2">
                      <SvgIcon className="w-4 h-4 text-amber-600">{Icons.alert}</SvgIcon>
                      <span className="text-sm text-amber-700">
                        无法识别数据格式，请检查是否为有效的 JSON 或 CSV
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Goal (import mode too) ── */}
            {dataSource === "import" && (
              <div>
                <label htmlFor="goal-import" className="block text-sm font-medium text-slate-700 mb-1.5">
                  分析目标
                  <span className="text-slate-400 font-normal ml-1">（可选）</span>
                </label>
                <input
                  id="goal-import"
                  type="text"
                  value={analysisGoal}
                  onChange={(e) => setAnalysisGoal(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && canSubmit) handleAnalyze();
                  }}
                  placeholder="例如：用户反馈分析、功能建议提取、Bug 报告汇总"
                  disabled={isAnalyzing}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm
                    focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                    transition-all duration-200 placeholder:text-slate-400
                    disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>
            )}

            {/* Submit button */}
            <button
              onClick={isAnalyzing && isHoverCancel ? handleCancel : handleAnalyze}
              disabled={!canSubmit && !isAnalyzing}
              onMouseEnter={() => setIsHoverCancel(true)}
              onMouseLeave={() => setIsHoverCancel(false)}
              className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-violet-600 text-white
                font-semibold rounded-xl text-sm
                hover:from-blue-700 hover:to-violet-700 hover:shadow-lg hover:shadow-blue-200/40
                active:scale-[0.99] transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none disabled:active:scale-100
                flex items-center justify-center gap-2"
            >
              {isAnalyzing ? (
                isHoverCancel ? (
                  <>
                    <SvgIcon className="w-5 h-5">{Icons.close}</SvgIcon>
                    取消分析
                  </>
                ) : (
                  <>
                    <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    分析中，请耐心等待...
                  </>
                )
              ) : (
                <>
                  <SvgIcon className="w-5 h-5">{Icons.cog}</SvgIcon>
                  开始分析
                </>
              )}
            </button>
          </div>
        </section>

        {/* ── Error ── */}
        {error && !isAnalyzing && (
          <div className="mb-6 sm:mb-8">
            <ErrorAlert
              message={error}
              onDismiss={() => setError(null)}
              onRetry={handleAnalyze}
            />
          </div>
        )}

        {/* ── Loading / Live Progress ── */}
        {isAnalyzing && (
          <section className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 p-6 sm:p-8 mb-6 sm:mb-8" role="status" aria-live="polite" aria-label="分析加载中">
            {streamingStages ? (
              /* ── Live stage progress ── */
              <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] xl:grid-cols-[300px_1fr] gap-6 sm:gap-8">
                <aside aria-label="实时工作流进度">
                  <WorkflowProgress stages={streamingStages} />
                </aside>
                <main className="flex items-center justify-center min-h-[200px]">
                  <div className="flex flex-col items-center gap-4 animate-fade-in">
                    <div className="relative">
                      <div className="w-16 h-16 rounded-full border-[3px] border-slate-100" />
                      <div className="absolute inset-0 w-16 h-16 rounded-full border-[3px] border-transparent border-t-blue-500 border-r-blue-400 animate-spin" />
                      <div className="absolute inset-2 w-12 h-12 rounded-full border-[3px] border-transparent border-b-purple-400 border-l-purple-300 animate-spin-slow" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <SvgIcon className="w-5 h-5 text-blue-500 animate-pulse-soft">
                          {Icons.sparkles}
                        </SvgIcon>
                      </div>
                    </div>
                    <p className="text-sm text-slate-500">
                      {(() => {
                        const currentStage = Object.entries(stageStates).find(
                          ([, s]) => s === "running",
                        );
                        return currentStage
                          ? STAGE_LABELS[currentStage[0]] ?? "处理中..."
                          : "正在初始化...";
                      })()}
                    </p>
                  </div>
                </main>
              </div>
            ) : (
              /* ── Initial loading (before any SSE event) ── */
              <LoadingState message="正在连接分析服务..." />
            )}
          </section>
        )}

        {/* ── Results ── */}
        {!isAnalyzing && hasResults && (
          <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] xl:grid-cols-[300px_1fr] gap-6 sm:gap-8">
            <aside className="order-2 lg:order-1" aria-label="工作流进度面板">
              <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 p-5 sm:p-6 lg:sticky lg:top-8 animate-slide-up">
                <WorkflowProgress stages={response.stages} />

                {response.artifacts && (
                  <div className="mt-6 pt-5 border-t border-slate-100">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                      数据概览
                    </h4>
                    <div className="grid grid-cols-2 gap-2">
                      <StatItem label="原始评论" value={response.artifacts.reviews_count} color="text-blue-600" />
                      <StatItem label="清洗后" value={response.artifacts.cleaned_count} color="text-teal-600" />
                      <StatItem label="已分类" value={response.artifacts.classified_count} color="text-violet-600" />
                      <StatItem label="发现" value={response.artifacts.findings_count} color="text-amber-600" />
                      <StatItem label="需求" value={response.artifacts.requirements_count} color="text-rose-600" />
                      <StatItem label="测试用例" value={response.artifacts.test_cases_count} color="text-emerald-600" />
                    </div>
                    {response.duration_ms != null && (
                      <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-400">
                        <div className="w-1 h-1 rounded-full bg-slate-300" />
                        总耗时：{formatDuration(response.duration_ms)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </aside>

            <main id="main-content" className="order-1 lg:order-2 min-w-0" aria-label="分析结果">
              <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 p-4 sm:p-6 animate-fade-in">
                {hasArtifacts ? (
                  <ArtifactTabs artifacts={artifacts} />
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                    <SvgIcon className="w-12 h-12 mb-3 opacity-40">{Icons.document}</SvgIcon>
                    <p className="text-sm">暂无数据</p>
                  </div>
                )}
              </div>
            </main>
          </div>
        )}

        {/* ── Initial empty ── */}
        {!isAnalyzing && !hasResults && (
          <section className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 p-6 sm:p-8">
            <h2 className="text-lg sm:text-xl font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <SvgIcon className="w-5 h-5 text-violet-600">{Icons.chart}</SvgIcon>
              分析结果
            </h2>
            <EmptyState />
          </section>
        )}
      </div>
    </div>
  );
}
