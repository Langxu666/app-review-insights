"use client";

import { useState } from "react";
import type { TestCase } from "@/types";

// ═══════════════════════════════════════════
// TestCaseCard
// ═══════════════════════════════════════════

function TestCaseCard({ testCase, index }: { testCase: TestCase; index: number }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start justify-between gap-3 p-4 text-left hover:bg-slate-50/50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 w-6 h-6 rounded-lg bg-slate-100 text-[10px] font-bold text-slate-500 flex items-center justify-center">
            {index + 1}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-slate-400">{testCase.id}</span>
              <h4 className="text-sm font-semibold text-slate-800 truncate">{testCase.title}</h4>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {testCase.related_requirement && (
            <span className="rounded-lg bg-blue-50 border border-blue-100 px-2 py-0.5 text-[11px] font-medium text-blue-700">
              {testCase.related_requirement}
            </span>
          )}
          <svg
            className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Body */}
      <div
        className={`overflow-hidden transition-all duration-300 ${
          expanded ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-4 pb-4 space-y-3">
          {/* Preconditions */}
          {testCase.preconditions.length > 0 && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-1 h-3 rounded-full bg-amber-400" />
                前置条件
              </h5>
              <ul className="space-y-1 bg-amber-50/50 rounded-lg p-2.5 border border-amber-100">
                {testCase.preconditions.map((precondition, i) => (
                  <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-400" />
                    {precondition}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Steps */}
          <div>
            <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <span className="w-1 h-3 rounded-full bg-blue-400" />
              测试步骤
            </h5>
            <ol className="space-y-2">
              {testCase.steps.map((step, i) => (
                <li key={i} className="flex items-start gap-3 text-sm">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-50 border border-blue-100 text-[11px] font-semibold text-blue-600 flex items-center justify-center">
                    {i + 1}
                  </span>
                  <span className="text-slate-700 pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Expected Result */}
          <div>
            <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <span className="w-1 h-3 rounded-full bg-emerald-400" />
              预期结果
            </h5>
            <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-3 flex items-start gap-2">
              <svg className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-emerald-800">{testCase.expected_result}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════
// TestCasesList
// ═══════════════════════════════════════════

interface TestCasesListProps {
  testCases: TestCase[];
}

export default function TestCasesList({ testCases }: TestCasesListProps) {
  const [expandAll, setExpandAll] = useState(true);

  if (!testCases || testCases.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <span className="text-4xl mb-3">🧪</span>
        <p className="text-sm font-medium">暂无测试用例</p>
        <p className="text-xs mt-1 text-slate-300">测试用例生成后将在此显示</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800">测试用例</h3>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            {testCases.length} 条
          </span>
        </div>
        <button
          onClick={() => setExpandAll(!expandAll)}
          className="text-xs text-slate-500 hover:text-slate-700 transition-colors flex items-center gap-1"
        >
          {expandAll ? "全部收起" : "全部展开"}
          <svg
            className={`h-3 w-3 transition-transform ${expandAll ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      <div className="max-h-[600px] space-y-2.5 overflow-y-auto pr-1">
        {testCases.map((tc, i) => (
          <TestCaseCard key={tc.id} testCase={tc} index={i} />
        ))}
      </div>
    </div>
  );
}