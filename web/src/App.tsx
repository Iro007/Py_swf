import React, { useMemo, useState } from "react";
import {
  AlertCircle, Folder, FolderOpen, FileSignature, Layers, Save, Upload,
} from "lucide-react";

import { FileInfo, TagInfo, TreeItem, SWFCategory } from "./types";
import { downloadUrl, getTags, uploadSwf } from "./api";

import ShapeViewer from "./components/ShapeViewer";
import ImageViewer from "./components/ImageViewer";
import ScriptViewer from "./components/ScriptViewer";
import SoundViewer from "./components/SoundViewer";
import FontViewer from "./components/FontViewer";
import TextViewer from "./components/TextViewer";
import StageViewer from "./components/StageViewer";
import SpriteViewer from "./components/SpriteViewer";
import HexPanel from "./components/HexPanel";

const SHAPE_TAGS = [2, 22, 32, 83];
const MORPH_TAGS = [46, 84];
const IMAGE_TAGS = [6, 20, 21, 35, 36, 90];
const SCRIPT_TAGS = [12, 59, 82];
const FONT_TAGS = [48, 75];
const TEXT_TAGS = [11, 33, 37];

export default function App() {
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [selectedTreeId, setSelectedTreeId] = useState<string>("header");
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    shapes: true,
    images: true,
    scripts: true,
  });
  const [activeTab, setActiveTab] = useState<"preview" | "hex">("preview");
  const [errorText, setErrorText] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const refreshTags = async (sid: string) => {
    setTags(await getTags(sid));
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const info = await uploadSwf(file);
      setFileInfo(info);
      await refreshTags(info.session_id);
      setSelectedTreeId("header");
      setDirty(false);
      setErrorText(null);
    } catch (err: any) {
      setErrorText(`SWF parsing failed: ${err.message}`);
    } finally {
      event.target.value = "";
    }
  };

  const markDirty = () => {
    setDirty(true);
    if (fileInfo) refreshTags(fileInfo.session_id).catch(() => undefined);
  };

  const toggleNode = (nodeId: string) => {
    setExpandedNodes((prev) => ({ ...prev, [nodeId]: !prev[nodeId] }));
  };

  const treeStructure = useMemo((): TreeItem[] => {
    if (!fileInfo) return [];

    const categories: Record<SWFCategory, TreeItem> = {
      header: { id: "header", label: "SWF File Header", type: "header" },
      shapes: { id: "shapes", label: "Shapes / Vectors", type: "shapes", children: [] },
      images: { id: "images", label: "Images / Bitmaps", type: "images", children: [] },
      sounds: { id: "sounds", label: "Sounds / Audio Blocks", type: "sounds", children: [] },
      texts: { id: "texts", label: "Texts / Fonts", type: "texts", children: [] },
      buttons: { id: "buttons", label: "Buttons / Triggers", type: "buttons", children: [] },
      sprites: { id: "sprites", label: "Sprites / MovieClips", type: "sprites", children: [] },
      scripts: { id: "scripts", label: "Scripts / ActionScript", type: "scripts", children: [] },
      frames: { id: "frames", label: "Frames / Timeline", type: "frames", children: [] },
      others: { id: "others", label: "Other Tags / Metadata", type: "others", children: [] },
    };

    tags.forEach((tag) => {
      const suffix = tag.symbol_name
        ? ` — ${tag.symbol_name}`
        : tag.char_id != null
          ? ` (#${tag.char_id})`
          : "";
      const node: TreeItem = {
        id: `tag-${tag.index}`,
        label: `${tag.name}${suffix}`,
        type: "tag-node",
        tagIndex: tag.index,
        tagCode: tag.code,
      };
      const t = tag.code;
      if (SHAPE_TAGS.includes(t) || MORPH_TAGS.includes(t)) categories.shapes.children?.push(node);
      else if (IMAGE_TAGS.includes(t)) categories.images.children?.push(node);
      else if ([14, 18, 19, 45].includes(t)) categories.sounds.children?.push(node);
      else if ([10, 11, 13, 33, 37, 48, 62, 73, 74, 75, 88, 91].includes(t)) categories.texts.children?.push(node);
      else if ([7, 34].includes(t)) categories.buttons.children?.push(node);
      else if (t === 39) categories.sprites.children?.push(node);
      else if (SCRIPT_TAGS.includes(t)) categories.scripts.children?.push(node);
      else if ([1, 43, 5, 28, 4, 26, 70].includes(t)) categories.frames.children?.push(node);
      else categories.others.children?.push(node);
    });

    return Object.values(categories);
  }, [fileInfo, tags]);

  const selectedTag: TagInfo | null = useMemo(() => {
    if (!selectedTreeId.startsWith("tag-")) return null;
    const idx = parseInt(selectedTreeId.replace("tag-", ""), 10);
    return tags.find((t) => t.index === idx) ?? null;
  }, [selectedTreeId, tags]);

  const sid = fileInfo?.session_id ?? "";

  return (
    <div id="pysw-app-root" className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none antialiased">
      {/* Top Navbar */}
      <header className="bg-[#0b0f19] border-b border-slate-800/80 px-6 py-3 shrink-0 flex flex-wrap items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-emerald-600 to-teal-500 rounded-xl shadow-md flex items-center justify-center">
            <Layers className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white">
              py_swf_editor
              <span className="ml-2 text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-extrabold border border-emerald-500/20">
                Python backend
              </span>
            </h1>
            <p className="text-[10px] text-slate-400 font-mono">SWF decompiler & editor — FastAPI + py_swf</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 cursor-pointer border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition active:scale-95 shadow">
            <Upload className="w-3.5 h-3.5 text-blue-400" />
            <span>Open SWF</span>
            <input type="file" accept=".swf" onChange={handleFileUpload} className="hidden" />
          </label>

          <a
            href={fileInfo ? downloadUrl(sid) : undefined}
            download={fileInfo?.filename}
            aria-disabled={!fileInfo}
            className={`flex items-center gap-1.5 font-bold px-3 py-1.5 rounded-lg text-xs transition shadow-md ${
              fileInfo
                ? "bg-emerald-500 hover:bg-emerald-600 active:scale-95 text-slate-950"
                : "bg-slate-800 text-slate-600 pointer-events-none"
            }`}
          >
            <Save className="w-3.5 h-3.5" />
            <span>{dirty ? "Save SWF *" : "Save SWF"}</span>
          </a>
        </div>
      </header>

      {errorText && (
        <div className="bg-red-500/15 border-b border-red-500/20 px-6 py-2 flex items-center gap-3 text-red-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{errorText}</span>
          <button onClick={() => setErrorText(null)} className="ml-auto text-[10px] uppercase text-red-500 font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Tree sidebar */}
        <aside className="w-80 bg-[#080d16] border-r border-slate-900 flex flex-col shrink-0 min-h-0">
          <div className="p-3 bg-slate-950/60 border-b border-slate-900 flex justify-between items-center text-xs text-slate-400 font-mono">
            <span className="font-bold">SWF DIRECTORY</span>
            {fileInfo && (
              <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-slate-500 font-medium">
                {tags.length} tags
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
            {!fileInfo && (
              <div className="text-center text-xs text-slate-600 font-mono p-6 leading-relaxed">
                Open a .swf file to explore its tags, images, shapes and bytecode.
              </div>
            )}
            {treeStructure.map((cat) => {
              const matches = selectedTreeId === cat.id;
              const hasChildren = !!cat.children?.length;
              const isExpanded = expandedNodes[cat.id];

              if (cat.id !== "header" && !hasChildren) return null;

              return (
                <div key={cat.id} className="space-y-0.5">
                  <div
                    onClick={() => {
                      if (hasChildren) toggleNode(cat.id);
                      setSelectedTreeId(cat.id);
                    }}
                    className={`flex items-center justify-between px-2 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition ${
                      matches
                        ? "bg-slate-800/40 text-emerald-400 border border-emerald-500/10 shadow-sm"
                        : "text-slate-300 hover:bg-slate-900"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <FolderOpen className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Folder className="w-4 h-4 text-slate-500" />
                      )}
                      <span className="truncate">{cat.label}</span>
                    </div>
                    {hasChildren && (
                      <span className="text-[9px] font-mono bg-slate-950 px-1.5 py-0.5 rounded text-slate-500 font-bold">
                        {cat.children?.length}
                      </span>
                    )}
                  </div>

                  {hasChildren && isExpanded && (
                    <div className="pl-4 ml-2 border-l border-slate-900 space-y-1 mt-0.5 py-0.5">
                      {cat.children?.map((child) => (
                        <div
                          key={child.id}
                          onClick={() => setSelectedTreeId(child.id)}
                          className={`flex items-center gap-2 px-2 py-1 rounded text-xs font-mono cursor-pointer transition ${
                            selectedTreeId === child.id
                              ? "bg-slate-800 text-slate-100 border border-slate-700/60 shadow"
                              : "text-slate-400 hover:bg-slate-900/60 hover:text-slate-300"
                          }`}
                        >
                          <span className="text-slate-600">•</span>
                          <span className="truncate text-[11px]">{child.label}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {fileInfo && (
            <div className="p-3 bg-[#050910] border-t border-slate-900 text-[10px] font-mono text-slate-500 space-y-1">
              <div className="flex justify-between">
                <span>File:</span>
                <span className="text-slate-300 truncate w-40 text-right">{fileInfo.filename}</span>
              </div>
              <div className="flex justify-between">
                <span>Signature:</span>
                <span className="text-slate-300">
                  {fileInfo.signature} v{fileInfo.version}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Stage:</span>
                <span className="text-slate-300">
                  {fileInfo.width}×{fileInfo.height}px @ {fileInfo.frame_rate}fps
                </span>
              </div>
            </div>
          )}
        </aside>

        {/* Main viewport */}
        <main className="flex-1 bg-[#0b0f19]/30 p-6 overflow-y-auto flex flex-col min-h-0">
          {selectedTreeId === "header" && fileInfo && (
            <div className="space-y-6">
              <div className="bg-gradient-to-r from-[#0d1626] to-[#0a0f18] border border-slate-800/80 rounded-2xl p-6 shadow-xl">
                <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                  <FileSignature className="w-5 h-5 text-emerald-400" />
                  {fileInfo.filename}
                </h2>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Parsed by the Python backend (py_swf). Select any tag on the left to preview or edit it.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                  <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 font-bold mb-1.5">
                    Frame rate
                  </span>
                  <h3 className="text-3xl font-bold text-white">
                    {fileInfo.frame_rate} <span className="text-xs uppercase text-slate-400 font-medium">fps</span>
                  </h3>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                  <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 font-bold mb-1.5">
                    Stage size
                  </span>
                  <h3 className="text-2xl font-bold text-white">
                    {fileInfo.width} × {fileInfo.height} <span className="text-xs uppercase text-slate-400 font-medium">px</span>
                  </h3>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                  <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 font-bold mb-1.5">
                    Timeline
                  </span>
                  <h3 className="text-3xl font-bold text-white">
                    {fileInfo.frame_count} <span className="text-xs uppercase text-slate-400 font-medium">frames</span>
                  </h3>
                </div>
              </div>

              <StageViewer sid={sid} onError={setErrorText} />

              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-md">
                <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800 flex justify-between items-center">
                  <span className="text-xs font-mono font-bold text-slate-300">Tag stream</span>
                  <span className="text-[10px] bg-slate-900 px-2 py-0.5 rounded text-emerald-400 font-mono font-medium">
                    {tags.length} tags
                  </span>
                </div>
                <div className="max-h-[300px] overflow-y-auto text-xs font-mono">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-950/40 text-slate-500 border-b border-slate-900">
                        <th className="p-2.5 pl-4">#</th>
                        <th className="p-2.5">CODE</th>
                        <th className="p-2.5">NAME</th>
                        <th className="p-2.5">CHAR ID</th>
                        <th className="p-2.5 pr-4 text-right">SIZE</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900/50">
                      {tags.map((tag) => (
                        <tr
                          key={tag.index}
                          onClick={() => setSelectedTreeId(`tag-${tag.index}`)}
                          className="hover:bg-slate-800/40 cursor-pointer text-[11px] text-slate-300 transition"
                        >
                          <td className="p-2.5 pl-4 text-slate-500">{tag.index}</td>
                          <td className="p-2.5 text-blue-400 font-medium">{tag.code}</td>
                          <td className="p-2.5 font-sans font-semibold text-white">
                            {tag.name}
                            {tag.parse_error && (
                              <span className="ml-2 text-[9px] text-red-400">⚠ {tag.parse_error}</span>
                            )}
                          </td>
                          <td className="p-2.5 text-slate-400">{tag.char_id ?? "—"}</td>
                          <td className="p-2.5 pr-4 text-right text-emerald-400 font-semibold">{tag.size} B</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {!selectedTag && selectedTreeId !== "header" && fileInfo && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-900/20 border border-dashed border-slate-800 rounded-xl">
              <FolderOpen className="w-12 h-12 text-slate-700 mb-3" />
              <h3 className="text-base font-bold text-slate-300 capitalize">{selectedTreeId}</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1 leading-relaxed">
                Select an individual tag under this folder to inspect it.
              </p>
            </div>
          )}

          {selectedTag && fileInfo && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs uppercase text-slate-400 tracking-wider font-bold">
                    Tag #{selectedTag.index} — {selectedTag.name}
                  </span>
                  <span className="h-4 w-px bg-slate-800" />
                  <span className="text-[11px] font-mono text-slate-500">{selectedTag.size} bytes</span>
                </div>
                <div className="flex bg-slate-950 p-1 border border-slate-800 rounded-lg">
                  <button
                    onClick={() => setActiveTab("preview")}
                    className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                      activeTab === "preview" ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Preview
                  </button>
                  <button
                    onClick={() => setActiveTab("hex")}
                    className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                      activeTab === "hex" ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Hex
                  </button>
                </div>
              </div>

              {activeTab === "hex" ? (
                <HexPanel
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  onChanged={markDirty}
                  onError={setErrorText}
                />
              ) : SHAPE_TAGS.includes(selectedTag.code) || MORPH_TAGS.includes(selectedTag.code) ? (
                <ShapeViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  charId={selectedTag.char_id}
                  isMorph={MORPH_TAGS.includes(selectedTag.code)}
                  onError={setErrorText}
                />
              ) : selectedTag.code === 39 ? (
                <SpriteViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  onError={setErrorText}
                />
              ) : IMAGE_TAGS.includes(selectedTag.code) ? (
                <ImageViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  charId={selectedTag.char_id}
                  onChanged={markDirty}
                  onError={setErrorText}
                />
              ) : SCRIPT_TAGS.includes(selectedTag.code) ? (
                <ScriptViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  onChanged={markDirty}
                  onError={setErrorText}
                />
              ) : selectedTag.code === 14 ? (
                <SoundViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  charId={selectedTag.char_id}
                  onError={setErrorText}
                />
              ) : FONT_TAGS.includes(selectedTag.code) ? (
                <FontViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  onError={setErrorText}
                />
              ) : TEXT_TAGS.includes(selectedTag.code) ? (
                <TextViewer
                  sid={sid}
                  tagIndex={selectedTag.index}
                  tagName={selectedTag.name}
                  tagCode={selectedTag.code}
                  onError={setErrorText}
                />
              ) : (
                <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-3 shadow-xl text-xs font-mono">
                  <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-500">Tag code:</span>
                    <span className="text-slate-200">{selectedTag.code}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-500">Payload size:</span>
                    <span className="text-purple-400 font-bold">{selectedTag.size} bytes</span>
                  </div>
                  {selectedTag.char_id != null && (
                    <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                      <span className="text-slate-500">Character id:</span>
                      <span className="text-slate-200">{selectedTag.char_id}</span>
                    </div>
                  )}
                  <p className="text-slate-500 pt-2 leading-relaxed">
                    No dedicated viewer for this tag type yet — use the Hex tab to inspect and edit
                    its raw bytes.
                  </p>
                </div>
              )}
            </div>
          )}

          {!fileInfo && (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Layers className="w-16 h-16 text-slate-800 mb-4" />
              <h2 className="text-lg font-bold text-slate-400">No SWF loaded</h2>
              <p className="text-xs text-slate-600 mt-1">Use “Open SWF” above to upload a file.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
