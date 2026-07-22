import React, { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { getEditTextInfo, getTextSvg } from "../api";

interface Props {
  sid: string;
  tagIndex: number;
  tagName: string;
  tagCode: number;
  onError: (msg: string) => void;
}

export default function TextViewer({ sid, tagIndex, tagName, tagCode, onError }: Props) {
  const [svg, setSvg] = useState<string | null>(null);
  const [props, setProps] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    setSvg(null);
    setProps(null);
    if (tagCode === 37) {
      getEditTextInfo(sid, tagIndex)
        .then(setProps)
        .catch((e) => onError(`EditText parse failed: ${e.message}`));
    } else {
      getTextSvg(sid, tagIndex)
        .then(setSvg)
        .catch((e) => onError(`Text render failed: ${e.message}`));
    }
  }, [sid, tagIndex, tagCode]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <FileText className="w-4 h-4 text-violet-400" />
        <span className="font-sans text-sm text-slate-200 font-semibold">{tagName}</span>
      </div>

      {svg && (
        <div className="p-6 bg-white/95 flex items-center justify-center min-h-[160px]">
          <div className="[&>svg]:max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />
        </div>
      )}

      {props && (
        <div className="p-5">
          <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg font-mono text-xs text-slate-200 divide-y divide-slate-900 max-h-[380px] overflow-y-auto">
            {Object.entries(props).map(([key, val]) => (
              <div key={key} className="flex justify-between py-1.5 gap-6">
                <span className="text-slate-500">{key}:</span>
                <span className="text-violet-300 truncate max-w-md text-right">
                  {typeof val === "object" ? JSON.stringify(val) : String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!svg && !props && (
        <div className="p-8 text-center text-xs font-mono text-slate-600">Loading…</div>
      )}
    </div>
  );
}
