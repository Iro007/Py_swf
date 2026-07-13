import React, { useState } from "react";
import { Download, Upload, Image as ImageIcon, Sparkles, Check, FileCode } from "lucide-react";

interface ImageViewerProps {
  id: number;
  name: string;
  width: number;
  height: number;
  color: string; // fallback accent color
  type: "PNG" | "JPEG";
  caption: string;
  dataUrl?: string | null;
}

export default function ImageViewer({ id, name, width, height, color, type, caption, dataUrl }: ImageViewerProps) {
  const [isExported, setIsExported] = useState<boolean>(false);
  const [replacedName, setReplacedName] = useState<string | null>(null);

  const handleExport = () => {
    setIsExported(true);
    setTimeout(() => {
      setIsExported(false);
    }, 2000);
    
    // Simulate downloading PNG file
    const element = document.createElement("a");
    const file = new Blob([`mock-image-payload-id-${id}`], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = name;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setReplacedName(e.target.files[0].name);
    }
  };

  return (
    <div id={`image-viewer-${id}`} className="bg-slate-900 border border-slate-700/60 rounded-xl overflow-hidden shadow-2xl transition duration-300 hover:border-slate-600/80 p-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
            <ImageIcon className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-slate-100 font-medium text-sm font-sans">{name}</h4>
            <p className="text-[10px] font-mono text-slate-400">DefineBitsLossless ID: #{id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-slate-950 px-2.5 py-1 rounded text-xs font-mono text-blue-400">
          <span>{type} Asset</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Pixel design asset canvas mock or dynamic decompressed image */}
        <div className="relative flex flex-col items-center justify-center bg-slate-950 border border-slate-850 rounded-xl p-6 min-h-[220px]">
          {dataUrl ? (
            <div className="relative group overflow-hidden rounded-lg border border-slate-800 bg-[#0f172a] p-1 shadow-lg max-w-[200px] max-h-[200px] flex items-center justify-center">
              <img
                src={dataUrl}
                alt={name}
                referrerPolicy="no-referrer"
                className="max-w-full max-h-[160px] object-contain rounded transition transform group-hover:scale-105"
              />
            </div>
          ) : (
            /* A beautiful pixel bento visual representation */
            <div 
              className="w-32 h-32 rounded-lg flex items-center justify-center shadow-lg relative overflow-hidden transition transform hover:scale-105"
              style={{ 
                backgroundColor: color, 
                backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.15) 10%, transparent 20%)",
                backgroundSize: "16px 16px"
              }}
            >
              {/* Overlay grid lines */}
              <div className="absolute inset-0 bg-slate-950/20 grid grid-cols-8 grid-rows-8 gap-px pointer-events-none">
                {Array.from({ length: 64 }).map((_, i) => (
                  <div key={i} className="border-[0.5px] border-white/5" />
                ))}
              </div>

              <Sparkles className="w-8 h-8 text-white/50 drop-shadow-md animate-pulse" />
            </div>
          )}

          <span className="mt-4 text-[10px] font-mono text-slate-500">
            Render Dimensions: {width} x {height} px • BitDepth: 32bpp ARGB
          </span>
        </div>

        {/* Right: Asset Properties Table & Editing Actions */}
        <div className="flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <span className="block text-[10px] uppercase tracking-wider font-mono text-slate-400 font-semibold mb-2">
                Header Attributes
              </span>
              <div className="bg-slate-950 border border-slate-850 p-3 rounded-lg text-xs font-mono text-slate-300 space-y-2">
                <div className="flex justify-between border-b border-slate-900 pb-1.5">
                  <span className="text-slate-500">Compression:</span>
                  <span className="text-slate-100">Zlib DEFLATE</span>
                </div>
                <div className="flex justify-between border-b border-slate-900 pb-1.5">
                  <span className="text-slate-500">Original Format:</span>
                  <span className="text-slate-100">{type} Tag</span>
                </div>
                <div className="flex justify-between border-b border-slate-900 pb-1.5">
                  <span className="text-slate-500">Asset size:</span>
                  <span className="text-slate-100">{(width * height * 4 / 1024).toFixed(1)} KB (decompressed)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Alpha transparency:</span>
                  <span className="text-emerald-400">Yes (ARGB)</span>
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-400 font-sans italic leading-relaxed">
              {caption}
            </div>

            {replacedName && (
              <div className="flex items-center gap-2 p-2 bg-emerald-900/20 border border-emerald-800/40 rounded-lg text-emerald-300 text-xs font-mono">
                <Check className="w-4 h-4" />
                <span>Replaced with: {replacedName}</span>
              </div>
            )}
          </div>

          {/* Buttons: Export & Replace */}
          <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-800/60">
            <button
              onClick={handleExport}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition active:scale-95"
            >
              {isExported ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  Exported!
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5 text-blue-400" />
                  Export Image
                </>
              )}
            </button>

            <label className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition cursor-pointer active:scale-95 text-center">
              <Upload className="w-3.5 h-3.5" />
              <span>Replace Asset</span>
              <input
                type="file"
                accept="image/*.png, image/*.jpeg, image/*.jpg"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
