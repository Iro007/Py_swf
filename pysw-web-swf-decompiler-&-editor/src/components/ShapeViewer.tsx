import React, { useEffect, useRef, useState } from "react";
import { Play, Pause, RotateCcw, ZoomIn, ZoomOut, Paintbrush, Sliders } from "lucide-react";

interface PathNode {
  type: "move" | "line" | "curve";
  x: number;
  y: number;
  cx?: number;
  cy?: number;
}

interface ShapeViewerProps {
  id: number;
  width: number;
  height: number;
  paths: PathNode[];
  fillStyle: string;
  strokeStyle: string;
  lineWidth: number;
  onUpdateShape?: (shapeId: number, fill: string, lineCol: string, strokeWidth: number) => void;
}

export default function ShapeViewer({
  id,
  width,
  height,
  paths,
  fillStyle,
  strokeStyle,
  lineWidth,
  onUpdateShape
}: ShapeViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState<number>(1.2);
  const [isRotating, setIsRotating] = useState<boolean>(false);
  const [angle, setAngle] = useState<number>(0);
  const [localFill, setLocalFill] = useState<string>(fillStyle);
  const [localStroke, setLocalStroke] = useState<string>(strokeStyle);
  const [localLineWidth, setLocalLineWidth] = useState<number>(lineWidth);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    setLocalFill(fillStyle);
    setLocalStroke(strokeStyle);
    setLocalLineWidth(lineWidth);
  }, [fillStyle, strokeStyle, lineWidth]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear and draw background grid
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawGrid(ctx, canvas.width, canvas.height);

    ctx.save();
    // Center of canvas
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.scale(zoom, zoom);
    ctx.rotate((angle * Math.PI) / 180);

    // Render vector paths
    ctx.beginPath();
    ctx.fillStyle = localFill;
    ctx.strokeStyle = localStroke;
    ctx.lineWidth = localLineWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Shift back to center the shape bounding box
    const offsetX = -width / 2;
    const offsetY = -height / 2;

    if (paths && paths.length > 0) {
      paths.forEach((node) => {
        if (node.type === "move") {
          ctx.moveTo(node.x + offsetX, node.y + offsetY);
        } else if (node.type === "line") {
          ctx.lineTo(node.x + offsetX, node.y + offsetY);
        } else if (node.type === "curve") {
          const cx = node.cx !== undefined ? node.cx : node.x;
          const cy = node.cy !== undefined ? node.cy : node.y;
          ctx.quadraticCurveTo(cx + offsetX, cy + offsetY, node.x + offsetX, node.y + offsetY);
        }
      });
    } else {
      // Draw standard fallback square if empty path
      ctx.rect(offsetX, offsetY, width, height);
    }

    ctx.fill();
    if (localLineWidth > 0) {
      ctx.stroke();
    }
    ctx.restore();
  }, [zoom, angle, paths, localFill, localStroke, localLineWidth, width, height]);

  // Handle rotation loop
  useEffect(() => {
    if (isRotating) {
      const tick = () => {
        setAngle((prev) => (prev + 2) % 360);
        animationRef.current = requestAnimationFrame(tick);
      };
      animationRef.current = requestAnimationFrame(tick);
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isRotating]);

  const drawGrid = (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 0.5;
    const gridSize = 20;

    // Draw mesh lines
    for (let x = 0; x < w; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Draw origin axes
    ctx.strokeStyle = "#94a3b8";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(w / 2, 0);
    ctx.lineTo(w / 2, h);
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();
  };

  const handleApplyChanges = () => {
    if (onUpdateShape) {
      onUpdateShape(id, localFill, localStroke, localLineWidth);
    }
  };

  return (
    <div id={`shape-viewer-${id}`} className="bg-slate-900 border border-slate-700/60 rounded-xl overflow-hidden shadow-2xl transition duration-300 hover:border-slate-600/80">
      {/* Top Header info */}
      <div className="flex items-center justify-between bg-slate-950/80 px-4 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Paintbrush className="w-4 h-4 text-emerald-400" />
          <span className="font-mono text-xs text-slate-300 font-semibold">
            DefineShape ID: <span className="text-emerald-400">#{id}</span>
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <span>Bounding Box: {width} x {height} px</span>
          <span className="bg-slate-800 px-2 py-0.5 rounded text-emerald-400">Vector twips</span>
        </div>
      </div>

      {/* Main Area: Split Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 mini:grid-cols-3">
        {/* Left: Canvas drawing frame */}
        <div className="col-span-2 relative bg-slate-950 min-h-[340px] flex items-center justify-center p-4">
          <canvas
            ref={canvasRef}
            width={400}
            height={340}
            className="border border-slate-800/80 rounded-lg bg-[#0b0f19] cursor-grab active:cursor-grabbing"
          />

          {/* Quick float sliders */}
          <div className="absolute bottom-4 left-4 flex gap-2">
            <button
              onClick={() => setIsRotating(!isRotating)}
              className={`p-2 rounded-lg text-white font-semibold transition ${
                isRotating ? "bg-emerald-600 hover:bg-emerald-700" : "bg-slate-800 hover:bg-slate-700"
              }`}
              title={isRotating ? "Pause Timeline Anim" : "Animate Rotate Timeline"}
            >
              {isRotating ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button
              onClick={() => {
                setAngle(0);
                setZoom(1.2);
                setIsRotating(false);
              }}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
              title="Reset Viewport"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-slate-900/90 border border-slate-700/60 p-1.5 rounded-lg text-slate-200 text-xs">
            <button onClick={() => setZoom(Math.max(0.4, zoom - 0.2))} className="p-1 hover:bg-slate-800 rounded">
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono w-10 text-center">{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom(Math.min(5, zoom + 0.2))} className="p-1 hover:bg-slate-800 rounded">
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Shape Parameters & Real Editor Customizing */}
        <div className="bg-slate-900 border-t md:border-t-0 md:border-l border-slate-800 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-slate-200 text-xs font-semibold mb-3">
              <Sliders className="w-3.5 h-3.5 text-slate-400" />
              <span>SWF Shape Property Editor</span>
            </div>

            {/* Editing Inputs */}
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] uppercase tracking-wider font-mono text-slate-400 mb-1.5 font-semibold">
                  Vector Fill Color
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={localFill}
                    onChange={(e) => setLocalFill(e.target.value)}
                    className="w-10 h-8 rounded border border-slate-700 bg-transparent cursor-pointer"
                  />
                  <input
                    type="text"
                    value={localFill}
                    onChange={(e) => setLocalFill(e.target.value)}
                    placeholder="#e74c3c"
                    className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider font-mono text-slate-400 mb-1.5 font-semibold">
                  Vector Stroke Color
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={localStroke}
                    onChange={(e) => setLocalStroke(e.target.value)}
                    className="w-10 h-8 rounded border border-slate-700 bg-transparent cursor-pointer"
                  />
                  <input
                    type="text"
                    value={localStroke}
                    onChange={(e) => setLocalStroke(e.target.value)}
                    placeholder="#2c3e50"
                    className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-[10px] uppercase tracking-wider font-mono text-slate-400 font-semibold">
                    Stroke Width
                  </label>
                  <span className="font-mono text-[10px] text-slate-400">{localLineWidth}px</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="12"
                  step="0.5"
                  value={localLineWidth}
                  onChange={(e) => setLocalLineWidth(parseFloat(e.target.value))}
                  className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-emerald-400 focus:outline-none"
                />
              </div>
            </div>

            {/* Instruction List */}
            <div className="mt-5 pt-4 border-t border-slate-800">
              <span className="block text-[9px] uppercase tracking-wider font-mono text-slate-500 font-semibold mb-2">
                Path Operations [{paths?.length || 0}]
              </span>
              <div className="max-h-[110px] overflow-y-auto bg-slate-950 border border-slate-850 p-2 rounded text-[10px] font-mono text-slate-400 space-y-1">
                {paths && paths.map((p, idx) => (
                  <div key={idx} className="flex justify-between hover:bg-slate-900/50 px-1 py-0.5 rounded">
                    <span className="text-emerald-400 font-medium capitalize">{p.type}To</span>
                    <span>
                      {p.cx !== undefined ? `cp(${p.cx},${p.cy}) ` : ""}
                      pt({p.x},{p.y})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={handleApplyChanges}
            className="w-full mt-4 bg-emerald-500 hover:bg-emerald-600 active:scale-[98%] text-slate-950 text-xs font-semibold py-2 px-3 rounded-lg transition shadow-md flex items-center justify-center gap-1.5"
          >
            <Paintbrush className="w-3.5 h-3.5" />
            Apply Vector Changes
          </button>
        </div>
      </div>
    </div>
  );
}
