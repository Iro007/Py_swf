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

  // Health check
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
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
