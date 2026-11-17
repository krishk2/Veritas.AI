"use client";

import React, { useState } from "react";
import { ExternalLink, CheckCircle2, AlertTriangle, HelpCircle } from "lucide-react";

export interface SourceCitationItem {
  citation_id: number;
  title: string;
  url: string;
  domain: string;
  favicon_url: string;
  credibility_status: "Trusted" | "Questionable" | "Neutral" | string;
  credibility_score: number;
  snippet?: string | null;
}

interface SourcesCarouselProps {
  sources: SourceCitationItem[];
  highlightedCitationId?: number | null;
  onCitationClick?: (citationId: number) => void;
}

export const SourcesCarousel: React.FC<SourcesCarouselProps> = ({
  sources,
  highlightedCitationId,
  onCitationClick,
}) => {
  const [selectedSnippet, setSelectedSnippet] = useState<SourceCitationItem | null>(null);

  if (!sources || sources.length === 0) {
    return null;
  }

  const getStatusBadge = (status: string, score: number) => {
    switch (status.toLowerCase()) {
      case "trusted":
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Accredited ({Math.round(score * 100)}%)
          </span>
        );
      case "questionable":
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full">
            <AlertTriangle className="w-3 h-3" />
            Unverified ({Math.round(score * 100)}%)
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-slate-400 bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full">
            <HelpCircle className="w-3 h-3" />
            Neutral
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs uppercase tracking-wider font-semibold text-slate-400">
          Corroborating Sources ({sources.length})
        </h4>
        <span className="text-[11px] text-slate-500">Perplexity-style attribution</span>
      </div>

      {/* Horizontal Scroll Carousel */}
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
        {sources.map((src) => {
          const isHighlighted = highlightedCitationId === src.citation_id;

          return (
            <div
              key={src.citation_id}
              id={`source-card-${src.citation_id}`}
              onClick={() => {
                setSelectedSnippet(src);
                onCitationClick?.(src.citation_id);
              }}
              className={`flex-shrink-0 w-64 p-3.5 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col justify-between gap-3 ${
                isHighlighted
                  ? "bg-cyan-500/15 border-cyan-400 shadow-lg shadow-cyan-500/10 scale-[1.02]"
                  : "bg-[#0D1527] border-white/10 hover:border-white/20 hover:bg-[#131E35]"
              }`}
            >
              {/* Header with Favicon & Citation Badge */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 overflow-hidden">
                  <img
                    src={src.favicon_url}
                    alt={src.domain}
                    className="w-4 h-4 rounded-sm flex-shrink-0"
                    onError={(e) => {
                      // Fallback if favicon fails
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />
                  <span className="text-xs font-semibold text-white truncate max-w-[140px]">
                    {src.domain}
                  </span>
                </div>

                <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 text-cyan-400 font-mono text-[10px] flex items-center justify-center font-bold">
                  {src.citation_id}
                </span>
              </div>

              {/* Title & Snippet preview */}
              <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                {src.title || src.snippet || "Corroborated news report and context."}
              </p>

              {/* Credibility Status & Link */}
              <div className="flex items-center justify-between pt-1 border-t border-white/5">
                {getStatusBadge(src.credibility_status, src.credibility_score)}
                {src.url && (
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-slate-400 hover:text-cyan-400 transition-colors p-1"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Snippet Preview Drawer / Modal */}
      {selectedSnippet && (
        <div className="p-4 rounded-xl bg-[#090F1E] border border-cyan-500/20 text-xs text-slate-300 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-cyan-400">
              Citation [{selectedSnippet.citation_id}]: {selectedSnippet.domain}
            </span>
            <button
              onClick={() => setSelectedSnippet(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          <p className="italic leading-relaxed text-slate-300">
            "{selectedSnippet.snippet || "Full document text analyzed by evidence agent."}"
          </p>
        </div>
      )}
    </div>
  );
};
