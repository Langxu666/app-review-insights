"use client";

import type { PRDDraft, Requirement, VersionPlan, UserStory, Priority } from "@/types";

// ═══════════════════════════════════════════
// Priority Config
// ═══════════════════════════════════════════

const PRIORITY_CONFIG: Record<Priority, { style: string; label: string }> = {
  P0: { style: "bg-red-50 text-red-700 border-red-200", label: "P0 紧急" },
  P1: { style: "bg-orange-50 text-orange-700 border-orange-200", label: "P1 高优" },
  P2: { style: "bg-blue-50 text-blue-700 border-blue-200", label: "P2 中优" },
  P3: { style: "bg-slate-50 text-slate-600 border-slate-200", label: "P3 低优" },
};

// ═══════════════════════════════════════════
// Section Header
// ═══════════════════════════════════════════

function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">{title}</h4>
      {count !== undefined && (
        <span className="text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full font-medium">
          {count}
        </span>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════
// User Story Card
// ═══════════════════════════════════════════

function UserStoryCard({ story }: { story: UserStory }) {
  return (
    <div className="rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50/60 to-white p-3.5">
      <p className="text-sm text-slate-700 leading-relaxed">
        <span className="font-semibold text-indigo-600">作为</span>{" "}
        <span className="text-indigo-600 font-medium">{story.role}</span>
        <span className="text-indigo-400">，</span>
        <span className="font-semibold text-indigo-600"> 我想要</span>{" "}
        <span className="text-indigo-600 font-medium">{story.goal}</span>
        <span className="text-indigo-400">，</span>
        <span className="font-semibold text-indigo-600"> 以便</span>{" "}
        <span className="text-indigo-600 font-medium">{story.benefit}</span>
      </p>
    </div>
  );
}

// ═══════════════════════════════════════════
// Requirement Card
// ═══════════════════════════════════════════

function RequirementCard({ requirement }: { requirement: Requirement }) {
  const prio = PRIORITY_CONFIG[requirement.priority] ?? PRIORITY_CONFIG.P3;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-mono text-slate-400">{requirement.req_id}</span>
          <span className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${prio.style}`}>
            {prio.label}
          </span>
          {requirement.target_version && (
            <span className="rounded-md bg-purple-50 border border-purple-200 px-2 py-0.5 text-[11px] font-medium text-purple-700">
              v{requirement.target_version}
            </span>
          )}
          {requirement.is_assumption && (
            <span className="rounded-md bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-medium text-amber-700">
              ⚠ 假设
            </span>
          )}
        </div>
        {requirement.effort_estimate && (
          <span className="text-[11px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md">
            {requirement.effort_estimate}
          </span>
        )}
      </div>

      <h4 className="mt-2.5 text-sm font-semibold text-slate-800">{requirement.title}</h4>
      <p className="mt-1 text-sm text-slate-600 leading-relaxed">{requirement.description}</p>

      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        <div className="bg-slate-50 rounded-lg p-2.5">
          <span className="font-medium text-slate-500">用户问题</span>
          <p className="mt-0.5 text-slate-600">{requirement.user_problem}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-2.5">
          <span className="font-medium text-slate-500">商业价值</span>
          <p className="mt-0.5 text-slate-600">{requirement.business_value}</p>
        </div>
      </div>

      {requirement.acceptance_criteria.length > 0 && (
        <div className="mt-3">
          <h5 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
            验收标准
          </h5>
          <ul className="space-y-1">
            {requirement.acceptance_criteria.map((criterion, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                <svg className="mt-0.5 h-3 w-3 flex-shrink-0 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                {criterion}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════
// Version Plan Card
// ═══════════════════════════════════════════

function VersionPlanCard({ plan }: { plan: VersionPlan }) {
  return (
    <div className="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50/60 to-white p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-lg bg-purple-600 px-2.5 py-1 text-xs font-semibold text-white shadow-sm shadow-purple-200">
          v{plan.version}
        </span>
        <span className="text-sm font-semibold text-purple-800">{plan.theme}</span>
      </div>
      <p className="mt-2 text-sm text-purple-700/80">{plan.release_goal}</p>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {plan.requirement_ids.map((reqId) => (
          <span
            key={reqId}
            className="rounded-md bg-white border border-purple-200 px-2 py-0.5 text-[11px] font-mono text-purple-600 shadow-sm"
          >
            {reqId}
          </span>
        ))}
      </div>
      <p className="mt-2.5 text-xs text-slate-500 leading-relaxed">{plan.rationale}</p>
    </div>
  );
}

// ═══════════════════════════════════════════
// PRDView
// ═══════════════════════════════════════════

interface PRDViewProps {
  prd: PRDDraft;
}

export default function PRDView({ prd }: PRDViewProps) {
  if (!prd) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <span className="text-4xl mb-3">📋</span>
        <p className="text-sm font-medium">暂无 PRD 数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h3 className="text-lg font-bold text-slate-900">产品需求文档 (PRD)</h3>
        <div className="mt-2 flex items-center gap-3 flex-wrap text-sm">
          <span className="rounded-lg bg-blue-50 border border-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700">
            {prd.app_name}
          </span>
          <span className="text-xs text-slate-500">
            分析目标：{prd.analysis_goal}
          </span>
          {prd.generated_at && (
            <span className="text-xs text-slate-400">
              {new Date(prd.generated_at).toLocaleString("zh-CN")}
            </span>
          )}
        </div>
      </div>

      {/* Title */}
      {prd.title && (
        <h2 className="text-xl font-bold text-slate-900 pb-4 border-b border-slate-100">
          {prd.title}
        </h2>
      )}

      {/* Background */}
      {prd.background && (
        <section>
          <SectionHeader title="背景" />
          <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">
            <p className="text-sm leading-relaxed text-slate-600">{prd.background}</p>
          </div>
        </section>
      )}

      {/* Problem Statement */}
      {prd.problem_statement && (
        <section>
          <SectionHeader title="问题陈述" />
          <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">
            <p className="text-sm leading-relaxed text-slate-600">{prd.problem_statement}</p>
          </div>
        </section>
      )}

      {/* User Stories */}
      {prd.user_stories && prd.user_stories.length > 0 && (
        <section>
          <SectionHeader title="用户故事" count={prd.user_stories.length} />
          <div className="space-y-2">
            {prd.user_stories.map((story) => (
              <UserStoryCard key={story.id} story={story} />
            ))}
          </div>
        </section>
      )}

      {/* Requirements */}
      {prd.requirements && prd.requirements.length > 0 && (
        <section>
          <SectionHeader
            title="需求列表"
            count={prd.requirements.length}
          />
          <div className="max-h-[600px] space-y-3 overflow-y-auto pr-1">
            {prd.requirements.map((req) => (
              <RequirementCard key={req.req_id} requirement={req} />
            ))}
          </div>
        </section>
      )}

      {/* Version Plan */}
      {prd.version_plan && prd.version_plan.length > 0 && (
        <section>
          <SectionHeader title="版本计划" count={prd.version_plan.length} />
          <div className="space-y-3">
            {prd.version_plan.map((plan) => (
              <VersionPlanCard key={plan.version} plan={plan} />
            ))}
          </div>
        </section>
      )}

      {/* Empty content warning */}
      {(!prd.requirements || prd.requirements.length === 0) &&
        (!prd.user_stories || prd.user_stories.length === 0) && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
            <span className="text-3xl mb-2">📋</span>
            <p className="text-sm">PRD 内容为空</p>
            <p className="text-xs mt-1 text-slate-300">该 PRD 尚未包含需求或用户故事</p>
          </div>
        )}
    </div>
  );
}