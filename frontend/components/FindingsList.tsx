"use client";

import { useState } from "react";
import type { Finding, FindingSeverity, EvidenceSufficiency } from "@/types";

// ═══════════════════════════════════════════
// Severity Config
// ═══════════════════════════════════════════

const SEVERITY_CONFIG: Record<FindingSeverity, { style: string; label: string; dot: string }> = {
  critical: { style: "bg-red-50 text-red-700 border-red-200", label: "严重", dot: "bg-red-500" },
  high:     { style: "bg-orange-50 text-orange-700 border-orange-200", label: "高", dot: "bg-orange-500" },
  medium:   { style: "bg-amber-50 text-amber-700 border-amber-200", label: "中", dot: "bg-amber-500" },
  low:      { style: "bg-blue-50 text-blue-700 border-blue-200", label: "低", dot: "bg-blue-500" },
};

const EVIDENCE_LABELS: Record<EvidenceSufficiency, string> = {
  sufficient: "证据充分",
  limited: "证据有限",
  insufficient: "证据不足",
};

const EVIDENCE_COLORS: Record<EvidenceSufficiency, string> = {
  sufficient: "text-emerald-600 bg-emerald-50",
  limited: "text-amber-600 bg-amber-50",
  insufficient: "text-red-600 bg-red-50",
};

// ═══════════════════════════════════════════
// Confidence Bar
// ═══════════════════════════════════════════

function ConfidenceBar({ confidence }: { confidence: number }) {
  const percentage = Math.round(confidence * 100);
  let color = "bg-emerald-500";
  if (percentage < 50) color = "bg-red-500";
  else if (percentage < 75) color = "bg-amber-500";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-[11px] font-medium text-slate-500 w-9 text-right tabular-nums">
        {percentage}%
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════
// FindingCard
// ═══════════════════════════════════════════

function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const sev = SEVERITY_CONFIG[finding.severity] ?? SEVERITY_CONFIG.medium;
  const evColor = EVIDENCE_COLORS[finding.evidence_sufficiency] ?? "text-slate-600 bg-slate-50";

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${sev.style}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${sev.dot}`} />
                {sev.label}
              </span>
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                {finding.category}
              </span>
            </div>
            <h4 className="mt-2 text-sm font-semibold text-slate-800 leading-snug">
              {finding.title}
            </h4>
          </div>

          <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
            <span className="text-[11px] font-medium text-slate-500">
              {finding.support_count} 条支持
            </span>
            <span className={`rounded-md px-2 py-0.5 text-[10px] font-medium ${evColor}`}>
              {EVIDENCE_LABELS[finding.evidence_sufficiency]}
            </span>
          </div>
        </div>

        {/* Description */}
        <p className="mt-2.5 text-sm leading-relaxed text-slate-600">
          {finding.description}
        </p>

        {/* Confidence bar */}
        <div className="mt-3">
          <ConfidenceBar confidence={finding.confidence} />
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors group"
        >
          <svg
            className={`h-3.5 w-3.5 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          {expanded ? "收起详情" : "展开详情"}
        </button>
      </div>

      {/* Expanded details */}
      <div
        className={`border-t border-slate-100 bg-slate-50/80 overflow-hidden transition-all duration-300 ${
          expanded ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-4 py-3 space-y-3.5">
          {/* Supporting evidence */}
          {finding.supporting_excerpts.length > 0 && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-1 h-3 rounded-full bg-emerald-400" />
                支持证据
              </h5>
              <ul className="space-y-1.5">
                {finding.supporting_excerpts.map((excerpt, i) => (
                  <li key={i} className="text-xs text-slate-600 pl-3 border-l-2 border-emerald-200 italic">
                    &ldquo;{excerpt}&rdquo;
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conflicting evidence */}
          {finding.conflicting_evidence && finding.conflicting_evidence.length > 0 && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-1 h-3 rounded-full bg-orange-400" />
                冲突证据
              </h5>
              <ul className="space-y-1.5">
                {finding.conflicting_evidence.map((evidence, i) => (
                  <li key={i} className="text-xs text-orange-600 pl-3 border-l-2 border-orange-200">
                    {evidence}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Assumptions */}
          {finding.assumptions && finding.assumptions.length > 0 && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <span className="w-1 h-3 rounded-full bg-blue-400" />
                假设
              </h5>
              <ul className="space-y-1">
                {finding.assumptions.map((assumption, i) => (
                  <li key={i} className="text-xs text-slate-500 flex items-start gap-1.5">
                    <span className="mt-0.5 text-blue-400">●</span>
                    {assumption}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Uncertainty notes */}
          {finding.uncertainty_notes && (
            <div>
              <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <span className="w-1 h-3 rounded-full bg-slate-400" />
                不确定性说明
              </h5>
              <p className="text-xs text-slate-500 italic bg-white rounded-lg p-2 border border-slate-100">
                {finding.uncertainty_notes}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════
// FindingsList
// ═══════════════════════════════════════════

interface FindingsListProps {
  findings: Finding[];
}

export default function FindingsList({ findings }: FindingsListProps) {
  if (!findings || findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <span className="text-4xl mb-3">🔍</span>
        <p className="text-sm font-medium">暂无发现数据</p>
        <p className="text-xs mt-1 text-slate-300">分析洞察结果将在此显示</p>
      </div>
    );
  }

  const severityOrder: FindingSeverity[] = ["critical", "high", "medium", "low"];
  const sorted = [...findings].sort(
    (a, b) => severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity)
  );

  return (
    <div className="space-y-3 animate-fade-in">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-800">分析发现</h3>
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
          {findings.length} 项
        </span>
      </div>

      <div className="max-h-[600px] space-y-3 overflow-y-auto pr-1">
        {sorted.map((finding, i) => (
          <FindingCard key={finding.finding_id} finding={finding} index={i} />
        ))}
      </div>
    </div>
  );
}