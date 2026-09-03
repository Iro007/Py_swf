import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

async function startServer() {
  const app = express();
  app.use(express.json({ limit: "50mb" }));
  const PORT = 3000;

  // AI decompression assistant endpoint
  app.post("/api/decompile-ai", async (req, res) => {
    try {
      const { bytecode, tagType, filename, context, taskType } = req.body;
      
      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        return res.status(500).json({ error: "GEMINI_API_KEY environment variable is not configured in Secrets." });
      }

      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            "User-Agent": "aistudio-build",
          },
        },
      });

      let prompt = "";
      if (taskType === "explain") {
        prompt = `Explain the following Flash ActionScript bytecode/disassembly instructions (Tag type: ${tagType || 'DoABC/DoAction'}).
Provide a clear, human-readable breakdown of:
1. The logical intention of the code.
2. Key functions, global triggers, variables, and imported namespaces/traits.
3. Flow controls, loops, and conditions.

File context: ${filename || 'decompiled_tag.swf'}

Bytecode/Disassembly snippet:
\`\`\`assembly
${bytecode || context}
\`\`\``;
      } else if (taskType === "decompile") {
        prompt = `You are a world-class professional Flash ActionScript decompiler engine (comparable to JPEXS Free Flash Decompiler).
Analyze this Flash bytecode/assembly block and reconstruct high-level, elegant, properly structured, and commented ActionScript ${tagType === 'DoAction' ? '1/2' : '3'} source code.
- If it's AS3, please structure it correctly inside a package and class framework with proper access specifiers, annotations, getters, setters, methods, and variables.
- Preserve semantic meanings indicated by multinames, traits, or metadata in the assembly.
- Add concise comments explaining what complex chunks are doing.
- Reply ONLY with the high-level code, without writing general introductory conversational filler. Use codeblocks for the ActionScript code.

Disassembly instruction set:
\`\`\`assembly
${bytecode || context}
\`\`\``;
      } else if (taskType === "modernize") {
        prompt = `You are an expert SWF-to-HTML5 conversion architect. Convert this Flash ActionScript logic or disassembly into modern, clean TypeScript and HTML5 Canvas API calls.
Explain how features like:
- Frame events (ENTER_FRAME, MOUSE_DOWN)
- Vector shapes rendering (moveTo, lineTo, beginFill)
- DisplayObject tree hierarchy logic (addChild, removeChild, Sprite)
are mapped. Give a complete, runnable typescript code structure.
Provide the code block prominently, followed by a succinct architecture map.

Flash context / instructions:
\`\`\`
${bytecode || context}
\`\`\``;
      } else {
        prompt = `Decompile or analyze this segment of SWF payload:
${bytecode || context}`;
      }

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: prompt,
      });

      res.json({ result: response.text });
    } catch (err: any) {
      console.error(err);
      res.status(500).json({ error: err.message || "An error occurred with Gemini." });
    }
  });

  // Decompile ABC server-side using bundled Python tool (POST JSON { b64, zip?: boolean })
  app.post('/api/decompile-abc', async (req, res) => {
    try {
      const { b64, zip } = req.body as { b64?: string; zip?: boolean };
      if (!b64) return res.status(400).json({ error: "Missing base64 ABC in 'b64' field" });

      const cp = await import('child_process');

      if (zip) {
        // Request Python to emit a ZIP to stdout (binary)
        const py = cp.spawnSync('python', [
          path.join(process.cwd(), 'py_swf', 'tools', 'decompile_abc.py'),
          b64,
          '--zip'
        ], { maxBuffer: 50 * 1024 * 1024, timeout: 60 * 1000 });

        if (py.error) {
          console.error(py.error);
          return res.status(500).json({ error: String(py.error) });
        }

        if (py.status !== 0) {
          // Try to parse stderr as JSON-friendly text
          const stderr = py.stderr ? py.stderr.toString('utf8') : 'Python decompiler failed';
          return res.status(500).json({ error: stderr });
        }

        const zipBuf = py.stdout as Buffer;
        res.setHeader('Content-Type', 'application/zip');
        res.setHeader('Content-Disposition', 'attachment; filename=decompiled_as3.zip');
        return res.send(zipBuf);
      }

      // Default: text output
      const py = cp.spawnSync('python', [
        path.join(process.cwd(), 'py_swf', 'tools', 'decompile_abc.py'),
        b64
      ], { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024, timeout: 30 * 1000 });

      if (py.error) {
        console.error(py.error);
        return res.status(500).json({ error: String(py.error) });
      }

      if (py.status !== 0) {
        return res.status(500).json({ error: py.stderr || 'Python decompiler failed' });
      }

      // Optionally request AI-enhanced suggestions if client asked and Gemini key is configured
      let resultText = py.stdout;
      if (req.body && req.body.ai && process.env.GEMINI_API_KEY) {
        try {
          const aiResp = await fetch(`http://localhost:${PORT}/api/decompile-ai`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bytecode: resultText, taskType: 'decompile', filename: req.body.filename || 'decompiled_tag.swf' })
          });
          if (aiResp.ok) {
            const aiJson = await aiResp.json();
            return res.json({ result: resultText, ai: aiJson.result });
          }
        } catch (e) {
          console.error('AI augmentation failed:', e);
        }
      }

      return res.json({ result: resultText });
    } catch (err: any) {
      console.error(err);
      res.status(500).json({ error: err.message || 'Unknown error' });
    }
  });

  // Health check
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
  });

  // SWF parse endpoint (JSON body with base64 file: { filename, b64 })
  app.post("/api/parse-swf", async (req, res) => {
    try {
      const { filename, b64 } = req.body as { filename?: string; b64?: string };
      if (!b64) return res.status(400).json({ error: "Request missing base64 payload in 'b64' field" });

      const buf = Buffer.from(b64, 'base64');
      if (buf.length < 8) return res.status(400).json({ error: "File too short to be SWF" });

      const sig = buf.toString("ascii", 0, 3);
      const version = buf.readUInt8(3);
      const fileLength = buf.readUInt32LE(4);

      let uncompressed: Buffer;
      if (sig === "CWS") {
        const zlib = await import("zlib");
        const zlibPayload = buf.slice(8);
        uncompressed = Buffer.concat([buf.slice(0, 8), zlib.inflateSync(zlibPayload)]);
      } else if (sig === "FWS") {
        uncompressed = buf;
      } else if (sig === "ZWS") {
        return res.status(400).json({ error: "LZMA-compressed ZWS files are not supported by server parser." });
      } else {
        return res.status(400).json({ error: `Unknown SWF signature: ${sig}` });
      }

      const tags: Array<{ type: number; length: number; offset: number }> = [];
      let offset = 8;
      while (offset + 2 <= uncompressed.length) {
        const header = uncompressed.readUInt16LE(offset);
        offset += 2;
        const tagType = header >> 6;
        let tagLen = header & 0x3F;
        if (tagLen === 0x3F) {
          if (offset + 4 > uncompressed.length) break;
          tagLen = uncompressed.readUInt32LE(offset);
          offset += 4;
        }
        if (offset + tagLen > uncompressed.length) break;
        tags.push({ type: tagType, length: tagLen, offset });
        offset += tagLen;
        if (tagType === 0) break;
      }

      return res.json({ filename: filename || "uploaded.swf", signature: sig, version, fileLength, tagsCount: tags.length, tags });
    } catch (err: any) {
      console.error(err);
      return res.status(500).json({ error: err.message || String(err) });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
