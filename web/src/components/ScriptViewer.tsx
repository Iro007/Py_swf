import React, { useEffect, useState } from "react";
import { Check, Code2, RotateCcw, Save, Sparkles, Search } from "lucide-react";
import { assemble, DecompileSection, getDecompilation, getDisassembly } from "../api";
import { ScriptListing } from "../types";
import { highlightCode, renderHighlighted } from "../utils/syntaxHighlight";

interface Props {
  sid: string;
  tagIndex: number;
  tagName: string;
  onChanged: () => void;
  onError: (msg: string) => void;
}

type Mode = "disasm" | "source";

export default function ScriptViewer({ sid, tagIndex, tagName, onChanged, onError }: Props) {
  const [mode, setMode] = useState<Mode>("disasm");
  const [listing, setListing] = useState<ScriptListing | null>(null);
  const [selected, setSelected] = useState(0);
  const [code, setCode] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<number[]>([]);
  const [searchIndex, setSearchIndex] = useState(0);

  const [sections, setSections] = useState<DecompileSection[] | null>(null);
  const [srcSelected, setSrcSelected] = useState(0);

  const load = () => {
    setListing(null);
    setSections(null);
    getDisassembly(sid, tagIndex)
      .then((l) => {
        setListing(l);
        setSelected(0);
        setCode(l.scripts[0]?.code ?? "");
      })
      .catch((e) => onError(`Disassembly failed: ${e.message}`));
  };

  useEffect(load, [sid, tagIndex]);

  useEffect(() => {
    setMode("disasm");
    setSearchQuery("");
    setSearchResults([]);
    setSearchIndex(0);
  }, [sid, tagIndex]);

  const loadSource = () => {
    setMode("source");
    if (sections) return;
    getDecompilation(sid, tagIndex)
      .then((d) => {
        setSections(d.sections);
        setSrcSelected(0);
      })
      .catch((e) => onError(`Decompilation failed: ${e.message}`));
  };

  const selectBody = (idx: number) => {
    if (!listing) return;
    setSelected(idx);
    setCode(listing.scripts[idx]?.code ?? "");
    setSearchQuery("");
    setSearchResults([]);
    setSearchIndex(0);
  };

  const apply = async () => {
    if (!listing) return;
    setBusy(true);
    try {
      await assemble(sid, tagIndex, listing.scripts[selected].body_index, code);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onChanged();
    } catch (e: any) {
      onError(`Assembly failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (!query) {
      setSearchResults([]);
      setSearchIndex(0);
      return;
    }
    const text = mode === "disasm" ? code : sections?.[srcSelected]?.source ?? "";
    const results: number[] = [];
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    let pos = 0;
    while ((pos = lowerText.indexOf(lowerQuery, pos)) !== -1) {
      results.push(pos);
      pos += lowerQuery.length;
    }
    setSearchResults(results);
    setSearchIndex(0);
  };

  const srcSection = sections?.[srcSelected];
  const currentText = mode === "disasm" ? code : srcSection?.source ?? "";
  const tokens = highlightCode(currentText);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl flex flex-col h-[560px]">
      <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Code2 className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="font-sans text-sm text-slate-200 font-semibold shrink-0">{tagName}</span>
          {listing && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase shrink-0">
              {listing.kind}
            </span>
          )}
          {mode === "disasm" && listing && listing.scripts.length > 1 && (
            <select
              value={selected}
              onChange={(e) => selectBody(parseInt(e.target.value, 10))}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs font-mono rounded px-2 py-1 min-w-0 max-w-[300px] truncate"
            >
              {listing.scripts.map((s, i) => (
                <option key={i} value={i}>{s.name}</option>
              ))}
            </select>
          )}
          {mode === "source" && sections && sections.length > 1 && (
            <select
              value={srcSelected}
              onChange={(e) => setSrcSelected(parseInt(e.target.value, 10))}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs font-mono rounded px-2 py-1 min-w-0 max-w-[300px] truncate"
            >
              {sections.map((s, i) => (
                <option key={i} value={i}>{s.name}</option>
              ))}
            </select>
          )}
        </div>
        <div className="flex gap-2 shrink-0 items-center">
          <div className="flex bg-slate-950 p-0.5 border border-slate-800 rounded-md mr-1">
            <button
              onClick={() => setMode("disasm")}
              className={`px-2 py-1 text-[11px] font-semibold rounded transition ${
                mode === "disasm" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Disassembly
            </button>
            <button
              onClick={loadSource}
              className={`px-2 py-1 text-[11px] font-semibold rounded transition flex items-center gap-1 ${
                mode === "source" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Sparkles className="w-3 h-3" />
              Source
            </button>
          </div>
          
          {/* Search box */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search..."
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs font-mono rounded px-6 py-1 pl-8 w-48 focus:outline-none focus:border-emerald-500"
            />
            {searchResults.length > 0 && (
              <span className="text-[10px] text-slate-500 ml-1 px-1.5 py-0.5 bg-slate-950 rounded">
                {searchIndex + 1} / {searchResults.length}
              </span>
            )}
          </div>

          {mode === "disasm" && (
            <>
              <button
                onClick={() => selectBody(selected)}
                className="p-1 px-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition flex items-center gap-1 border border-slate-700/40"
                title="Discard edits"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Revert</span>
              </button>
              <button
                onClick={apply}
                disabled={busy || !listing}
                className="p-1 px-3 bg-amber-600 hover:bg-amber-700 active:scale-95 text-white rounded text-xs font-semibold transition flex items-center gap-1 shadow-md disabled:opacity-40"
                title="Assemble and write back into the tag"
              >
                {saved ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
                <span>{saved ? "Assembled!" : "Assemble"}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {mode === "disasm" ? (
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          className="flex-1 bg-slate-950 text-slate-200 font-mono text-xs p-4 outline-none resize-none leading-relaxed"
          placeholder={listing ? "" : "Loading disassembly…"}
        />
      ) : (
        <pre className="flex-1 bg-slate-950 text-slate-200 font-mono text-xs p-4 overflow-auto leading-relaxed whitespace-pre">
          {renderHighlighted(tokens)}
        </pre>
      )}

      <div className="p-2.5 bg-slate-900 border-t border-slate-800 text-[10px] font-mono text-slate-500 flex items-center justify-between">
        <span>
          {mode === "disasm"
            ? "Edit the P-code and press Assemble. Labels (L_n) are recomputed; constants are resolved against the pool."
            : "Source is experimental (decompiler v1): methods with complex control flow fall back to disassembly."}
        </span>
        {searchResults.length > 0 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSearchIndex((i) => (i > 0 ? i - 1 : searchResults.length - 1))}
              className="p-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 text-xs"
              title="Previous match"
            >
              ↑
            </button>
            <button
              onClick={() => setSearchIndex((i) => (i + 1) % searchResults.length)}
              className="p-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 text-xs"
              title="Next match"
            >
              ↓
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
