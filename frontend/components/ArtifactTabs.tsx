"use client";

import { useState } from "react";
import type { Artifacts, ClassificationResult } from "@/types";

import ReviewList from "./ReviewList";
import FindingsList from "./FindingsList";
import PRDView from "./PRDView";
import TestCasesList from "./TestCasesList";

// ═══════════════════════════════════════════
// Tab Config
// ═══════════════════════════════════════════

const TABS = [
  { key: "raw_reviews", label: "原始评论", icon: "📝" },
  { key: "cleaned_data", label: "清洗数据", icon: "🧹" },
  { key: "classification", label: "评论分类", icon: "🏷️" },
  { key: "findings", label: "分析发现", icon: "🔍" },
  { key: "prd", label: "PRD", icon: "📋" },
  { key: "test_cases", label: "测试用例", icon: "🧪" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

// ═══════════════════════════════════════════
// Classification View
// ═══════════════════════════════════════════

const SENTIMENT_CONFIG: Record<string, { emoji: string; color: string; label: string }> = {
  positive: { emoji: "😊", color: "bg-emerald-100 text-emerald-700 border-emerald-200", label: "正面" },
  negative: { emoji: "😞", color: "bg-red-100 text-red-700 border-red-200", label: "负面" },
  neutral:  { emoji: "😐", color: "bg-slate-100 text-slate-600 border-slate-200", label: "中性" },
  mixed:    { emoji: "🤔", color: "bg-amber-100 text-amber-700 border-amber-200", label: "混合" },
};

function ClassificationView({ classifications }: { classifications: ClassificationResult[] }) {
  if (!classifications || classifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <span className="text-4xl mb-3">🏷️</span>
        <p className="text-sm font-medium">暂无分类数据</p>
        <p className="text-xs mt-1 text-slate-300">评论分类结果将在此显示</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-800">评论分类</h3>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
          {classifications.length} 条
        </span>
      </div>

      <div className="max-h-[600px] space-y-2 overflow-y-auto pr-1">
        {classifications.map((cls) => {
          const cfg = SENTIMENT_CONFIG[cls.sentiment] ?? SENTIMENT_CONFIG.neutral;
          return (
            <div
              key={cls.review_id}
              className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all duration-200"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] font-mono text-slate-400">{cls.review_id}</span>
                <span className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${cfg.color}`}>
                  {cfg.emoji} {cfg.label}
                </span>
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                  {cls.primary_category}
                </span>
                <span className="text-[11px] text-slate-400 ml-auto">
                  {Math.round(cls.confidence * 100)}% 置信
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">{cls.summary}</p>
              {cls.key_quote && (
                <p className="mt-1.5 text-xs italic text-slate-400 border-l-2 border-slate-200 pl-2.5">
                  &ldquo;{cls.key_quote}&rdquo;
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════
// ArtifactTabs Component
// ═══════════════════════════════════════════

interface ArtifactTabsProps {
  artifacts: Artifacts;
}

function getTabCount(artifacts: Artifacts, tab: TabKey): number {
  switch (tab) {
    case "raw_reviews":       return artifacts.raw_reviews?.length ?? 0;
    case "cleaned_data":      return artifacts.cleaned_data?.length ?? 0;
    case "classification":    return artifacts.classification_results?.length ?? 0;
    case "findings":          return artifacts.findings?.length ?? 0;
    case "prd":               return artifacts.prd_draft ? 1 : 0;
    case "test_cases":        return artifacts.test_case_drafts?.length ?? 0;
  }
}

export default function ArtifactTabs({ artifacts }: ArtifactTabsProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("raw_reviews");

  const renderTabContent = () => {
    const content = (() => {
      switch (activeTab) {
        case "raw_reviews":
          return <ReviewList reviews={artifacts.raw_reviews ?? []} />;
        case "cleaned_data":
          return <ReviewList reviews={artifacts.cleaned_data ?? []} />;
        case "classification":
          return <ClassificationView classifications={artifacts.classification_results ?? []} />;
        case "findings":
          return <FindingsList findings={artifacts.findings ?? []} reviews={artifacts.cleaned_data ?? artifacts.raw_reviews ?? []} />;
        case "prd":
          if (!artifacts.prd_draft) {
            return (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                <span className="text-4xl mb-3">📋</span>
                <p className="text-sm font-medium">暂无 PRD 数据</p>
                <p className="text-xs mt-1 text-slate-300">PRD 文档生成后将在此显示</p>
              </div>
            );
          }
          return <PRDView prd={artifacts.prd_draft} />;
        case "test_cases":
          return <TestCasesList testCases={artifacts.test_case_drafts ?? []} />;
        default:
          return null;
      }
    })();

    return <div className="animate-fade-in" key={activeTab}>{content}</div>;
  };

  return (
    <div className="w-full">
      {/* Tab bar */}
      <div className="flex border-b border-slate-200 overflow-x-auto -mx-1 px-1 scrollbar-none gap-0.5">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          const count = getTabCount(artifacts, tab.key);
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 whitespace-nowrap px-3.5 py-2.5 text-sm font-medium transition-all duration-200 border-b-2 -mb-px rounded-t-lg ${
                isActive
                  ? "border-blue-500 text-blue-600 bg-blue-50/50"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <span className="text-base">{tab.icon}</span>
              {tab.label}
              {count > 0 && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                  isActive ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-500"
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="mt-5">{renderTabContent()}</div>
    </div>
  );
}