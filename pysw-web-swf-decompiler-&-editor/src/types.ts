export interface SWFHeader {
  signature: "FWS" | "CWS" | "ZWS";
  version: number;
  fileLength: number;
  frameSize: {
    xMin: number;
    xMax: number;
    yMin: number;
    yMax: number;
    width: number;
    height: number;
  };
  frameRate: number;
  frameCount: number;
}

export interface SWFTag {
  type: number;
  typeName: string;
  name: string;
  id?: number; // Character ID or unique asset ID
  length: number;
  offset: number;
  content: Uint8Array;
  disassembly?: string; // Assembly instructions for ActionScript
  properties?: Record<string, any>; // Parsed parameters
}

export interface SWFFile {
  filename: string;
  header: SWFHeader;
  tags: SWFTag[];
  rawBytes: Uint8Array;
}

// Tree items in PySW-like directory view
export type SWFCategory = 
  | "header"
  | "shapes"
  | "images"
  | "sounds"
  | "texts"
  | "buttons"
  | "sprites"
  | "scripts"
  | "frames"
  | "others";

export interface TreeItem {
  id: string;
  label: string;
  type: SWFCategory | "tag-node";
  iconName: string;
  tagIndex?: number; // maps back to the tags list
  children?: TreeItem[];
  tagType?: number;
}
