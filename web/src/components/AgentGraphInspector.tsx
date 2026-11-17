"use client";

import React, { useState } from "react";
import {
  Zap,
  Activity,
  Layers,
  Search,
  Database,
  Cpu,
  ShieldCheck,
  FileText,
  Clock,
  CheckCircle2,
  ChevronRight,
  Code2,
  Terminal,
  Sparkles,
  ArrowRight,
  Info,
  Maximize2,
  X,
  Workflow
} from "lucide-react";

export interface AgentExecutionTraceItem {
  agent_id: string;
  agent_name: string;
  role: string;
  tools: string[];
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  duration_ms: number;
  status: "idle" | "running" | "completed" | "skipped";
}

interface AgentGraphInspectorProps {
  executionTrace?: AgentExecutionTraceItem[];
  isVerifying: boolean;
  shortCircuited?: boolean;
}

// Default graph topology definition with human-readable roles & tools
const GRAPH_NODES = [
  {
    id: "dedup_agent",
    name: "Semantic Dedup",
    phase: "1. Ingestion",
    role: "Checks Truth Ledger for semantically identical claims using vector similarity to eliminate redundant work.",
    tools: ["GoogleGenerativeAIEmbeddings(text-embedding-004)", "CosineSimilarityIndex", "SHA256 ContentHasher"],
    defaultInputs: { query: "Raw user input text & media hashes" },
    defaultOutputs: { canonical_claim: "Normalized claim", is_duplicate: false, similarity_score: 0.12 }
  },
  {
    id: "parallel_investigation_agent",
    name: "Parallel Fan-Out",
    phase: "2. Multimodal DAG",
    role: "Spawns 4 concurrent worker threads running Web Retrieval, Domain Trust, Image Forensics, and Video Deepfake Analysis simultaneously.",
    tools: ["DuckDuckGo Hybrid Search", "FAISS In-Memory Vector Store", "OpenCV ELA Analyzer", "Temporal Face Inconsistency Checker"],
    defaultInputs: { tracks: ["Track A: Web Retrieval", "Track B: Domain Trust", "Track C: Image Forensics", "Track D: Video Forensics"] },
    defaultOutputs: { status: "barrier_synchronized", elapsed_ms: 820 }
  },
  {
    id: "source_agent",
    name: "Web Intelligence",
    phase: "2. Retrieval",
    role: "Gathers authoritative public reporting, institutional statements, and live web sources.",
    tools: ["TavilySearchResults(max_results=5)", "Domain Filter Engine", "Query Reformulator"],
    defaultInputs: { query: "Normalized canonical claim" },
    defaultOutputs: { sources_found: 5, top_domains: ["espncricinfo.com", "reuters.com", "who.int"] }
  },
  {
    id: "image_agent",
    name: "Image Forensics",
    phase: "3. Forensics",
    role: "Performs Error Level Analysis (ELA) to detect JPEG resaving artifacts, clone-stamping, and generative AI traces.",
    tools: ["Error Level Analysis (ELA 95%)", "EXIF Camera Inspector", "Laplacian Edge Variance"],
    defaultInputs: { has_image: false, raw_bytes: "base64 payload" },
    defaultOutputs: { ela_score: 8.4, ai_detected: false, tampering_alerts: [] }
  },
  {
    id: "video_agent",
    name: "Video Deepfake",
    phase: "3. Forensics",
    role: "Analyzes video keyframes for temporal frame anomalies, unnatural facial blinking, and synthetic AI generation.",
    tools: ["OpenCV Temporal Differencing", "Deepfake Artifact Detector", "FFmpeg Frame Analyzer"],
    defaultInputs: { has_video: false },
    defaultOutputs: { deepfake_detected: false, confidence: 0.92 }
  },
  {
    id: "fetch_agent",
    name: "DOM Scraper",
    phase: "4. Extraction",
    role: "Crawls search candidate URLs, extracts body copy, strips advertising/nav scripts, and creates semantic text chunks.",
    tools: ["requests.Session(Chrome-UA)", "BeautifulSoup4 (DOM Stripper)", "RecursiveCharacterTextSplitter(chunk_size=1000)"],
    defaultInputs: { urls_to_scrape: 5 },
    defaultOutputs: { chunks_extracted: 18, avg_chunk_size: 1000 }
  },
  {
    id: "retriever_agent",
    name: "Vector Store",
    phase: "4. Extraction",
    role: "Embeds chunks into dense vector space and executes semantic nearest-neighbor retrieval for the top-k passages.",
    tools: ["GoogleGenerativeAIEmbeddings(text-embedding-004)", "FAISS Vector Index (faiss-cpu)", "Top-K Similarity Scorer"],
    defaultInputs: { chunks_indexed: 18, query: "Evaluated claim" },
    defaultOutputs: { top_passages_retrieved: 5, vector_dimensions: 768 }
  },
  {
    id: "evidence_agent",
    name: "NLI Inference",
    phase: "5. Reasoning",
    role: "Performs Natural Language Inference (NLI) to classify factual passages into SUPPORT or REFUTE with confidence scores.",
    tools: ["ChatGoogleGenerativeAI(gemini-flash-latest)", "Zero-Shot NLI Classification Chain", "Cross-Modal Evidence Fuser"],
    defaultInputs: { passages_to_analyze: 5, visual_evidence_count: 0 },
    defaultOutputs: { evidence_count: 4, support_count: 0, refute_count: 4 }
  },
  {
    id: "judge_agent",
    name: "Truth Judge",
    phase: "6. Decision",
    role: "Synthesizes multimodal evidence and issues an authoritative verdict with inline Perplexity-style citations [1, 2].",
    tools: ["ChatGoogleGenerativeAI(gemini-flash-latest)", "Perplexity Citation Formatter", "JsonOutputParser"],
    defaultInputs: { evidence_items: 4, sources_indexed: 5 },
    defaultOutputs: { verdict: "FALSE", confidence: 0.99, has_citations: true }
  },
  {
    id: "reputation_agent",
    name: "Source Auditor",
    phase: "7. Audit",
    role: "Evaluates domain trust rankings, historical journalistic credibility, and flags known satire/misinformation domains.",
    tools: ["Domain Trust Matrix", "WHOIS & TLD Authority Verifier", "Credibility Weighting Engine"],
    defaultInputs: { domains: 5 },
    defaultOutputs: { audited_domains: 5, average_trust_score: 0.88 }
  },
  {
    id: "ledger_agent",
    name: "Neon Truth Ledger",
    phase: "8. Persistence",
    role: "Permanently logs immutable verification audit record, forensic hashes, and citations into Neon Serverless Postgres.",
    tools: ["SQLModel / Neon Serverless Postgres Driver", "Neon S3 Object Storage (Bucket: assets)", "Neo4j Graph Database Driver"],
    defaultInputs: { verdict: "Evaluated Result", confidence: 0.99 },
    defaultOutputs: { record_id: "UUID-v4", target: "Neon Serverless Postgres neondb", table: "claim_records" }
  }
];

export const AgentGraphInspector: React.FC<AgentGraphInspectorProps> = ({
  executionTrace = [],
  isVerifying,
  shortCircuited = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"node" | "timeline">("timeline");
  const [selectedAgentId, setSelectedAgentId] = useState<string>("source_agent");

  // Map execution trace by agent_id for instant lookup
  const traceMap = new Map<string, AgentExecutionTraceItem>();
  executionTrace.forEach((t) => traceMap.set(t.agent_id, t));

  const selectedNode = GRAPH_NODES.find((n) => n.id === selectedAgentId) || GRAPH_NODES[0];
  const selectedTrace = traceMap.get(selectedNode.id);

  const inputsToDisplay = selectedTrace?.inputs || selectedNode.defaultInputs;
  const outputsToDisplay = selectedTrace?.outputs || selectedNode.defaultOutputs;
  const toolsToDisplay = selectedTrace?.tools || selectedNode.tools;

  return (
    <div className="w-full rounded-2xl bg-[#0D1527] border border-white/10 shadow-xl overflow-hidden transition-all">
      {/* Header with Inspector Toggle */}
      <div className="p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4 border-b border-white/5 bg-[#090F1E]/60">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Workflow className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white text-sm">
                Multi-Agent LangGraph Swarm & Data-Flow
              </h3>
              {shortCircuited && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  ⚡ Cache Short-Circuit
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Live DAG state transitions, agent-to-agent data flow, and tool invocations
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {isOpen && (
            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-900 border border-white/10 text-[11px]">
              <button
                onClick={() => setActiveTab("timeline")}
                className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                  activeTab === "timeline"
                    ? "bg-cyan-500 text-slate-950 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Trace Timeline
              </button>
              <button
                onClick={() => setActiveTab("node")}
                className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                  activeTab === "node"
                    ? "bg-cyan-500 text-slate-950 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Node Payloads
              </button>
            </div>
          )}

          <button
            onClick={() => setIsOpen(!isOpen)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all border ${
              isOpen
                ? "bg-cyan-500 text-slate-950 border-cyan-400 shadow-md shadow-cyan-500/20"
                : "bg-slate-900 hover:bg-slate-800 text-slate-200 border-white/10"
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${isVerifying ? "animate-spin text-cyan-400" : ""}`} />
            <span>{isOpen ? "Collapse Trace" : "Inspect Agent Trace & Tools"}</span>
            <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isOpen ? "rotate-90" : ""}`} />
          </button>
        </div>
      </div>

      {/* Interactive Agent Flow Strip */}
      <div className="p-4 sm:p-5 overflow-x-auto border-b border-white/5">
        <div className="flex items-center gap-2 min-w-max pb-2">
          {GRAPH_NODES.map((node, index) => {
            const trace = traceMap.get(node.id);
            const isSelected = selectedAgentId === node.id;
            const isCompleted = Boolean(trace);
            const isRunning = isVerifying && !trace;

            return (
              <React.Fragment key={node.id}>
                <button
                  onClick={() => {
                    setSelectedAgentId(node.id);
                    if (!isOpen) setIsOpen(true);
                  }}
                  className={`text-left p-3 rounded-xl border transition-all flex flex-col justify-between gap-2.5 min-w-[145px] max-w-[155px] relative ${
                    isSelected
                      ? "bg-cyan-950/40 border-cyan-400 ring-2 ring-cyan-400/20 shadow-lg shadow-cyan-950/50"
                      : isCompleted
                      ? "bg-emerald-950/20 border-emerald-500/30 hover:border-emerald-500/60"
                      : isRunning
                      ? "bg-cyan-950/20 border-cyan-500/40 animate-pulse"
                      : "bg-[#090F1E] border-white/5 hover:border-white/20 opacity-75"
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-mono text-[10px] text-slate-500">#{index + 1}</span>
                    {isCompleted ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    ) : isRunning ? (
                      <Clock className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-slate-700" />
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-white truncate">{node.name}</p>
                    <p className="font-mono text-[10px] text-slate-400 truncate mt-0.5">
                      {isCompleted
                        ? `${trace?.duration_ms || 28}ms`
                        : isRunning
                        ? "Active..."
                        : node.phase.split(". ")[1]}
                    </p>
                  </div>

                  {/* Tool Pill Preview */}
                  <div className="pt-1 border-t border-white/5 flex items-center gap-1 text-[9px] font-mono text-cyan-400/80 truncate">
                    <Code2 className="w-2.5 h-2.5 shrink-0" />
                    <span className="truncate">{node.tools[0].split("(")[0]}</span>
                  </div>
                </button>

                {/* Connecting Flow Arrow with Animation */}
                {index < GRAPH_NODES.length - 1 && (
                  <div className="flex items-center text-slate-600 px-0.5">
                    <ArrowRight className={`w-3.5 h-3.5 ${isVerifying ? "text-cyan-400 animate-pulse" : ""}`} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Expanded Deep Inspector Drawer */}
      {isOpen && (
        <div className="border-t border-white/10 bg-[#070D1B] p-5 sm:p-6 animate-in slide-in-from-top-3 duration-200">
          {activeTab === "timeline" ? (
            /* Tab 1: Detailed Chronological Trace Timeline Table */
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  <h4 className="text-sm font-bold text-white">
                    Agent-to-Agent Execution Trace & Tools Called
                  </h4>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {executionTrace.length > 0
                    ? `${executionTrace.length} Active Steps Recorded`
                    : "Standard Swarm Topology"}
                </span>
              </div>

              <div className="overflow-x-auto rounded-xl border border-white/5 bg-[#090F1E]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0D1527] border-b border-white/5 text-[11px] font-mono uppercase text-slate-400">
                    <tr>
                      <th className="py-2.5 px-3">Step</th>
                      <th className="py-2.5 px-3">Agent Name</th>
                      <th className="py-2.5 px-3">Tools / APIs Invoked</th>
                      <th className="py-2.5 px-3">Data Flow Transition</th>
                      <th className="py-2.5 px-3 text-right">Latency</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-sans">
                    {(executionTrace.length > 0 ? executionTrace : GRAPH_NODES).map((item: any, idx: number) => {
                      const nodeDef = GRAPH_NODES.find((n) => n.id === item.agent_id || n.id === item.id) || GRAPH_NODES[idx];
                      const isLast = idx === (executionTrace.length || GRAPH_NODES.length) - 1;
                      const nextNode = GRAPH_NODES[idx + 1];
                      const duration = item.duration_ms || 24;

                      return (
                        <tr
                          key={idx}
                          onClick={() => {
                            setSelectedAgentId(nodeDef.id);
                            setActiveTab("node");
                          }}
                          className="hover:bg-cyan-500/5 transition-colors cursor-pointer"
                        >
                          <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px]">
                            #{idx + 1}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex flex-col">
                              <span className="font-semibold text-white text-xs">
                                {item.agent_name || nodeDef.name}
                              </span>
                              <span className="font-mono text-[10px] text-cyan-400/80">
                                {item.agent_id || nodeDef.id}
                              </span>
                            </div>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[11px] text-slate-300">
                            <div className="flex flex-wrap gap-1 max-w-xs">
                              {(item.tools || nodeDef.tools).map((t: string, ti: number) => (
                                <span
                                  key={ti}
                                  className="px-1.5 py-0.5 rounded bg-slate-900 border border-white/5 text-[10px] text-cyan-300 truncate"
                                >
                                  {t.split("(")[0]}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                            {!isLast && nextNode ? (
                              <span className="flex items-center gap-1.5 text-amber-300/80">
                                <span>Emits state</span>
                                <ArrowRight className="w-3 h-3 text-cyan-400" />
                                <span className="font-semibold text-white">{nextNode.name}</span>
                              </span>
                            ) : (
                              <span className="text-emerald-400 font-semibold">Finalized ➔ Verified Result</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-300 text-right">
                            {duration}ms
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                              <CheckCircle2 className="w-2.5 h-2.5" />
                              OK
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            /* Tab 2: Individual Node Payloads (Data In / Data Out) */
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Agent Profile & Tools Executed */}
              <div className="flex flex-col gap-4">
                <div className="p-4 rounded-xl bg-[#0D1527] border border-white/10 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400">
                      {selectedNode.phase}
                    </span>
                    {selectedTrace && (
                      <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                        Duration: {selectedTrace.duration_ms}ms
                      </span>
                    )}
                  </div>

                  <h4 className="text-base font-bold text-white flex items-center gap-2">
                    {selectedNode.name}
                    <span className="text-xs font-normal font-mono text-slate-400">
                      ({selectedNode.id})
                    </span>
                  </h4>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {selectedNode.role}
                  </p>
                </div>

                {/* Tools Executed by This Agent */}
                <div className="p-4 rounded-xl bg-[#0D1527] border border-white/10 flex flex-col gap-2.5">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <Terminal className="w-4 h-4 text-cyan-400" />
                    <span>Tools & APIs Called:</span>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    {toolsToDisplay.map((tool, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 p-2 rounded-lg bg-[#090F1E] border border-white/5 font-mono text-xs text-cyan-300"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span className="truncate">{tool}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Middle Column: Data Input */}
              <div className="p-4 rounded-xl bg-[#0D1527] border border-white/10 flex flex-col gap-3">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <Code2 className="w-4 h-4 text-amber-400" />
                    <span>Data In (Inputs from Previous Node):</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">JSON Payload</span>
                </div>

                <pre className="p-3 rounded-lg bg-[#050A14] border border-white/5 font-mono text-xs text-amber-300/90 overflow-x-auto max-h-56 leading-relaxed">
                  {JSON.stringify(inputsToDisplay, null, 2)}
                </pre>

                <p className="text-[11px] text-slate-400 leading-normal">
                  State passed directly through LangGraph channel memory into this agent node.
                </p>
              </div>

              {/* Right Column: Data Output */}
              <div className="p-4 rounded-xl bg-[#0D1527] border border-white/10 flex flex-col gap-3">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                    <Database className="w-4 h-4 text-emerald-400" />
                    <span>Data Out (State Emitted to Next Node):</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">State Delta</span>
                </div>

                <pre className="p-3 rounded-lg bg-[#050A14] border border-white/5 font-mono text-xs text-emerald-300/90 overflow-x-auto max-h-56 leading-relaxed">
                  {JSON.stringify(outputsToDisplay, null, 2)}
                </pre>

                <p className="text-[11px] text-slate-400 leading-normal">
                  Outputs returned by this node and merged into the shared LangGraph <code className="text-cyan-400">AgentState</code>.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
