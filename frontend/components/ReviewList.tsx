"use client";

import { useState, useEffect } from "react";
import type { Review } from "@/types";

// ═══════════════════════════════════════════
// Star Rating
// ═══════════════════════════════════════════

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5" aria-label={`评分 ${rating} / 5`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <svg
          key={star}
          className={`h-3.5 w-3.5 transition-colors ${
            star <= rating ? "text-amber-400" : "text-slate-200"
          }`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════
// Rating Badge
// ═══════════════════════════════════════════

function RatingBadge({ rating }: { rating: number }) {
  const colors: Record<number, string> = {
    1: "bg-red-100 text-red-700",
    2: "bg-orange-100 text-orange-700",
    3: "bg-amber-100 text-amber-700",
    4: "bg-blue-100 text-blue-700",
    5: "bg-emerald-100 text-emerald-700",
  };
  return (
    <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${colors[rating] ?? "bg-slate-100 text-slate-600"}`}>
      {rating}/5
    </span>
  );
}

// ═══════════════════════════════════════════
// Date Formatter
// ═══════════════════════════════════════════

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

// ═══════════════════════════════════════════
// ReviewList Component
// ═══════════════════════════════════════════

interface ReviewListProps {
  reviews: Review[];
  highlightedReviewId?: string | null;
}

export default function ReviewList({ reviews, highlightedReviewId }: ReviewListProps) {
  const [filterRating, setFilterRating] = useState<number | null>(null);

  if (!reviews || reviews.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <span className="text-4xl mb-3">📝</span>
        <p className="text-sm font-medium">暂无评论数据</p>
        <p className="text-xs mt-1 text-slate-300">评论采集后将在此显示</p>
      </div>
    );
  }

  const filtered = filterRating
    ? reviews.filter((r) => r.rating === filterRating)
    : reviews;

  // Auto-scroll to highlighted review
  useEffect(() => {
    if (highlightedReviewId) {
      setTimeout(() => {
        document.getElementById(`review-${highlightedReviewId}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 150);
    }
  }, [highlightedReviewId]);

  const ratingCounts = [5, 4, 3, 2, 1].map((r) => ({
    rating: r,
    count: reviews.filter((rev) => rev.rating === r).length,
  }));

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-800">评论列表</h3>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
            {reviews.length} 条
          </span>
          {filterRating && (
            <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              筛选: {filterRating} 星
              <button
                onClick={() => setFilterRating(null)}
                className="ml-1 text-blue-400 hover:text-blue-600"
              >
                ×
              </button>
            </span>
          )}
        </div>

        {/* Rating filter pills */}
        <div className="flex items-center gap-1 flex-wrap">
          {ratingCounts.map(({ rating, count }) => (
            <button
              key={rating}
              onClick={() => setFilterRating(filterRating === rating ? null : rating)}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-all duration-200 ${
                filterRating === rating
                  ? "bg-blue-100 text-blue-700 ring-1 ring-blue-300"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {"★".repeat(rating)}
              <span className="opacity-60">{count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Review cards */}
      <div className="max-h-[600px] space-y-2.5 overflow-y-auto pr-1">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-400">
            没有匹配的评论
          </div>
        ) : (
          filtered.map((review, i) => (
            <div
              key={review.id}
              id={`review-${review.id}`}
              className={`rounded-xl border bg-white p-4 shadow-sm hover:shadow-md transition-all duration-500 ${
                highlightedReviewId === review.id
                  ? "border-blue-400 ring-2 ring-blue-200 bg-blue-50/30 scale-[1.02]"
                  : "border-slate-200 hover:border-slate-300"
              }`}
              style={{ animationDelay: `${i * 30}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <RatingBadge rating={review.rating} />
                    <StarRating rating={review.rating} />
                  </div>
                  <span className="text-sm font-medium text-slate-700">
                    {review.author}
                  </span>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <span className="text-[11px] text-slate-400">{formatDate(review.date)}</span>
                  {review.version && (
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500 font-mono">
                      v{review.version}
                    </span>
                  )}
                </div>
              </div>

              {review.title && (
                <h4 className="mt-2.5 text-sm font-semibold text-slate-800 leading-snug">
                  {review.title}
                </h4>
              )}

              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                {review.content}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}