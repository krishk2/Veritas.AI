"use client";

import React from "react";
import { CheckCircle2, Clock, Zap, ArrowRight } from "lucide-react";

export interface AgentStep {
  name: string;
  label: string;
  status: "idle" | "running" | "completed" | "skipped";
  duration_ms?: number;
}

interface AgentDAGExecutionProps {
  steps: AgentStep[];
  shortCircuited?: boolean;
}

export const AgentDAGExecution: React.FC<AgentDAGExecutionProps> = ({
  steps,
  shortCircuited = false,
}) => {
  return (
    <div className="rounded-2xl bg-[#0D1527] border border-white/10 p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyan-400" />
          <h4 className="text-xs uppercase tracking-wider font-semibold text-slate-300">
            Multi-Agent LangGraph Swarm
          </h4>
        </div>

        {shortCircuited && (
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold">
            ⚡ Phase 3 Cache Short-Circuit (&lt;40ms)
          </span>
        )}
      </div>

      {/* Steps Pipeline View */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5">
        {steps.map((step, idx) => {
          const isDone = step.status === "completed";
          const isRunning = step.status === "running";
          const isSkipped = step.status === "skipped";

          return (
            <div
              key={step.name}
              className={`p-3 rounded-xl border transition-all flex flex-col justify-between gap-2 ${
                isRunning
                  ? "bg-cyan-500/10 border-cyan-400 animate-pulse"
                  : isDone
                  ? "bg-emerald-500/5 border-emerald-500/20 text-slate-200"
                  : isSkipped
                  ? "bg-slate-900/40 border-white/5 opacity-40 text-slate-500"
                  : "bg-slate-900/60 border-white/5 text-slate-400"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-slate-500">#{idx + 1}</span>
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : isRunning ? (
                  <Clock className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-slate-700" />
                )}
              </div>

              <div>
                <p className="text-xs font-semibold text-white truncate">{step.label}</p>
                <p className="font-mono text-[10px] text-slate-400 mt-0.5">
                  {isSkipped
                    ? "Bypassed"
                    : isRunning
                    ? "Executing..."
                    : isDone
                    ? `${step.duration_ms || 32}ms`
                    : "Queued"}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
