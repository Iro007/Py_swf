import React, { useState, useEffect } from "react";
import { 
  Folder, FolderOpen, FileCode, Binary, Music, Code2, 
  Settings, AlertCircle, Upload, Check, Play, Info, 
  FileSignature, Table, Save, RefreshCw, Sparkles, Image, 
  FileText, PlayCircle, Star, Database, ArrowRight, Layers, HelpCircle
} from "lucide-react";

import { SWFFile, SWFTag, TreeItem, SWFCategory } from "./types";
import { parseSWF, rebuildAndSaveSWF } from "./utils/swfParser";
import { SAMPLE_SWFS, createSWFFileFromSample, SampleSWF } from "./utils/sampleFiles";

import ShapeViewer from "./components/ShapeViewer";
import ImageViewer from "./components/ImageViewer";
import SoundViewer from "./components/SoundViewer";
import ScriptViewer from "./components/ScriptViewer";
import HexEditor from "./components/HexEditor";

export default function App() {
  const [activeSampleIndex, setActiveSampleIndex] = useState<number>(0);
  const [swfFile, setSwfFile] = useState<SWFFile | null>(null);
  const [selectedTreeId, setSelectedTreeId] = useState<string>("header");
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    header: true,
    shapes: true,
    images: false,
    sounds: false,
    texts: false,
    scripts: true,
    sprites: false,
    frames: false,
    others: false
  });

  const [activeTab, setActiveTab] = useState<"preview" | "hex">("preview");
  const [errorText, setErrorText] = useState<string | null>(null);
  const [serverResponse, setServerResponse] = useState<any | null>(null);

  // Load default sample on mount
  useEffect(() => {
    loadSample(SAMPLE_SWFS[0], 0);
  }, []);

  const loadSample = (sample: SampleSWF, index: number) => {
    try {
      const parsed = createSWFFileFromSample(sample);
      setSwfFile(parsed);
      setActiveSampleIndex(index);
      setSelectedTreeId("header");
      setErrorText(null);
    } catch (e: any) {
      setErrorText(`Failed to generate mock sample: ${e.message}`);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const buffer = e.target?.result as ArrayBuffer;
        const parsed = parseSWF(buffer, file.name);
        setSwfFile(parsed);
        setSelectedTreeId("header");
        setErrorText(null);
      } catch (err: any) {
        setErrorText(`SWF Parsing failed: ${err.message}`);
      }
    };
    reader.readAsArrayBuffer(file);
  };

  const handleServerParse = (file: File) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const arrayBuf = e.target?.result as ArrayBuffer;
        const bytes = new Uint8Array(arrayBuf);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const b64 = btoa(binary);
        const resp = await fetch('/api/parse-swf', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: file.name, b64 })
        });
        const data = await resp.json();
        if (!resp.ok) {
          setErrorText(`Server parse failed: ${data.error || resp.statusText}`);
          setServerResponse(null);
          return;
        }
        setServerResponse(data);
        setErrorText(null);
      } catch (err: any) {
        setErrorText(`Server parse error: ${err.message}`);
        setServerResponse(null);
      }
    };
    reader.readAsArrayBuffer(file);
  };

  // Trigger rebuild and download of SWF binary file
  const handleDownloadSWF = () => {
    if (!swfFile) return;
    try {
      const blob = rebuildAndSaveSWF(swfFile);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = swfFile.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err: any) {
      setErrorText(`Failed to rebuild SWF: ${err.message}`);
    }
  };

  // Update shape payload values
  const handleUpdateShape = (shapeId: number, fill: string, stroke: string, strokeWidth: number) => {
    if (!swfFile) return;
    const updatedTags = swfFile.tags.map(tag => {
      if ((tag.type === 2 || tag.type === 22 || tag.type === 32 || tag.type === 83) && tag.id === shapeId) {
        return {
          ...tag,
          properties: {
            ...tag.properties,
            fillStyle: fill,
            strokeStyle: stroke,
            lineWidth: strokeWidth
          }
        };
      }
      return tag;
    });

    setSwfFile({
      ...swfFile,
      tags: updatedTags
    });
  };

  // Update Hex bytes payload values
  const handleUpdateHexBytes = (tagIndex: number, updatedBytes: Uint8Array) => {
    if (!swfFile) return;
    const updatedTags = [...swfFile.tags];
    updatedTags[tagIndex] = {
      ...updatedTags[tagIndex],
      content: updatedBytes,
      length: updatedBytes.length
    };

    setSwfFile({
      ...swfFile,
      tags: updatedTags
    });
  };

  // Update high-level ActionScript codes
  const handleUpdateScriptCode = (scriptId: number, updatedCode: string) => {
    if (!swfFile) return;
    const updatedTags = swfFile.tags.map(tag => {
      if ((tag.type === 82 || tag.type === 12) && tag.id === scriptId) {
        return {
          ...tag,
          properties: {
            ...tag.properties,
            decompiledAS: updatedCode
          }
        };
      }
      return tag;
    });

    setSwfFile({
      ...swfFile,
      tags: updatedTags
    });
  };

  // Expand / collapse tree folders
  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => ({
      ...prev,
      [nodeId]: !prev[nodeId]
    }));
  };

  // Map category code to tree view lists
  const resolveTreeStructure = (): TreeItem[] => {
    if (!swfFile) return [];

    const categories: Record<SWFCategory, TreeItem> = {
      header: { id: "header", label: "SWF File Header", type: "header", iconName: "header" },
      shapes: { id: "shapes", label: "Shapes / Vectors", type: "shapes", iconName: "shapes", children: [] },
      images: { id: "images", label: "Images / Bitmaps", type: "images", iconName: "images", children: [] },
      sounds: { id: "sounds", label: "Sounds / Audio Blocks", type: "sounds", iconName: "sounds", children: [] },
      texts: { id: "texts", label: "Texts / Outlines", type: "texts", iconName: "texts", children: [] },
      buttons: { id: "buttons", label: "Buttons / Triggers", type: "buttons", iconName: "buttons", children: [] },
      sprites: { id: "sprites", label: "Sprites / MovieClips", type: "sprites", iconName: "sprites", children: [] },
      scripts: { id: "scripts", label: "Scripts / ActionScript", type: "scripts", iconName: "scripts", children: [] },
      frames: { id: "frames", label: "Frames / Timeline", type: "frames", iconName: "frames", children: [] },
      others: { id: "others", label: "Other Tags / Metadata", type: "others", iconName: "others", children: [] }
    };

    swfFile.tags.forEach((tag, idx) => {
      const type = tag.type;
      const tNode: TreeItem = {
        id: `tag-${idx}`,
        label: tag.name,
        type: "tag-node",
        iconName: "tag",
        tagIndex: idx,
        tagType: type
      };

      if (type === 2 || type === 22 || type === 32 || type === 83) {
        categories.shapes.children?.push(tNode);
      } else if (type === 6 || type === 20 || type === 21 || type === 35 || type === 36 || type === 90) {
        categories.images.children?.push(tNode);
      } else if (type === 14) {
        categories.sounds.children?.push(tNode);
      } else if (type === 11 || type === 33 || type === 37) {
        categories.texts.children?.push(tNode);
      } else if (type === 7 || type === 34) {
        categories.buttons.children?.push(tNode);
      } else if (type === 39) {
        categories.sprites.children?.push(tNode);
      } else if (type === 12 || type === 82 || type === 59) {
        categories.scripts.children?.push(tNode);
      } else if (type === 1 || type === 43 || type === 5 || type === 28) {
        categories.frames.children?.push(tNode);
      } else {
        categories.others.children?.push(tNode);
      }
    });

    return Object.values(categories);
  };

  const treeStructure = resolveTreeStructure();

  // Find currently selected element contents
  const getSelectedTag = (): { tag: SWFTag; idx: number } | null => {
    if (!swfFile || !selectedTreeId.startsWith("tag-")) return null;
    const idx = parseInt(selectedTreeId.replace("tag-", ""), 10);
    if (isNaN(idx) || idx >= swfFile.tags.length) return null;
    return { tag: swfFile.tags[idx], idx };
  };

  const selectedPayload = getSelectedTag();

  return (
    <div id="pysw-app-root" className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none antialiased">
      {/* Top Navbar */}
      <header className="bg-[#0b0f19] border-b border-slate-800/80 px-6 py-3 shrink-0 flex flex-wrap items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-emerald-600 to-teal-500 rounded-xl shadow-md flex items-center justify-center">
            <Layers className="w-5 h-5 text-slate-950 font-black animate-pulse" />
          </div>
          <div>
            <h1 className="text-base font-bold font-sans tracking-tight text-white flex items-center gap-1.5">
              PySW Web SWF Decompiler & Editor
              <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-extrabold border border-emerald-500/20">
                PRO v3.5
              </span>
            </h1>
            <p className="text-[10px] text-slate-400 font-mono">Flash Decompression, Reassembly & Bytecode Assist Engine</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {/* Quick select samples widgets */}
          <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-1">
            <span className="text-[10px] uppercase font-mono text-slate-500 font-bold">Samples:</span>
            <div className="flex gap-1">
              {SAMPLE_SWFS.map((s, idx) => (
                <button
                  key={s.filename}
                  onClick={() => loadSample(s, idx)}
                  className={`text-[10px] font-medium px-2 py-0.5 rounded transition ${
                    activeSampleIndex === idx 
                      ? "bg-slate-800 text-emerald-400 border border-emerald-500/20 shadow-sm"
                      : "text-slate-400 hover:bg-slate-850 hover:text-slate-200"
                  }`}
                  title={s.description}
                >
                  {s.displayName.split(" ")[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Upload and downloads */}
          <label className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-850 text-slate-350 cursor-pointer border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition active:scale-95 shadow">
            <Upload className="w-3.5 h-3.5 text-blue-400" />
            <span>Upload SWF</span>
            <input type="file" accept=".swf" onChange={handleFileUpload} className="hidden" />
          </label>

          <label className="flex items-center gap-1.5 bg-slate-900 hover:bg-slate-850 text-slate-350 cursor-pointer border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition active:scale-95 shadow">
            <Upload className="w-3.5 h-3.5 text-emerald-400" />
            <span>Parse on Server</span>
            <input type="file" accept=".swf" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleServerParse(f); }} className="hidden" />
          </label>

          <button
            onClick={handleDownloadSWF}
            disabled={!swfFile}
            className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-600 active:scale-95 text-slate-950 font-bold px-3 py-1.5 rounded-lg text-xs transition shadow-md shadow-emerald-950/20 disabled:opacity-40 disabled:pointer-events-none"
          >
            <Save className="w-3.5 h-3.5 fill-slate-950" />
            <span>Reassemble & Save SWF</span>
          </button>
        </div>
      </header>

      {/* Error notification banner if any */}
      {errorText && (
        <div className="bg-red-500/15 border-b border-red-500/20 px-6 py-2 flex items-center gap-3 text-red-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 animate-bounce" />
          <span>{errorText}</span>
          <button onClick={() => setErrorText(null)} className="ml-auto text-[10px] uppercase text-red-500 font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Workspace Area: Left Tree sidebar + Central viewport */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Side Navigation Tree Directory */}
        <aside className="w-80 bg-[#080d16] border-r border-slate-900 flex flex-col shrink-0 min-h-0">
          <div className="p-3 bg-slate-950/60 border-b border-slate-900 flex justify-between items-center text-xs text-slate-400 font-mono">
            <span className="font-bold">SWF LOGICAL DIRECTORY</span>
            <span className="text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-slate-500 font-medium">
              ASCII/AVM Tree
            </span>
          </div>

          <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
            {treeStructure.map((cat) => {
              const matches = selectedTreeId === cat.id;
              const hasChildren = cat.children && cat.children.length > 0;
              const isExpanded = expandedNodes[cat.id];

              return (
                <div key={cat.id} className="space-y-0.5">
                  {/* Category Directory Row */}
                  <div
                    onClick={() => {
                      if (hasChildren) {
                        toggleNode(cat.id);
                        setSelectedTreeId(cat.id);
                      } else {
                        setSelectedTreeId(cat.id);
                      }
                    }}
                    className={`flex items-center justify-between px-2 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition ${
                      matches
                        ? "bg-slate-800/40 text-emerald-400 border border-emerald-500/10 shadow-sm"
                        : "text-slate-350 hover:bg-slate-900"
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

                  {/* Children tag list nodes */}
                  {hasChildren && isExpanded && (
                    <div className="pl-4 ml-2 border-l border-slate-900 space-y-1 mt-0.5 py-0.5">
                      {cat.children?.map((child) => {
                        const isChildSelected = selectedTreeId === child.id;
                        return (
                          <div
                            key={child.id}
                            onClick={() => setSelectedTreeId(child.id)}
                            className={`flex items-center gap-2 px-2 py-1 rounded text-xs font-mono cursor-pointer transition ${
                              isChildSelected
                                ? "bg-slate-800 text-slate-100 border border-slate-700/60 shadow"
                                : "text-slate-450 hover:bg-slate-900/60 hover:text-slate-300"
                            }`}
                          >
                            <span className="text-slate-600">•</span>
                            <span className="truncate text-[11px]">{child.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Quick specs footnote info */}
          {swfFile && (
            <div className="p-3 bg-[#050910] border-t border-slate-900 text-[10px] font-mono text-slate-500 space-y-1">
              <div className="flex justify-between">
                <span>SWF Name:</span>
                <span className="text-slate-300 truncate w-32 text-right">{swfFile.filename}</span>
              </div>
              <div className="flex justify-between">
                <span>Signature:</span>
                <span className={`${swfFile.header.signature === 'CWS' ? 'text-blue-400' : 'text-slate-300'}`}>
                  {swfFile.header.signature} (Compressed)
                </span>
              </div>
              <div className="flex justify-between">
                <span>File Size:</span>
                <span className="text-slate-300">{(swfFile.header.fileLength / 1024).toFixed(1)} KB</span>
              </div>
            </div>
          )}
        </aside>

        {/* Central Display Playground Viewport */}
        <main className="flex-1 bg-[#0b0f19]/30 p-6 overflow-y-auto flex flex-col min-h-0">
          {/* Header specification view */}
          {selectedTreeId === "header" && swfFile && (
            <div className="space-y-6">
              {/* Intro Jumbotron Cards */}
              <div className="relative bg-gradient-to-r from-[#0d1626] to-[#0a0f18] border border-slate-800/80 rounded-2xl p-6 overflow-hidden shadow-xl">
                <div className="absolute top-0 right-0 transform translate-x-20 -translate-y-20 p-24 bg-emerald-500/5 rounded-full filter blur-3xl" />
                <h2 className="text-lg font-bold text-white mb-2 font-sans flex items-center gap-2">
                  <FileSignature className="w-5 h-5 text-emerald-400 animate-bounce" />
                  Flash SWF Container Specifications
                </h2>
                <p className="text-xs text-slate-400 leading-relaxed max-w-3xl">
                  Inspect general file details below. This structure was decoded using real-time binary stream processors.
                </p>
              </div>

              {/* Grid Specifications parameters */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 font-bold mb-1.5">
                      Framerates & Stages
                    </span>
                    <h3 className="text-3xl font-bold text-white tracking-tight">{swfFile.header.frameRate} <span className="text-xs uppercase text-slate-400 font-medium">FPS</span></h3>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-3 border-t border-slate-900 pt-2 leading-relaxed">
                    Movie timeline pacing settings. Native playback speed for tweens, animations and enter_frames.
                  </p>
                </div>

                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 font-bold mb-1.5">
                      Stage Canvas Size
                    </span>
                    <h3 className="text-2xl font-bold text-white tracking-tight">
                      {swfFile.header.frameSize.width} x {swfFile.header.frameSize.height} <span className="text-xs uppercase text-slate-400 font-medium">px</span>
                    </h3>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-3 border-t border-slate-900 pt-2 leading-relaxed font-mono">
                    Bounding Box RECT: {swfFile.header.frameSize.xMin} to {swfFile.header.frameSize.xMax} twips width.
                  </p>
                </div>

                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-500 font-bold mb-1.5">
                      Timeline Frames length
                    </span>
                    <h3 className="text-3xl font-bold text-white tracking-tight">{swfFile.header.frameCount} <span className="text-xs uppercase text-slate-400 font-medium">Frames</span></h3>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-3 border-t border-slate-900 pt-2 leading-relaxed">
                    Total count of timeline frame nodes. Total running length: ~{(swfFile.header.frameCount / swfFile.header.frameRate).toFixed(1)}s.
                  </p>
                </div>
              </div>

              {/* Structural Tag Stream Metrics */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-md">
                <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800 flex justify-between items-center">
                  <span className="text-xs font-mono font-bold text-slate-300">SWF Structural Tags Stream Table</span>
                  <span className="text-[10px] bg-slate-900 px-2 py-0.5 rounded text-emerald-400 font-mono font-medium">
                    {swfFile.tags.length} parsed items
                  </span>
                </div>
                <div className="max-h-[220px] overflow-y-auto text-xs font-mono">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-950/40 text-slate-500 border-b border-slate-900">
                        <th className="p-2.5 pl-4">INDEX</th>
                        <th className="p-2.5">TAG TYPE</th>
                        <th className="p-2.5">TAG NAME</th>
                        <th className="p-2.5">OFFSET</th>
                        <th className="p-2.5 pr-4 text-right">LENGTH</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900/50">
                      {swfFile.tags.map((tag, idx) => (
                        <tr 
                          key={idx} 
                          onClick={() => setSelectedTreeId(`tag-${idx}`)}
                          className="hover:bg-slate-850/40 cursor-pointer text-[11px] text-slate-300 transition duration-100"
                        >
                          <td className="p-2.5 pl-4 text-slate-500">#{idx + 1}</td>
                          <td className="p-2.5 text-blue-400 font-medium">{tag.type}</td>
                          <td className="p-2.5 font-sans font-semibold text-white">{tag.typeName}</td>
                          <td className="p-2.5 text-slate-400">0x{tag.offset.toString(16).toUpperCase()}</td>
                          <td className="p-2.5 pr-4 text-right text-emerald-400 font-semibold">{tag.length} bytes</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Fallbacks if general folders are selected */}
          {swfFile && (
            selectedTreeId === "shapes" ||
            selectedTreeId === "images" ||
            selectedTreeId === "sounds" ||
            selectedTreeId === "texts" ||
            selectedTreeId === "buttons" ||
            selectedTreeId === "sprites" ||
            selectedTreeId === "scripts" ||
            selectedTreeId === "frames" ||
            selectedTreeId === "others"
          ) && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-900/20 border border-dashed border-slate-800 rounded-xl">
              <FolderOpen className="w-12 h-12 text-slate-650 mb-3 animate-pulse" />
              <h3 className="text-base font-bold text-slate-300 font-sans capitalize">{selectedTreeId} Folder selected</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1 leading-relaxed">
                Click any nested sub-nodes or individual character IDs underneath this folder in the left hand SWF Logical Directory block to inspect resource details.
              </p>
            </div>
          )}

          {/* Specific Tag element previews */}
          {selectedPayload && swfFile && (
            <div className="space-y-6">
              {/* Main Subtab toggle headers */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs uppercase text-slate-400 tracking-wider font-bold">
                    TAG SPECIFICS PREVIEW
                  </span>
                  <span className="h-4 w-px bg-slate-800" />
                  <span className="text-[11px] font-mono text-slate-500">
                    File Offset: 0x{selectedPayload.tag.offset.toString(16).toUpperCase()}
                  </span>
                </div>

                {/* Tab select trigger preview/hex */}
                <div className="flex bg-slate-950 p-1 border border-slate-850 rounded-lg">
                  <button
                    onClick={() => setActiveTab("preview")}
                    className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                      activeTab === "preview" ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Visual Preview
                  </button>
                  <button
                    onClick={() => setActiveTab("hex")}
                    className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                      activeTab === "hex" ? "bg-slate-800 text-white shadow" : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Hex Raw Dump
                  </button>
                </div>
              </div>

              {/* Rendering depending on Active Tab and Type */}
              {activeTab === "preview" ? (
                <div>
                  {/* SHAPES */}
                  {(selectedPayload.tag.type === 2 || 
                    selectedPayload.tag.type === 22 || 
                    selectedPayload.tag.type === 32 || 
                    selectedPayload.tag.type === 83) ? (
                    (() => {
                      const shapeId = selectedPayload.tag.id || 101;
                      const sampleShape = SAMPLE_SWFS[activeSampleIndex]?.vectorShapes.find(s => s.id === shapeId);
                      
                      const paths = selectedPayload.tag.properties?.paths || sampleShape?.paths || [];
                      const width = selectedPayload.tag.properties?.width || sampleShape?.width || 200;
                      const height = selectedPayload.tag.properties?.height || sampleShape?.height || 200;
                      const finalFill = selectedPayload.tag.properties?.fillStyle || sampleShape?.fillStyle || "#e74c3c";
                      const finalStroke = selectedPayload.tag.properties?.strokeStyle || sampleShape?.strokeStyle || "#1a1a1a";
                      const finalWidth = selectedPayload.tag.properties?.lineWidth !== undefined ? selectedPayload.tag.properties.lineWidth : (sampleShape?.lineWidth || 1.5);

                      return (
                        <ShapeViewer
                          id={shapeId}
                          width={width}
                          height={height}
                          paths={paths}
                          fillStyle={finalFill}
                          strokeStyle={finalStroke}
                          lineWidth={finalWidth}
                          onUpdateShape={handleUpdateShape}
                        />
                      );
                    })()
                  ) : 

                  /* IMAGES */
                  (selectedPayload.tag.type === 6 || 
                   selectedPayload.tag.type === 20 || 
                   selectedPayload.tag.type === 21 || 
                   selectedPayload.tag.type === 35 || 
                   selectedPayload.tag.type === 36 || 
                   selectedPayload.tag.type === 90) ? (
                    (() => {
                      const imgId = selectedPayload.tag.id || 201;
                      const sampleImg = SAMPLE_SWFS[activeSampleIndex]?.images.find(img => img.id === imgId);
                      
                      const name = selectedPayload.tag.properties?.name || sampleImg?.name || `image_${imgId}.png`;
                      const width = selectedPayload.tag.properties?.width || sampleImg?.width || 100;
                      const height = selectedPayload.tag.properties?.height || sampleImg?.height || 100;
                      const color = selectedPayload.tag.properties?.color || sampleImg?.color || "#3b82f6";
                      const type = selectedPayload.tag.properties?.type || sampleImg?.type || "PNG";
                      const caption = selectedPayload.tag.properties?.caption || sampleImg?.caption || "Standard asset placeholder.";
                      const dataUrl = selectedPayload.tag.properties?.dataUrl || null;

                      return (
                        <ImageViewer
                          id={imgId}
                          name={name}
                          width={width}
                          height={height}
                          color={color}
                          type={type as any}
                          caption={caption}
                          dataUrl={dataUrl}
                        />
                      );
                    })()
                  ) :

                  /* SOUNDS */
                  (selectedPayload.tag.type === 14) ? (
                    (() => {
                      const soundId = selectedPayload.tag.id || 301;
                      const sampleSnd = SAMPLE_SWFS[activeSampleIndex]?.sounds.find(snd => snd.id === soundId);

                      const name = selectedPayload.tag.properties?.name || sampleSnd?.name || `sound_${soundId}.wav`;
                      const duration = selectedPayload.tag.properties?.duration || sampleSnd?.duration || 1.5;
                      const frequency = selectedPayload.tag.properties?.frequency || sampleSnd?.frequency || 440;
                      const type = selectedPayload.tag.properties?.type || sampleSnd?.type || "WAV";
                      const waveType = selectedPayload.tag.properties?.waveType || sampleSnd?.waveType || "sine";
                      const caption = selectedPayload.tag.properties?.caption || sampleSnd?.caption || "Standard synth baseline play sound.";

                      return (
                        <SoundViewer
                          id={soundId}
                          name={name}
                          duration={duration}
                          frequency={frequency}
                          type={type as any}
                          waveType={waveType as any}
                          caption={caption}
                        />
                      );
                    })()
                  ) :

                  /* ACTION SCRIPTS / ABC CLASS */
                  (selectedPayload.tag.type === 12 || selectedPayload.tag.type === 82) ? (
                    (() => {
                      const sName = selectedPayload.tag.properties?.abcName || "com.game.PlayerController";
                      const sampleScript = SAMPLE_SWFS[activeSampleIndex]?.scripts.find(s => s.name === sName);
                      
                      const codeFinal = selectedPayload.tag.properties?.decompiledAS || sampleScript?.decompiledAS || "// ActionScript source placeholder";
                      const bytecodeFinal = selectedPayload.tag.disassembly || sampleScript?.bytecode || "";
                      const idVal = sampleScript?.id || selectedPayload.tag.id || 99;

                      return (
                        <ScriptViewer
                          id={idVal}
                          name={sName}
                          tagType={selectedPayload.tag.type === 82 ? "DoABC" : "DoAction"}
                          bytecode={bytecodeFinal}
                          decompiledAS={codeFinal}
                        abcB64={selectedPayload.tag.properties?.abcB64}
                        onUpdateScript={handleUpdateScriptCode}
                      />
                      );
                    })()
                  ) :

                  /* UNPACKED / DEFAULT RAW PREVIEW TABLE */
                  (
                    <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-4 shadow-xl">
                      <div className="flex gap-2 p-2.5 bg-slate-950/40 rounded border border-slate-800/60 items-center justify-between">
                        <div className="text-slate-300 font-sans text-xs">
                          TypeName: <strong className="text-white">{selectedPayload.tag.typeName}</strong> (Code: {selectedPayload.tag.type})
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">Raw Tag Header details</span>
                      </div>

                      <div className="space-y-2">
                        <span className="block text-[10px] uppercase font-mono text-slate-400 font-bold tracking-wider">
                          Parsed Properties List
                        </span>
                        
                        <div className="bg-slate-950 border border-slate-850 p-4 rounded-lg font-mono text-xs text-slate-200 divide-y divide-slate-900">
                          <div className="flex justify-between py-2">
                            <span className="text-slate-500">Tag Code Number:</span>
                            <span>{selectedPayload.tag.type}</span>
                          </div>
                          <div className="flex justify-between py-2">
                            <span className="text-slate-500">Offset location address:</span>
                            <span>0x{selectedPayload.tag.offset.toString(16).toUpperCase()}</span>
                          </div>
                          <div className="flex justify-between py-2">
                            <span className="text-slate-500">Payload length (body):</span>
                            <span className="text-purple-400 font-bold">{selectedPayload.tag.length} bytes</span>
                          </div>
                          {Object.entries(selectedPayload.tag.properties || {}).map(([key, val]) => (
                            <div key={key} className="flex justify-between py-2">
                              <span className="text-slate-500 lowercase first-letter:uppercase">{key}:</span>
                              <span className="text-emerald-400 truncate max-w-sm">
                                {typeof val === "object" ? JSON.stringify(val) : String(val)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Display warning details */}
                      <div className="p-3 bg-slate-950/60 border border-slate-850 rounded-lg text-[11px] text-slate-400 flex items-start gap-2 leading-relaxed">
                        <Info className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <p>
                          This tag serves as configuration metadata container inside the SWF file. Toggle <span className="text-white font-semibold">Hex Raw Dump</span> in the subtab controls above to view and customize raw byte definitions directly.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* HEX RAW MODE INSPECTOR PANEL */
                <HexEditor
                  tagIndex={selectedPayload.idx}
                  tagName={selectedPayload.tag.typeName}
                  bytes={selectedPayload.tag.content}
                  onUpdateHex={handleUpdateHexBytes}
                />
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
