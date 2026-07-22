import { FileInfo, FontInfo, ScriptListing, SoundInfo, TagInfo } from "./types";

const BASE = "/api/files";

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export async function uploadSwf(file: File): Promise<FileInfo> {
  const form = new FormData();
  form.append("file", file, file.name);
  return jsonOrThrow(await fetch(BASE, { method: "POST", body: form }));
}

export async function getTags(sid: string): Promise<TagInfo[]> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags`));
}

export async function getRawBytes(sid: string, index: number): Promise<Uint8Array> {
  const resp = await fetch(`${BASE}/${sid}/tags/${index}/raw`);
  if (!resp.ok) throw new Error(resp.statusText);
  return new Uint8Array(await resp.arrayBuffer());
}

export async function putRawBytes(sid: string, index: number, bytes: Uint8Array): Promise<void> {
  const resp = await fetch(`${BASE}/${sid}/tags/${index}/raw`, {
    method: "PUT",
    headers: { "Content-Type": "application/octet-stream" },
    body: bytes,
  });
  await jsonOrThrow(resp);
}

export function imageUrl(sid: string, index: number): string {
  return `${BASE}/${sid}/tags/${index}/export/image`;
}

export async function getSvg(sid: string, index: number, ratio = 0): Promise<string> {
  const resp = await fetch(`${BASE}/${sid}/tags/${index}/export/svg?ratio=${ratio}`);
  if (!resp.ok) throw new Error((await resp.json()).detail ?? resp.statusText);
  return resp.text();
}

export async function getTimelineInfo(sid: string): Promise<{ frame_count: number }> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/timeline`));
}

export function frameSvgUrl(sid: string, frame: number): string {
  return `${BASE}/${sid}/frames/${frame}/svg`;
}

export async function getSpriteInfo(
  sid: string,
  index: number,
): Promise<{ char_id: number; declared_frames: number; frame_count: number }> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags/${index}/sprite-info`));
}

export function spriteFrameSvgUrl(sid: string, index: number, frame: number): string {
  return `${BASE}/${sid}/tags/${index}/sprite-frames/${frame}/svg`;
}

export async function getDisassembly(sid: string, index: number): Promise<ScriptListing> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags/${index}/disassemble`));
}

export interface DecompileSection {
  name: string;
  source: string;
  error: string | null;
}

export async function getDecompilation(
  sid: string,
  index: number,
): Promise<{ kind: string; sections: DecompileSection[] }> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags/${index}/decompile`));
}

export async function assemble(sid: string, index: number, bodyIndex: number, code: string): Promise<void> {
  const resp = await fetch(`${BASE}/${sid}/tags/${index}/assemble`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body_index: bodyIndex, code }),
  });
  await jsonOrThrow(resp);
}

export async function replaceResource(sid: string, index: number, file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file, file.name);
  const resp = await fetch(`${BASE}/${sid}/tags/${index}/replace`, { method: "POST", body: form });
  await jsonOrThrow(resp);
}

export function downloadUrl(sid: string): string {
  return `${BASE}/${sid}/download`;
}

export function soundUrl(sid: string, index: number): string {
  return `${BASE}/${sid}/tags/${index}/export/sound`;
}

export async function getSoundInfo(sid: string, index: number): Promise<SoundInfo> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags/${index}/sound-info`));
}

export function fontUrl(sid: string, index: number): string {
  return `${BASE}/${sid}/tags/${index}/export/font`;
}

export async function getFontInfo(sid: string, index: number): Promise<FontInfo> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags/${index}/font-info`));
}

export async function getTextSvg(sid: string, index: number): Promise<string> {
  const resp = await fetch(`${BASE}/${sid}/tags/${index}/export/text-svg`);
  if (!resp.ok) throw new Error((await resp.json()).detail ?? resp.statusText);
  return resp.text();
}

export async function getEditTextInfo(sid: string, index: number): Promise<Record<string, unknown>> {
  return jsonOrThrow(await fetch(`${BASE}/${sid}/tags/${index}/edit-text`));
}
