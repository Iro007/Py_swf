import React, { useState, useEffect } from "react";
import { Play, Sparkles, Code2, Cpu, FileCode, Check, Send, RotateCw, RefreshCw, AlertCircle, Download } from "lucide-react";

interface ScriptViewerProps {
  id: number;
  name: string;
  tagType: "DoABC" | "DoAction";
  bytecode: string;
  decompiledAS: string;
  abcB64?: string;
  onUpdateScript?: (scriptId: number, updatedCode: string) => void;
}

export default function ScriptViewer({
  id,
  name,
  tagType,
  bytecode,
  decompiledAS,
  abcB64,
  onUpdateScript
}: ScriptViewerProps) {
  const [activeTab, setActiveTab] = useState<"as" | "abc" | "ai">("as");
  const [editableCode, setEditableCode] = useState<string>(decompiledAS);
  const [isSaved, setIsSaved] = useState<boolean>(false);
  const [promptMessage, setPromptMessage] = useState<string>("");
  const [aiResult, setAiResult] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setEditableCode(decompiledAS);
    setAiResult("");
    setErrorMessage(null);
  }, [decompiledAS]);

  // Syntax highlighting helper for ActionScript 3.0
  const highlightAS = (code: string) => {
    if (!code) return "";
    
    // Simple regex replacements for highlighting
    const escape = (text: string) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    let safe = escape(code);

    // Comments
    safe = safe.replace(/(\/\/.*)/g, '<span class="text-slate-500 font-sans italic">$1</span>');
    safe = safe.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="text-slate-500 font-sans italic">$1</span>');

    // Keywords
    const keywords = [
      "package", "import", "class", "extends", "public", "private", "protected",
      "function", "var", "override", "void", "return", "new", "get", "set",
      "const", "switch", "case", "break", "default", "if", "else", "for", "while"
    ];
    keywords.forEach(kw => {
      const regex = new RegExp(`\\b(${kw})\\b`, "g");
      safe = safe.replace(regex, `<span class="text-orange-400 font-semibold">$1</span>`);
    });

    // Native Types
    const nativeTypes = ["Number", "Boolean", "int", "uint", "String", "Array", "Sprite", "Event", "KeyboardEvent", "Sound"];
    nativeTypes.forEach(t => {
      const regex = new RegExp(`\\b(${t})\\b`, "g");
      safe = safe.replace(regex, `<span class="text-blue-400">$1</span>`);
    });

    // Strings
    safe = safe.replace(/(".*?")/g, '<span class="text-emerald-400">$1</span>');
    safe = safe.replace(/('.*?')/g, '<span class="text-emerald-400">$1</span>');

    // Return element
    return <pre className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre" dangerouslySetInnerHTML={{ __html: safe }} />;
  };

  const handleApplyChanges = () => {
    setIsSaved(true);
    if (onUpdateScript) {
      onUpdateScript(id, editableCode);
    }
    setTimeout(() => {
      setIsSaved(false);
    }, 2000);
  };

  const callAIAction = async (taskType: "explain" | "decompile" | "modernize") => {
    setIsLoading(true);
    setErrorMessage(null);
    setAiResult("");
    setActiveTab("ai");

    try {
      const response = await fetch("/api/decompile-ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bytecode: bytecode,
          tagType: tagType,
          filename: name,
          context: editableCode,
          taskType: taskType
        })
      });

      if (!response.ok) {
        const errJson = await response.json();
        throw new Error(errJson.error || "Failed to contact Gemini server.");
      }

      const data = await response.json();
      setAiResult(data.result);
    } catch (err: any) {
      setErrorMessage(err.message || "An unexpected error occurred during AI decompilation.");
    } finally {
      setIsLoading(false);
    }
  };

  // Export AS ZIP from server with preview of ZIP contents
  const exportAsZip = async () => {
    if (!abcB64) {
      setErrorMessage("ABC payload not available for export.");
      return;
    }
    setIsLoading(true);
    try {
      const resp = await fetch('/api/decompile-abc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ b64: abcB64, zip: true })
      });
      if (!resp.ok) {
        const j = await resp.json();
        throw new Error(j.error || 'Failed to export ZIP');
      }
      const blob = await resp.blob();

      // Dynamically load JSZip from CDN to inspect contents without adding a build dependency
      const loadScript = (src: string) => new Promise<void>((resolve, reject) => {
        if ((window as any).JSZip) return resolve();
        const s = document.createElement('script');
        s.src = src;
        s.onload = () => resolve();
        s.onerror = () => reject(new Error('Failed to load JSZip'));
        document.head.appendChild(s);
      });

      try {
        await loadScript('https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js');
        const JSZip = (window as any).JSZip;
        const jszip = new JSZip();
        const zip = await jszip.loadAsync(blob);
        const names = Object.keys(zip.files);
        const listPreview = names.slice(0, 200).join('\n');
        const doDownload = window.confirm(`Archive contents:\n\n${listPreview}\n\nDownload archive?`);
        if (!doDownload) {
          setIsLoading(false);
          return;
        }
      } catch (e) {
        // If preview fails, fall back to direct download
        console.warn('ZIP preview failed, continuing to download', e);
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name || 'decompiled'}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setErrorMessage(err.message || 'Export failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Decompile server-side to text and show in AS tab
  const decompileServerText = async () => {
    if (!abcB64) {
      setErrorMessage('ABC payload not available');
      return;
    }
    setIsLoading(true);
    try {
      const resp = await fetch('/api/decompile-abc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ b64: abcB64 })
      });
      if (!resp.ok) {
        const j = await resp.json();
        throw new Error(j.error || 'Server decompile failed');
      }
      const data = await resp.json();
      // show result in AS tab
      setEditableCode(data.result || '');
      setActiveTab('as');
    } catch (err: any) {
      setErrorMessage(err.message || 'Server decompile failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id={`script-viewer-${id}`} className="bg-slate-900 border border-slate-700/60 rounded-xl overflow-hidden shadow-2xl transition duration-300 hover:border-slate-600/80 flex flex-col h-[525px]">
      {/* Script header */}
      <div className="flex items-center justify-between bg-slate-950/80 px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <FileCode className="w-4.5 h-4.5 text-orange-400 animate-pulse" />
          <div className="flex flex-col">
            <span className="font-sans text-sm text-slate-200 font-semibold">{name}</span>
            <span className="text-[10px] font-mono text-slate-500 font-medium">Decompiler Frame Tag ID {id} ({tagType})</span>
          </div>
        </div>

        {/* Action tags */}
        <div className="flex gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab("as")}
            className={`flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition ${
              activeTab === "as" ? "bg-orange-500/20 text-orange-400 font-bold border border-orange-500/30" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>ActionScript (.as)</span>
          </button>
          <button
            onClick={() => setActiveTab("abc")}
            className={`flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition ${
              activeTab === "abc" ? "bg-orange-500/20 text-orange-400 font-bold border border-orange-500/30" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>AVM Bytecode (.abc)</span>
          </button>
          <button
            onClick={() => setActiveTab("ai")}
            className={`flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition ${
              activeTab === "ai" ? "bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Gemini AI Wizard</span>
          </button>
        </div>
      </div>

      {/* Main Body content according to tab selection */}
      <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-4 min-h-0">
        {/* Left 3/4 content viewport */}
        <div className="col-span-3 p-4 bg-slate-950 flex flex-col h-full overflow-hidden">
          {activeTab === "as" && (
            <div className="flex-1 flex flex-col overflow-hidden gap-3.5">
              <div className="flex justify-between items-center bg-slate-900/60 p-2 border border-slate-850 rounded">
                <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-wider">
                  Source editor & syntax highlight mode
                </span>
                <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                  ● Editable
                </span>
              </div>
              
              {/* Split layout: Edit on top or side, high code renderer */}
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 overflow-hidden">
                {/* Editor textarea */}
                <div className="flex flex-col h-full">
                  <span className="text-[9px] text-slate-400 font-mono mb-1 font-semibold">EDIT INPUT</span>
                  <textarea
                    value={editableCode}
                    onChange={(e) => setEditableCode(e.target.value)}
                    className="flex-1 w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-orange-500 resize-none overflow-y-auto"
                    spellCheck="false"
                  />
                </div>

                {/* Styled highlight print */}
                <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-lg p-3 overflow-auto">
                  <span className="text-[9px] text-slate-500 font-mono mb-1 font-semibold">SYNTAX COLORED VIEW</span>
                  <div className="flex-1 overflow-auto">
                    {highlightAS(editableCode)}
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end pt-2 border-t border-slate-900 gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={decompileServerText}
                    disabled={isLoading}
                    className="bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-200 text-xs px-3 py-2 rounded-lg transition duration-150 flex items-center gap-2"
                  >
                    <Cpu className="w-4 h-4" />
                    <span>Decompile (server)</span>
                  </button>

                  <button
                    onClick={exportAsZip}
                    disabled={isLoading}
                    className="bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-slate-950 text-xs px-3 py-2 rounded-lg transition duration-150 flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export .AS ZIP</span>
                  </button>
                </div>

                <button
                  onClick={handleApplyChanges}
                  className="bg-orange-500 hover:bg-orange-600 active:scale-95 text-slate-950 font-bold text-xs px-4 py-2 rounded-lg transition duration-150 flex items-center gap-1.5 shadow"
                >
                  {isSaved ? <Check className="w-4 h-4" /> : <RotateCw className="w-4 h-4" />}
                  <span>{isSaved ? "Saved Script" : "Apply Script Changes"}</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === "abc" && (
            <div className="flex-1 flex flex-col overflow-hidden h-full">
              <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider font-semibold mb-2">
                ActionScript Virtual Machine (AVM) Registers Instructions
              </span>
              <div className="flex-1 bg-slate-900 border border-slate-850 rounded-lg p-3 overflow-y-auto font-mono text-slate-300 text-xs">
                <pre className="whitespace-pre leading-relaxed">{bytecode}</pre>
              </div>
            </div>
          )}

          {activeTab === "ai" && (
            <div className="flex-1 flex flex-col overflow-hidden h-full gap-3">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-mono text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                  Gemini-Powered Decompiler output
                </span>
                {isLoading && (
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-900/30">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>Gemini is compiling payload...</span>
                  </div>
                )}
              </div>

              {/* Display Result Box */}
              <div className="flex-1 bg-[#090d16] border border-slate-800/80 rounded-xl p-4 overflow-y-auto text-xs leading-relaxed font-sans text-slate-300">
                {isLoading ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 space-y-3">
                    <div className="p-3 bg-emerald-500/10 rounded-full animate-bounce">
                      <Sparkles className="w-7 h-7 text-emerald-400" />
                    </div>
                    <p className="font-mono text-xs">Querying Gemini model alias (gemini-3.5-flash)...</p>
                    <div className="w-32 h-1 bg-slate-800 rounded overflow-hidden">
                      <div className="h-full bg-emerald-400 rounded animate-loading-bar" style={{ width: "60%" }} />
                    </div>
                    <p className="text-[10px] text-slate-500 italic max-w-sm text-center">
                      Reconstructing packages, multiname structures, and method trait lists from byte assemblies...
                    </p>
                  </div>
                ) : errorMessage ? (
                  <div className="flex items-center gap-2.5 p-4 bg-red-900/10 border border-red-800/40 rounded-lg text-red-300">
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    <div className="text-xs">
                      <p className="font-bold">Gemini Decompile Error</p>
                      <p className="text-slate-400">{errorMessage}</p>
                      <p className="text-[10px] text-slate-500 mt-1">Please ensure your GEMINI_API_KEY is configured in the Secrets panel.</p>
                    </div>
                  </div>
                ) : aiResult ? (
                  <div className="whitespace-pre-line font-mono space-y-4">
                    {/* Render high level code cleanly */}
                    <div className="text-slate-300">
                      {aiResult}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center p-8">
                    <Sparkles className="w-8 h-8 text-slate-600 mb-2" />
                    <p className="text-sm font-semibold text-slate-400">Gemini Decompiler & Code Converter</p>
                    <p className="text-[11px] text-slate-500 max-w-sm mt-1">
                      Choose an AI action on the right side panel to decompile assemblies, analyze obfuscated bytecode, or convert legacy ActionScript directly to modern TypeScript Canvas code.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right 1/4 quick features panel of AI wizard controls */}
        <div className="bg-slate-900/60 p-4 shrink-0 flex flex-col border-t md:border-t-0 md:border-l border-slate-800 justify-between">
          <div className="space-y-4">
            <span className="block text-[10px] uppercase font-mono text-slate-400 font-bold tracking-wider mb-2">
              AI Command Actions
            </span>

            {/* action buttons */}
            <button
              onClick={() => callAIAction("decompile")}
              disabled={isLoading}
              className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-slate-950 text-xs font-bold py-2.5 px-3 rounded-lg transition text-left flex items-center gap-2 justify-start shadow-md"
            >
              <Sparkles className="w-4 h-4 flex-shrink-0" />
              <div className="flex flex-col text-left">
                <span className="leading-tight">AI Decompile to Source</span>
                <span className="text-[8px] opacity-75 font-normal">Reconstruct class tags</span>
              </div>
            </button>

            <button
              onClick={() => callAIAction("explain")}
              disabled={isLoading}
              className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs font-medium py-2 px-3 rounded-lg border border-slate-700/60 transition text-left flex items-center gap-2"
            >
              <Cpu className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <div className="flex flex-col">
                <span className="leading-tight text-slate-100 font-semibold">Explain Bytecode Logic</span>
                <span className="text-[8px] text-slate-400">Decode registers & registers layout</span>
              </div>
            </button>

            <button
              onClick={() => callAIAction("modernize")}
              disabled={isLoading}
              className="w-full bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs font-medium py-2 px-3 rounded-lg border border-slate-700/60 transition text-left flex items-center gap-2"
            >
              <Code2 className="w-4 h-4 text-orange-400 flex-shrink-0" />
              <div className="flex flex-col">
                <span className="leading-tight text-slate-100 font-semibold">Convert AS3 to TS</span>
                <span className="text-[8px] text-slate-400">Map curves to HTML5 Canvas</span>
              </div>
            </button>
          </div>

          <div className="text-[10px] text-slate-500 border-t border-slate-800/80 pt-3 flex flex-col gap-1.5">
            <div className="flex items-center gap-1 font-mono text-[9px] text-slate-400">
              <span>Model:</span>
              <span className="text-emerald-400 font-semibold">gemini-3.5-flash</span>
            </div>
            <p className="leading-relaxed">
              Gemini assists decompilers with decompilation pattern matching, naming recovery and modern canvas canvas bindings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
