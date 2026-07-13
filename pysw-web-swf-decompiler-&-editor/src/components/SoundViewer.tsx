import React, { useRef, useState, useEffect } from "react";
import { Play, Pause, Volume2, Music, Check, Headphones } from "lucide-react";

interface SoundViewerProps {
  id: number;
  name: string;
  duration: number;
  frequency: number;
  type: "MP3" | "WAV";
  waveType: "sine" | "square" | "sawtooth" | "triangle";
  caption: string;
}

export default function SoundViewer({
  id,
  name,
  duration,
  frequency,
  type,
  waveType,
  caption
}: SoundViewerProps) {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(0.3);
  const [synthWave, setSynthWave] = useState<"sine" | "square" | "sawtooth" | "triangle">(waveType);

  // Web Audio Refs
  const audioCtxRef = useRef<AudioContext | null>(null);
  const oscNodeRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const animationRef = useRef<number | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Stop sound on unmount
  useEffect(() => {
    return () => {
      stopOscillator();
    };
  }, []);

  // Update volume live
  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.setValueAtTime(volume, audioCtxRef.current?.currentTime || 0);
    }
  }, [volume]);

  // Update wave type live
  useEffect(() => {
    if (oscNodeRef.current) {
      oscNodeRef.current.type = synthWave;
    }
  }, [synthWave]);

  const startOscillator = () => {
    try {
      // 1. Initialize AudioContext
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      const ctx = audioCtxRef.current;
      if (ctx.state === "suspended") {
        ctx.resume();
      }

      // 2. Clear old osc if any
      stopOscillator();

      // 3. Create nodes
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = synthWave;
      // Synthesize based on note details we passed
      osc.frequency.setValueAtTime(frequency, ctx.currentTime);

      gain.gain.setValueAtTime(volume, ctx.currentTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();

      oscNodeRef.current = osc;
      gainNodeRef.current = gain;
      setIsPlaying(true);

      // Trigger automatic stop after sound's custom duration
      setTimeout(() => {
        setIsPlaying(currentState => {
          if (currentState) {
            stopOscillator();
          }
          return false;
        });
      }, duration * 1000);

      // Render waveform loop
      drawWaveform();
    } catch (e) {
      console.error("Audio Context launch failed:", e);
    }
  };

  const stopOscillator = () => {
    if (oscNodeRef.current) {
      try {
        oscNodeRef.current.stop();
      } catch (err) {}
      oscNodeRef.current.disconnect();
      oscNodeRef.current = null;
    }
    if (gainNodeRef.current) {
      gainNodeRef.current.disconnect();
      gainNodeRef.current = null;
    }
    setIsPlaying(false);
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  };

  const handlePlayToggle = () => {
    if (isPlaying) {
      stopOscillator();
    } else {
      startOscillator();
    }
  };

  const drawWaveform = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    let offset = 0;

    const render = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0c1524";
      ctx.fillRect(0, 0, w, h);

      // Draw grid lines
      ctx.strokeStyle = "#1e293b";
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(w, h / 2);
      ctx.stroke();

      // Render neon sound wave
      ctx.strokeStyle = "#10b981";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      
      offset += 0.2;
      for (let x = 0; x < w; x++) {
        let amp = 0;
        if (synthWave === "sine") {
          amp = Math.sin(x * 0.08 + offset) * 20;
        } else if (synthWave === "square") {
          amp = Math.sign(Math.sin(x * 0.08 + offset)) * 18;
        } else if (synthWave === "sawtooth") {
          amp = ((x * 0.04 + offset) % 2 - 1) * 22;
        } else if (synthWave === "triangle") {
          amp = (Math.abs(((x * 0.08 + offset) % 4) - 2) - 1) * 22;
        }

        if (x === 0) {
          ctx.moveTo(x, h / 2 + amp);
        } else {
          ctx.lineTo(x, h / 2 + amp);
        }
      }
      ctx.stroke();

      // Draw vertical amplitude frequency bars
      ctx.fillStyle = "#10b981/20";
      for (let x = 0; x < w; x += 15) {
        const barHeight = Math.abs(Math.sin(x * 0.05 + offset)) * (h / 2.5);
        ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
        ctx.fillRect(x, h / 2 - barHeight, 8, barHeight * 2);
      }

      animationRef.current = requestAnimationFrame(render);
    };

    render();
  };

  // Draw static flat wave preview when inactive
  useEffect(() => {
    if (!isPlaying) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#020617";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, canvas.height / 2);
      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();

      // Draw a muted sine wave
      ctx.strokeStyle = "#10b981/40";
      ctx.beginPath();
      for (let x = 0; x < canvas.width; x++) {
        const y = canvas.height / 2 + Math.sin(x * 0.04) * Math.cos(x * 0.01) * 12;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }, [isPlaying]);

  return (
    <div id={`sound-viewer-${id}`} className="bg-slate-900 border border-slate-700/60 rounded-xl overflow-hidden shadow-2xl transition duration-300 hover:border-slate-600/80 p-5">
      {/* Wave header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg animate-pulse">
            <Music className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-slate-150 font-medium text-sm font-sans">{name}</h4>
            <p className="text-[10px] font-mono text-slate-400">DefineSound ID: #{id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-slate-950 px-2.5 py-1 rounded text-xs font-mono text-emerald-400">
          <Headphones className="w-3.5 h-3.5" />
          <span>{type} Stream</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Wave visualizer */}
        <div className="flex flex-col">
          <canvas
            ref={canvasRef}
            width={340}
            height={130}
            className="w-full bg-[#030712] border border-slate-800 rounded-lg overflow-hidden"
          />
          <div className="flex justify-between items-center mt-3 px-1 text-[10px] font-mono text-slate-500">
            <span>0.0s</span>
            <span className="text-emerald-500 bg-emerald-950/40 px-2 py-0.5 rounded">Oscillator emulator active</span>
            <span>{duration.toFixed(2)}s</span>
          </div>
        </div>

        {/* Audio parameter control */}
        <div className="flex flex-col justify-between">
          <div className="space-y-3">
            <span className="block text-[10px] uppercase tracking-wider font-mono text-slate-400 font-semibold mb-1">
              Synth Controller
            </span>

            {/* Oscillator Select */}
            <div className="grid grid-cols-4 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-850">
              {(["sine", "square", "sawtooth", "triangle"] as const).map((w) => (
                <button
                  key={w}
                  onClick={() => setSynthWave(w)}
                  className={`text-[9px] font-mono font-medium py-1 rounded capitalize transition duration-150 ${
                    synthWave === w ? "bg-emerald-500 text-slate-950 font-bold" : "text-slate-400 hover:bg-slate-900"
                  }`}
                >
                  {w}
                </button>
              ))}
            </div>

            {/* Parameter readings */}
            <div className="bg-slate-950 border border-slate-850/80 p-2.5 rounded-lg text-[10px] font-mono text-slate-400 space-y-1.5">
              <div className="flex justify-between">
                <span>Sound frequency:</span>
                <span className="text-slate-200">{frequency} Hz (pitch key)</span>
              </div>
              <div className="flex justify-between">
                <span>Mono/Stereo:</span>
                <span className="text-slate-200">2 Channels (Stereo)</span>
              </div>
              <div className="flex justify-between">
                <span>Container tags:</span>
                <span className="text-slate-200">14 (DefineSound)</span>
              </div>
            </div>

            {/* Volume controller */}
            <div className="flex items-center gap-2 bg-slate-950 px-2 py-2 rounded border border-slate-850">
              <Volume2 className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="flex-1 h-1 bg-slate-800 rounded appearance-none cursor-pointer accent-emerald-400"
              />
              <span className="text-[9px] text-slate-400 font-mono w-6 text-right">{Math.round(volume * 100)}%</span>
            </div>
          </div>

          <button
            onClick={handlePlayToggle}
            className={`w-full py-2.5 px-4 mt-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition duration-150 ${
              isPlaying
                ? "bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30"
                : "bg-emerald-500 font-bold hover:bg-emerald-600 active:scale-[98%] text-slate-950"
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-4 h-4 text-red-400" />
                <span>Stop Demo Audio</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-slate-950" />
                <span>Play Sound Block</span>
              </>
            )}
          </button>
        </div>
      </div>
      <div className="text-[11px] text-slate-400 italic mt-3.5 border-t border-slate-800/40 pt-2.5 leading-relaxed font-sans">
        {caption}
      </div>
    </div>
  );
}
