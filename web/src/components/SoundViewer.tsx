import React, { useEffect, useState } from "react";
import { Download, Music } from "lucide-react";
import { getSoundInfo, soundUrl } from "../api";
import { SoundInfo } from "../types";

interface Props {
  sid: string;
  tagIndex: number;
  tagName: string;
  charId: number | null;
  onError: (msg: string) => void;
}

export default function SoundViewer({ sid, tagIndex, tagName, charId, onError }: Props) {
  const [info, setInfo] = useState<SoundInfo | null>(null);
  const src = soundUrl(sid, tagIndex);

  useEffect(() => {
    setInfo(null);
    getSoundInfo(sid, tagIndex)
      .then(setInfo)
      .catch((e) => onError(`Sound info failed: ${e.message}`));
  }, [sid, tagIndex]);

  const playable = info && (info.format === 2 || info.format === 0 || info.format === 1 || info.format === 3);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Music className="w-4 h-4 text-pink-400" />
          <span className="font-sans text-sm text-slate-200 font-semibold">{tagName}</span>
          {charId != null && <span className="text-[10px] font-mono text-slate-500">char id #{charId}</span>}
        </div>
        <a
          href={src}
          download={`sound_${charId ?? tagIndex}`}
          className="p-1 px-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition flex items-center gap-1 border border-slate-700/40"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export</span>
        </a>
      </div>

      <div className="p-6 space-y-4">
        {info && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
              <span className="block text-[9px] uppercase text-slate-500 font-bold mb-1">Format</span>
              <span className="text-pink-300 font-semibold">{info.format_name}</span>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
              <span className="block text-[9px] uppercase text-slate-500 font-bold mb-1">Rate</span>
              <span className="text-slate-200">{info.rate} Hz</span>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
              <span className="block text-[9px] uppercase text-slate-500 font-bold mb-1">Channels</span>
              <span className="text-slate-200">{info.channels === 2 ? "stereo" : "mono"} / {info.bits}-bit</span>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3">
              <span className="block text-[9px] uppercase text-slate-500 font-bold mb-1">Samples</span>
              <span className="text-slate-200">
                {info.sample_count} (~{(info.sample_count / info.rate).toFixed(1)}s)
              </span>
            </div>
          </div>
        )}

        {playable ? (
          <audio controls src={src} className="w-full" onError={() => onError("Audio could not be decoded")} />
        ) : (
          info && (
            <p className="text-xs font-mono text-slate-500">
              {info.format_name} no es reproducible en el navegador; usa Export para obtener los
              bytes crudos.
            </p>
          )
        )}
      </div>
    </div>
  );
}
