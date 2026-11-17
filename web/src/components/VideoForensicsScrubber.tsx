"use client";

import React, { useState } from "react";
import { Film, AlertOctagon, CheckCircle2 } from "lucide-react";

interface KeyframeData {
  time_offset_sec: number;
  anomaly_score: number;
  has_face_seam: boolean;
  notes: string;
}

interface VideoForensicsScrubberProps {
  isDeepfake?: boolean;
  confidence?: number;
  videoSrc?: string;
  keyframes?: KeyframeData[];
}

export const VideoForensicsScrubber: React.FC<VideoForensicsScrubberProps> = ({
  isDeepfake = false,
  confidence = 0.88,
  videoSrc,
  keyframes = [
    { time_offset_sec: 0.5, anomaly_score: 12, has_face_seam: false, notes: "Natural motion vector" },
    { time_offset_sec: 1.5, anomaly_score: 18, has_face_seam: false, notes: "Consistent lighting" },
    { time_offset_sec: 2.8, anomaly_score: 84, has_face_seam: true, notes: "Jawline boundary blending artifact" },
    { time_offset_sec: 4.2, anomaly_score: 79, has_face_seam: true, notes: "Irregular blinking frequency" },
  ],
}) => {
  const [selectedFrameIdx, setSelectedFrameIdx] = useState(2);
  const currentFrame = keyframes[selectedFrameIdx] || keyframes[0];

  return (
    <div className="rounded-2xl bg-[#0D1527] border border-white/10 p-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white text-base">Video Deepfake & AI Audit</h3>
            <p className="text-xs text-slate-400">Temporal Keyframe Face-Swap & Generative Inspection</p>
          </div>
        </div>

        {isDeepfake ? (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertOctagon className="w-3.5 h-3.5" />
            Synthetic Deepfake ({Math.round(confidence * 100)}%)
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Authentic Footage
          </span>
        )}
      </div>

      {/* Video & Keyframe Display */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Video Player or Placeholder */}
        <div className="w-full h-48 rounded-xl bg-black border border-white/10 overflow-hidden flex items-center justify-center relative">
          {videoSrc ? (
            <video src={videoSrc} controls className="w-full h-full object-contain" />
          ) : (
            <div className="text-center p-4">
              <Film className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 font-mono">Temporal Video Sample (00:05.4)</p>
            </div>
          )}
        </div>

        {/* Selected Keyframe Forensic Inspection */}
        <div className="p-4 rounded-xl bg-[#090F1E] border border-white/5 flex flex-col justify-between gap-3 text-xs">
          <div>
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
              Sampled Frame at {currentFrame.time_offset_sec.toFixed(1)}s
            </span>
            <div className="flex items-center justify-between mt-1">
              <span className="font-semibold text-white text-sm">Face-Swap Seam Probability</span>
              <span
                className={`font-mono text-sm font-bold ${
                  currentFrame.anomaly_score > 50 ? "text-rose-400" : "text-emerald-400"
                }`}
              >
                {currentFrame.anomaly_score}%
              </span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/90 border border-white/5 text-slate-300 leading-relaxed">
            <span className="font-semibold text-cyan-400">Forensic Diagnostic:</span>{" "}
            {currentFrame.notes}
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-white/5">
            <span>Seam Artifacts: {currentFrame.has_face_seam ? "Detected" : "None"}</span>
            <span className="text-cyan-400 font-mono">OpenCV + Gemini Vision</span>
          </div>
        </div>
      </div>

      {/* Interactive Temporal Scrubber Bar */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>0.0s (Start)</span>
          <span className="font-mono text-cyan-400">Select frame to inspect</span>
          <span>5.0s (End)</span>
        </div>

        <div className="flex gap-2">
          {keyframes.map((frame, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedFrameIdx(idx)}
              className={`flex-1 py-2 px-3 rounded-lg border text-xs font-mono transition-all flex flex-col items-center gap-1 ${
                selectedFrameIdx === idx
                  ? "bg-cyan-500/20 border-cyan-400 text-white shadow-md shadow-cyan-500/10"
                  : frame.anomaly_score > 50
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-300 hover:bg-rose-500/20"
                  : "bg-slate-900 border-white/5 text-slate-400 hover:bg-slate-800"
              }`}
            >
              <span>{frame.time_offset_sec.toFixed(1)}s</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  frame.anomaly_score > 50 ? "bg-rose-400" : "bg-emerald-400"
                }`}
              />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
