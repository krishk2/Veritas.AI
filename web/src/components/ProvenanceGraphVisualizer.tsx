"use client";

import React, { useState, useMemo } from "react";
import {
  Share2,
  Database,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Globe,
  FileText,
  Camera,
  Layers,
  Sparkles,
  Maximize2,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Eye
} from "lucide-react";
import { TruthGlobe3D } from "./TruthGlobe3D";

export interface GraphNode {
  id: string;
  label: string;
  type: "claim" | "evidence" | "source" | "domain" | "forensics";
  title?: string;
  verdict?: string;
  confidence?: number;
  score?: number;
  domain?: string;
  url?: string;
  credibility_status?: string;
  summary?: string;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface ProvenanceGraphData {
  connected: boolean;
  claim_id?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface ProvenanceGraphVisualizerProps {
  graphData?: ProvenanceGraphData | null;
  verdict?: "TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIED" | null;
  confidence?: number;
  claimText?: string;
  neo4jConnected?: boolean;
}

export const ProvenanceGraphVisualizer: React.FC<ProvenanceGraphVisualizerProps> = ({
  graphData,
  verdict,
  confidence = 0.88,
  claimText = "",
  neo4jConnected = false,
}) => {
  const [viewMode, setViewMode] = useState<"topology" | "sphere">("topology");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("claim");

  // Derive nodes and edges, synthesizing if empty
  const { nodes, edges } = useMemo(() => {
    if (graphData && graphData.nodes && graphData.nodes.length > 0) {
      return { nodes: graphData.nodes, edges: graphData.edges || [] };
    }

    // Default synthesized topology if no data passed yet
    const synthNodes: GraphNode[] = [
      {
        id: "claim",
        label: "Evaluated Claim",
        type: "claim",
        title: claimText ? (claimText.length > 80 ? claimText.slice(0, 80) + "..." : claimText) : "Evaluating Claim...",
        verdict: verdict || "UNVERIFIED",
        confidence: confidence,
      },
      {
        id: "ev_1",
        label: "Evidence [SUPPORT]",
        type: "evidence",
        title: "Official reporting corroborates facts",
        verdict: "SUPPORT",
        score: 0.92,
      },
      {
        id: "ev_2",
        label: "Evidence [REFUTE]",
        type: "evidence",
        title: "Disproven by primary record statement",
        verdict: "REFUTE",
        score: 0.88,
      },
      {
        id: "src_1",
        label: "Web Source",
        type: "source",
        domain: "reuters.com",
        title: "Reuters News Agency",
        url: "https://reuters.com",
        credibility_status: "Trusted",
      },
      {
        id: "forensics_1",
        label: "Multimodal Vision",
        type: "forensics",
        title: "Gemini 2.5 Flash Vision & ELA Verification",
        summary: "Visual alignment analyzed",
      },
    ];

    const synthEdges: GraphEdge[] = [
      { source: "claim", target: "ev_1", label: "HAS_EVIDENCE" },
      { source: "claim", target: "ev_2", label: "HAS_EVIDENCE" },
      { source: "claim", target: "src_1", label: "INVESTIGATED_SOURCE" },
      { source: "claim", target: "forensics_1", label: "MEDIA_FORENSICS" },
    ];

    return { nodes: synthNodes, edges: synthEdges };
  }, [graphData, verdict, confidence, claimText]);

  // Compute 2D circular topology coordinates for rendering
  const layout = useMemo(() => {
    const width = 480;
    const height = 360;
    const centerX = width / 2;
    const centerY = height / 2;

    const claimNode = nodes.find((n) => n.type === "claim") || nodes[0];
    const otherNodes = nodes.filter((n) => n.id !== claimNode?.id);

    const positions = new Map<string, { x: number; y: number }>();
    if (claimNode) {
      positions.set(claimNode.id, { x: centerX, y: centerY });
    }

    const radius = 135;
    const totalOthers = otherNodes.length;

    otherNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / (totalOthers || 1) - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      positions.set(node.id, { x, y });
    });

    return { width, height, positions };
  }, [nodes]);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || nodes[0];

  // Helper colors based on node types
  const getNodeColor = (node: GraphNode) => {
    if (node.type === "claim") {
      return verdict === "TRUE" ? "#10b981" : verdict === "FALSE" ? "#f43f5e" : "#f59e0b";
    }
    if (node.type === "evidence") {
      return node.verdict === "SUPPORT" ? "#10b981" : "#f43f5e";
    }
    if (node.type === "source" || node.type === "domain") {
      return "#06b6d4";
    }
    return "#8b5cf6"; // forensics
  };

  return (
    <div className="w-full h-full flex flex-col justify-between rounded-2xl bg-[#090F1E] border border-white/10 overflow-hidden shadow-2xl relative">
      {/* Visualizer Top Bar */}
      <div className="p-4 flex items-center justify-between border-b border-white/5 bg-[#0D1527]/70 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Share2 className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold text-white tracking-wide">
                Provenance Knowledge Graph
              </h4>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-mono border font-semibold flex items-center gap-1 ${
                  neo4jConnected
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                }`}
              >
                <Database className="w-2.5 h-2.5" />
                {neo4jConnected ? "Neo4j AuraDB Active" : "In-Memory Graph"}
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-400">
              {nodes.length} Nodes • {edges.length} Directed Relationships
            </p>
          </div>
        </div>

        {/* View Switcher: Topology vs 3D Sphere */}
        <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-900 border border-white/10 text-[11px]">
          <button
            onClick={() => setViewMode("topology")}
            className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
              viewMode === "topology"
                ? "bg-cyan-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Topology
          </button>
          <button
            onClick={() => setViewMode("sphere")}
            className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
              viewMode === "sphere"
                ? "bg-cyan-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            3D Globe
          </button>
        </div>
      </div>

      {/* Main View Area */}
      <div className="relative w-full h-[290px] flex items-center justify-center overflow-hidden bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#0e172a] via-[#070b14] to-[#04070e]">
        {viewMode === "sphere" ? (
          <TruthGlobe3D verdict={verdict} activeNodeCount={nodes.length} />
        ) : (
          <svg
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            className="w-full h-full cursor-grab active:cursor-grabbing select-none"
          >
            {/* Background Grid Pattern */}
            <defs>
              <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
              </pattern>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            <rect width={layout.width} height={layout.height} fill="url(#grid)" />

            {/* Connecting Edges */}
            {edges.map((edge, idx) => {
              const posA = layout.positions.get(edge.source);
              const posB = layout.positions.get(edge.target);
              if (!posA || !posB) return null;

              const isHighlighted =
                selectedNodeId === edge.source || selectedNodeId === edge.target;

              return (
                <g key={idx} className="transition-all duration-300">
                  <line
                    x1={posA.x}
                    y1={posA.y}
                    x2={posB.x}
                    y2={posB.y}
                    stroke={isHighlighted ? "#38bdf8" : "rgba(255,255,255,0.12)"}
                    strokeWidth={isHighlighted ? 2 : 1}
                    strokeDasharray={isHighlighted ? "none" : "3,3"}
                  />
                  {/* Midpoint Label Preview */}
                  <text
                    x={(posA.x + posB.x) / 2}
                    y={(posA.y + posB.y) / 2 - 4}
                    fill={isHighlighted ? "#7dd3fc" : "rgba(148,163,184,0.4)"}
                    fontSize="7"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    {edge.label.split(" ")[0]}
                  </text>
                </g>
              );
            })}

            {/* Render Nodes */}
            {nodes.map((node) => {
              const pos = layout.positions.get(node.id);
              if (!pos) return null;

              const isSelected = selectedNodeId === node.id;
              const isClaim = node.type === "claim";
              const color = getNodeColor(node);

              return (
                <g
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  className="cursor-pointer transition-transform duration-200 hover:scale-110"
                >
                  {/* Outer Pulsing Aura for Selected or Claim Node */}
                  {(isSelected || isClaim) && (
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={isClaim ? 36 : 24}
                      fill="none"
                      stroke={color}
                      strokeWidth="1.5"
                      strokeOpacity={isSelected ? "0.6" : "0.2"}
                      className="animate-pulse"
                    />
                  )}

                  {/* Core Node Circle */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={isClaim ? 26 : 17}
                    fill="#0A1122"
                    stroke={color}
                    strokeWidth={isSelected ? 3 : 2}
                    filter="url(#glow)"
                  />

                  {/* Node Label Text */}
                  <text
                    cx={pos.x}
                    cy={pos.y + (isClaim ? 36 : 26)}
                    x={pos.x}
                    y={pos.y + (isClaim ? 40 : 28)}
                    fill={isSelected ? "#ffffff" : "#94a3b8"}
                    fontSize={isClaim ? "10" : "8"}
                    fontWeight={isSelected ? "bold" : "normal"}
                    fontFamily="sans-serif"
                    textAnchor="middle"
                  >
                    {node.type === "claim"
                      ? "Claim Hub"
                      : node.domain || node.label.slice(0, 14)}
                  </text>

                  {/* Node Center Icon Text */}
                  <text
                    x={pos.x}
                    y={pos.y + 3}
                    fill={color}
                    fontSize={isClaim ? "12" : "9"}
                    fontFamily="monospace"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    {isClaim
                      ? verdict === "TRUE"
                        ? "✓"
                        : "✗"
                      : node.type === "evidence"
                      ? node.verdict === "SUPPORT"
                        ? "+"
                        : "-"
                      : node.type === "source"
                      ? "🔗"
                      : "👁"}
                  </text>
                </g>
              );
            })}
          </svg>
        )}
      </div>

      {/* Selected Node Details Drawer */}
      <div className="p-3.5 bg-[#070D1B] border-t border-white/5 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div
            className="p-2 rounded-xl shrink-0"
            style={{ backgroundColor: `${getNodeColor(selectedNode)}20`, color: getNodeColor(selectedNode) }}
          >
            {selectedNode.type === "claim" ? (
              <ShieldCheck className="w-4 h-4" />
            ) : selectedNode.type === "source" ? (
              <Globe className="w-4 h-4" />
            ) : selectedNode.type === "forensics" ? (
              <Camera className="w-4 h-4" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
          </div>

          <div className="flex flex-col truncate">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white truncate text-[11px]">
                {selectedNode.title || selectedNode.label}
              </span>
              <span
                className="text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold uppercase"
                style={{
                  borderColor: `${getNodeColor(selectedNode)}40`,
                  color: getNodeColor(selectedNode),
                }}
              >
                {selectedNode.type}
              </span>
            </div>

            <p className="text-[10px] text-slate-400 font-mono truncate">
              {selectedNode.domain
                ? `Domain: ${selectedNode.domain} • Credibility: ${selectedNode.credibility_status || "Audited"}`
                : selectedNode.score
                ? `NLI Confidence: ${Math.round(selectedNode.score * 100)}%`
                : selectedNode.summary || `Graph ID: ${selectedNode.id}`}
            </p>
          </div>
        </div>

        {selectedNode.url && (
          <a
            href={selectedNode.url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500 hover:text-slate-950 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
    </div>
  );
};
