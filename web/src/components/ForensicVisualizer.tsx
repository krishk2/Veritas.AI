"use client";

import React, { useState } from "react";
import { ShieldAlert, Cpu, Camera, MapPin, Hash, Sparkles } from "lucide-react";

interface ForensicVisualizerProps {
  imageSrc?: string;
  elaScore?: number;
  softwareUsed?: string[];
  aiGenerator?: string;
  exifData?: Record<string, string>;
  dHash?: string;
}

export const ForensicVisualizer: React.FC<ForensicVisualizerProps> = ({
  imageSrc,
  elaScore = 14.8,
  softwareUsed = [],
  aiGenerator,
  exifData = {},
  dHash = "a3f1c8b2d4e7f9a1",
}) => {
  const [sliderPos, setSliderPos] = useState(50);
  const isManipulated = elaScore > 20 || Boolean(aiGenerator) || softwareUsed.length > 0;

  return (
    <div className="rounded-2xl bg-[#0D1527] border border-white/10 p-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white text-base">Multimodal Image Forensics</h3>
            <p className="text-xs text-slate-400">Error Level Analysis & Generative AI Inspection</p>
          </div>
        </div>

        {isManipulated ? (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-3.5 h-3.5" />
            Manipulation Detected
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Forensically Clean
          </span>
        )}
      </div>

      {/* Interactive ELA Split-Screen Slider */}
      {imageSrc ? (
        <div className="relative w-full h-64 rounded-xl overflow-hidden select-none border border-white/10 bg-black">
          {/* Base Image */}
          <img
            src={imageSrc}
            alt="Original"
            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
          />

          {/* ELA Simulated Heatmap Overlay */}
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
          >
            <div className="w-full h-full relative bg-slate-950/80 filter contrast-200 invert brightness-125 flex items-center justify-center">
              <img
                src={imageSrc}
                alt="ELA View"
                className="w-full h-full object-contain mix-blend-color-dodge opacity-80"
              />
              <div className="absolute top-3 right-3 px-2 py-0.5 rounded bg-rose-600/90 text-white font-mono text-[10px] tracking-wider uppercase font-bold">
                ELA Heatmap
              </div>
            </div>
          </div>

          {/* Slider Divider Bar */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-cyan-400 cursor-ew-resize z-20"
            style={{ left: `${sliderPos}%` }}
          >
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-cyan-400 text-slate-950 flex items-center justify-center text-[10px] font-bold shadow-lg">
              ↔
            </div>
          </div>

          <input
            type="range"
            min="0"
            max="100"
            value={sliderPos}
            onChange={(e) => setSliderPos(Number(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-30"
          />
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-[#090F1E] border border-dashed border-white/10 flex items-center justify-center text-xs text-slate-500 py-10">
          No visual media attached to this claim. Attach an image to run Error Level Analysis.
        </div>
      )}

      {/* Forensic Telemetry Matrix */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {/* ELA Variance */}
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col gap-1">
          <span className="text-slate-400">ELA Noise Variance</span>
          <span className={`font-mono text-sm font-semibold ${elaScore > 20 ? "text-rose-400" : "text-emerald-400"}`}>
            {elaScore.toFixed(1)}% {elaScore > 20 ? "(High Anomaly)" : "(Consistent)"}
          </span>
        </div>

        {/* AI Generator Signature */}
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col gap-1">
          <span className="text-slate-400 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-amber-400" /> AI Generator
          </span>
          <span className="font-mono text-sm font-semibold text-white">
            {aiGenerator || "None Detected"}
          </span>
        </div>

        {/* Editing Software */}
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col gap-1">
          <span className="text-slate-400 flex items-center gap-1">
            <Camera className="w-3 h-3 text-cyan-400" /> Software Trace
          </span>
          <span className="font-mono text-sm font-semibold text-white truncate">
            {softwareUsed.length > 0 ? softwareUsed.join(", ") : "Untouched EXIF"}
          </span>
        </div>

        {/* dHash Fingerprint */}
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col gap-1">
          <span className="text-slate-400 flex items-center gap-1">
            <Hash className="w-3 h-3 text-slate-400" /> Perceptual dHash
          </span>
          <span className="font-mono text-xs font-semibold text-slate-300 truncate" title={dHash}>
            {dHash.slice(0, 12)}...
          </span>
        </div>
      </div>
    </div>
  );
};
