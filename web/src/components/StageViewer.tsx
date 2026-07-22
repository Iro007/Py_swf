import React, { useEffect, useState } from "react";
import { Clapperboard } from "lucide-react";
import { frameSvgUrl, getTimelineInfo } from "../api";

interface Props {
  sid: string;
  onError: (msg: string) => void;
}

export default function StageViewer({ sid, onError }: Props) {
  const [frameCount, setFrameCount] = useState(0);
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    setFrame(0);
    setFrameCount(0);
    getTimelineInfo(sid)
      .then((info) => setFrameCount(info.frame_count))
      .catch((e) => onError(`Timeline info failed: ${e.message}`));
  }, [sid]);

  if (frameCount === 0) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-md">
      <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800 flex justify-between items-center gap-4">
        <div className="flex items-center gap-2">
          <Clapperboard className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono font-bold text-slate-300">Stage preview</span>
          <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            aproximado
          </span>
        </div>
        <div className="flex items-center gap-3 flex-1 max-w-sm">
          <input
            type="range"
            min={0}
            max={Math.max(0, frameCount - 1)}
            value={frame}
            onChange={(e) => setFrame(parseInt(e.target.value, 10))}
            className="flex-1 accent-emerald-500"
          />
          <span className="text-[10px] font-mono text-slate-400 w-16 text-right">
            {frame + 1} / {frameCount}
          </span>
        </div>
      </div>
      <div className="p-4 bg-slate-950/40 flex items-center justify-center">
        <img
          src={frameSvgUrl(sid, frame)}
          alt={`frame ${frame + 1}`}
          className="max-w-full max-h-[420px] border border-slate-800 shadow"
          onError={() => onError("Frame could not be rendered")}
        />
      </div>
    </div>
  );
}
