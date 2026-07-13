import { SWFFile, SWFTag, SWFHeader } from "../types";

export interface VectorShape {
  id: number;
  width: number;
  height: number;
  paths: Array<{
    type: "move" | "line" | "curve";
    x: number;
    y: number;
    cx?: number; // control point for curves
    cy?: number;
  }>;
  fillStyle: string;
  strokeStyle: string;
  lineWidth: number;
}

export interface SampleSWF {
  filename: string;
  displayName: string;
  description: string;
  fileSizeLabel: string;
  header: {
    signature: "FWS" | "CWS";
    version: number;
    fileLength: number;
    frameSize: { width: number; height: number };
    frameRate: number;
    frameCount: number;
  };
  vectorShapes: VectorShape[];
  images: Array<{
    id: number;
    name: string;
    width: number;
    height: number;
    color: string;
    type: "PNG" | "JPEG";
    base64?: string; // fallback or decorative styling indicators
    caption: string;
  }>;
  sounds: Array<{
    id: number;
    name: string;
    duration: number; // in seconds
    frequency: number; // synth frequency
    type: "MP3" | "WAV";
    waveType: "sine" | "square" | "sawtooth" | "triangle";
    caption: string;
  }>;
  texts: Array<{
    id: number;
    name: string;
    content: string;
    font: string;
    color: string;
    align: "left" | "center" | "right";
  }>;
  scripts: Array<{
    id: number;
    name: string; // e.g. "com.game.Player"
    tagType: "DoABC" | "DoAction";
    bytecode: string;
    decompiledAS: string; // The ActionScript 3 high-level equivalent
  }>;
}

export const SAMPLE_SWFS: SampleSWF[] = [
  {
    filename: "super_mario_retro_stage.swf",
    displayName: "👾 Retro Platformer (AVM3/AS3)",
    description: "A functional platformer asset package containing sprites, dynamic inputs, collision vectors, sound loops, and level codes written in ActionScript 3.0.",
    fileSizeLabel: "234.5 KB",
    header: {
      signature: "CWS",
      version: 11,
      fileLength: 240128,
      frameSize: { width: 800, height: 600 },
      frameRate: 60,
      frameCount: 1800
    },
    vectorShapes: [
      {
        id: 101,
        width: 64,
        height: 64,
        paths: [
          { type: "move", x: 10, y: 10 },
          { type: "line", x: 54, y: 10 },
          { type: "line", x: 54, y: 40 },
          { type: "curve", cx: 54, cy: 54, x: 40, y: 54 },
          { type: "line", x: 10, y: 54 },
          { type: "line", x: 10, y: 10 }
        ],
        fillStyle: "#e74c3c", // Red cap/shirt
        strokeStyle: "#2c3e50",
        lineWidth: 3
      },
      {
        id: 102,
        width: 120,
        height: 200,
        paths: [
          { type: "move", x: 20, y: 20 },
          { type: "line", x: 100, y: 20 },
          { type: "line", x: 100, y: 80 },
          { type: "curve", cx: 60, cy: 120, x: 20, y: 80 },
          { type: "line", x: 20, y: 20 }
        ],
        fillStyle: "#3498db", // Blue overalls
        strokeStyle: "#2c3e50",
        lineWidth: 2
      },
      {
        id: 103,
        width: 150,
        height: 80,
        paths: [
          { type: "move", x: 5, y: 40 },
          { type: "curve", cx: 30, cy: 10, x: 75, y: 10 },
          { type: "curve", cx: 120, cy: 10, x: 145, y: 40 },
          { type: "curve", cx: 120, cy: 70, x: 75, y: 70 },
          { type: "curve", cx: 30, cy: 70, x: 5, y: 40 }
        ],
        fillStyle: "#2ecc71", // Green Pipe or bushes
        strokeStyle: "#27ae60",
        lineWidth: 4
      }
    ],
    images: [
      {
        id: 201,
        name: "img_char_mario_idle.png",
        width: 32,
        height: 48,
        color: "#e74c3c",
        type: "PNG",
        caption: "Main Character sprite sheet in PNG format. Compressed via Zlib DEFLATE."
      },
      {
        id: 202,
        name: "img_level_tileset.png",
        width: 256,
        height: 256,
        color: "#f39c12",
        type: "PNG",
        caption: "Bento level bricks, pipes, ground blocks and platform sprite textures."
      }
    ],
    sounds: [
      {
        id: 301,
        name: "snd_jump_synth.wav",
        duration: 0.25,
        frequency: 440,
        type: "WAV",
        waveType: "triangle",
        caption: "8-bit high-pitch classic retro jump action sound element."
      },
      {
        id: 302,
        name: "snd_music_theme.mp3",
        duration: 92,
        frequency: 261.6,
        type: "MP3",
        waveType: "sawtooth",
        caption: "Synth loop retro arcade background soundtrack."
      }
    ],
    texts: [
      {
        id: 401,
        name: "txt_score_display",
        content: "SCORE: 000000",
        font: "Monospace / Courier New",
        color: "#ffffff",
        align: "right"
      },
      {
        id: 402,
        name: "txt_loading_screen",
        content: "SUPER RETRO STAGE. TAP ENTER TO START GAME",
        font: "Arial / System-UI",
        color: "#f1c40f",
        align: "center"
      }
    ],
    scripts: [
      {
        id: 501,
        name: "com.game.PlayerController",
        tagType: "DoABC",
        bytecode: `// Bytecode segment for PlayerController.as (AVM2)
method_info: PlayerController (param_count=2, return_type="void")
  max_stack: 8, local_count: 5, max_scope: 4
  instructions:
    0: getlocal_0
    1: pushscope
    2: getlocal_0
    3: constructsuper     (args_count=0)
    5: getlocal_0
    6: pushdouble         0.0
    8: setproperty       QName(PackageNamespace(""), "vx")
    10: getlocal_0
    11: pushdouble         0.0
    13: setproperty       QName(PackageNamespace(""), "vy")
    15: getlocal_0
    16: findpropstrict     QName(PackageNamespace(""), "addEventListener")
    18: pushstring         "enterFrame"
    20: getlocal_0
    21: getproperty       QName(PackageNamespace(""), "onUpdate")
    23: callpropvoid      QName(PackageNamespace(""), "addEventListener") (args_count=2)
    26: getlocal_1         ; stageRef
    27: findpropstrict     QName(PackageNamespace(""), "addEventListener")
    29: pushstring         "keyDown"
    31: getlocal_0
    32: getproperty       QName(PackageNamespace(""), "onKeyDown")
    34: callpropvoid      QName(PackageNamespace(""), "addEventListener") (args_count=2)
    37: returnvoid

method_info: onKeyDown (param_count=1, return_type="void")
  instructions:
    0: getlocal_0
    1: pushscope
    2: getlocal_1         ; KeyboardEvent
    3: getproperty       QName(PackageNamespace(""), "keyCode")
    5: setlocal_2
    6: getlocal_2
    7: pushint           37  ; KEY_LEFT
    9: ifne              18
    12: getlocal_0
    13: pushdouble       -5.5
    15: setproperty      QName(PackageNamespace(""), "vx")
    17: jump             40
    18: getlocal_2
    19: pushint           39  ; KEY_RIGHT
    21: ifne              30
    24: getlocal_0
    25: pushdouble       5.5
    27: setproperty      QName(PackageNamespace(""), "vx")
    29: jump             40
    30: getlocal_2
    31: pushint           32  ; KEY_SPACE
    33: ifne              40
    36: getlocal_0
    37: callpropvoid     QName(PackageNamespace(""), "jump") (args_count=0)
    40: returnvoid

method_info: jump (param_count=0, return_type="void")
  instructions:
    0: getlocal_0
    1: pushscope
    2: getlocal_0
    3: getproperty       QName(PackageNamespace(""), "isGrounded")
    5: iffalse           14
    8: getlocal_0
    9: pushdouble       -12.0
    11: setproperty      QName(PackageNamespace(""), "vy")
    13: getlocal_0
    14: pushfalse
    15: setproperty      QName(PackageNamespace(""), "isGrounded")
    17: returnvoid`,
        decompiledAS: `package com.game {
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.events.KeyboardEvent;
    import flash.ui.Keyboard;
    import flash.media.Sound;

    /**
     * Decompiled PlayerController class responsible for physical vectors,
     * directional keyboard triggers, and high-frequency collision logic.
     */
    public class PlayerController extends Sprite {
        public var vx: Number;
        public var vy: Number;
        public var gravity: Number = 0.5;
        public var isGrounded: Boolean = true;
        
        [Embed(source="snd_jump_synth.wav")]
        private var JumpSoundClass: Class;
        private var jumpSound: Sound;

        public function PlayerController(stageRef: Sprite) {
            super();
            this.vx = 0.0;
            this.vy = 0.0;
            this.jumpSound = new JumpSoundClass() as Sound;
            
            this.addEventListener(Event.ENTER_FRAME, onUpdate);
            stageRef.addEventListener(KeyboardEvent.KEY_DOWN, onKeyDown);
            stageRef.addEventListener(KeyboardEvent.KEY_UP, onKeyUp);
        }

        public function onUpdate(event: Event): void {
            // Apply physical vectors
            if (!isGrounded) {
                vy += gravity;
            }
            
            this.x += vx;
            this.y += vy;
            
            // Render limits and floor collision check
            if (this.y >= 450) {
                this.y = 450;
                this.vy = 0;
                this.isGrounded = true;
            }
            
            // Friction decay
            vx *= 0.85;
        }

        public function onKeyDown(event: KeyboardEvent): void {
            switch (event.keyCode) {
                case Keyboard.LEFT:
                    vx = -5.5;
                    break;
                case Keyboard.RIGHT:
                    vx = 5.5;
                    break;
                case Keyboard.SPACE:
                case Keyboard.UP:
                    jump();
                    break;
            }
        }

        public function onKeyUp(event: KeyboardEvent): void {
            if (event.keyCode == Keyboard.LEFT || event.keyCode == Keyboard.RIGHT) {
                vx = 0;
            }
        }

        public function jump(): void {
            if (isGrounded) {
                vy = -12.0;
                isGrounded = false;
                try {
                    jumpSound.play();
                } catch (e: Error) {
                    // Fail gracefully if audio system is locked
                }
            }
        }
    }
}`
      },
      {
        id: 502,
        name: "com.game.LevelController",
        tagType: "DoABC",
        bytecode: `// Bytecode segment for LevelController.as
method_info: LevelController (param_count=0, return_type="void")
  instructions:
    0: getlocal_0
    1: pushscope
    2: getlocal_0
    3: constructsuper     (args_count=0)
    5: findpropstrict     QName(PackageNamespace(""), "generateTerrain")
    7: callpropvoid      QName(PackageNamespace(""), "generateTerrain") (args_count=0)
    10: returnvoid`,
        decompiledAS: `package com.game {
    import flash.display.Sprite;
    import flash.geom.Rectangle;

    /**
     * Managed game background grid mapping, tile creation,
     * and modular bounding boxes for block layers.
     */
    public class LevelController extends Sprite {
        private var grid: Array;
        public var blocks: Array;

        public function LevelController() {
            super();
            this.grid = [];
            this.blocks = [];
            generateTerrain();
        }

        public function generateTerrain(): void {
            // Generate standard tile vectors for drawing
            for (var col: int = 0; col < 25; col++) {
                // Ground creation
                var groundBlock: Sprite = new Sprite();
                groundBlock.graphics.beginFill(0x8e44ad); // Purple world ground
                groundBlock.graphics.drawRect(col * 32, 500, 32, 100);
                groundBlock.graphics.endFill();
                addChild(groundBlock);
                blocks.push(groundBlock);
            }
        }
    }
}`
      }
    ]
  },
  {
    filename: "interactive_promotion_banner.swf",
    displayName: "✨ Interactive Banner (AVM2/AS2)",
    description: "An elegant promotional Flash Banner styled with smooth fading vector masks, glowing button rollovers, and simple ActionScript 2 timeline controls.",
    fileSizeLabel: "84.2 KB",
    header: {
      signature: "FWS",
      version: 9,
      fileLength: 86224,
      frameSize: { width: 728, height: 90 },
      frameRate: 24,
      frameCount: 120
    },
    vectorShapes: [
      {
        id: 111,
        width: 728,
        height: 90,
        paths: [
          { type: "move", x: 0, y: 0 },
          { type: "line", x: 728, y: 0 },
          { type: "line", x: 728, y: 90 },
          { type: "line", x: 0, y: 90 },
          { type: "line", x: 0, y: 0 }
        ],
        fillStyle: "#1a1a24",
        strokeStyle: "#4b5563",
        lineWidth: 1
      },
      {
        id: 112,
        width: 140,
        height: 38,
        paths: [
          { type: "move", x: 5, y: 5 },
          { type: "line", x: 135, y: 5 },
          { type: "line", x: 135, y: 33 },
          { type: "line", x: 5, y: 33 },
          { type: "line", x: 5, y: 5 }
        ],
        fillStyle: "#2563eb", // Call To Action Blue Button
        strokeStyle: "#ffffff",
        lineWidth: 2
      }
    ],
    images: [
      {
        id: 211,
        name: "product_showcase.jpg",
        width: 320,
        height: 90,
        color: "#111827",
        type: "JPEG",
        caption: "JPEG standard tag containing product detail illustration overlay."
      }
    ],
    sounds: [
      {
        id: 311,
        name: "rollover_tick.wav",
        duration: 0.1,
        frequency: 880,
        type: "WAV",
        waveType: "sine",
        caption: "Short sine beep indicator for hovering buttons."
      }
    ],
    texts: [
      {
        id: 421,
        name: "txt_banner_header",
        content: "FLASH IS REBORN. EXPLORE NEW BOUNDARIES!",
        font: "Times New Roman",
        color: "#ffffff",
        align: "left"
      },
      {
        id: 422,
        name: "txt_button_label",
        content: "CLICK NOW",
        font: "Arial Bold",
        color: "#ffffff",
        align: "center"
      }
    ],
    scripts: [
      {
        id: 511,
        name: "BannerAnimation",
        tagType: "DoAction",
        bytecode: `// ActionScript 1/2 Assembly decompiled
0:  ActionPush     "txt_button_label"
5:  ActionPush     "LEARN MORE"
10: ActionSetMember
11: ActionPush     "btn_cta"
15: ActionGetVariable
16: ActionPush     "onRollOver"
20: ActionPush     function() {
      ActionPush   "snd_rollover"
      ActionCallMethod
    }
25: ActionSetMember`,
        decompiledAS: `// Frame 1 ActionScript 2.0 timeline assembly script
stop();

// Configure the Call to Action button triggers
btn_cta.onRollOver = function() {
    this.gotoAndPlay("hover");
    _root.playShortTickSound();
};

btn_cta.onRollOut = function() {
    this.gotoAndPlay("normal");
};

btn_cta.onRelease = function() {
    getURL("https://ai.studio/build", "_blank");
};

// Start a smooth fading loop animation
_root.onEnterFrame = function() {
    if (txt_banner_header._alpha < 100) {
        txt_banner_header._alpha += 4;
    }
};`
      }
    ]
  },
  {
    filename: "hifi_audio_visualizer.swf",
    displayName: "🎵 Hi-Fi Audio Widget (AVM3/AS3)",
    description: "An interactive sound mixer widget with real-time waveform filters, stereo knobs, sound triggers and custom visualizers reflecting synthetic WAV formats.",
    fileSizeLabel: "145.7 KB",
    header: {
      signature: "CWS",
      version: 15,
      fileLength: 149176,
      frameSize: { width: 500, height: 400 },
      frameRate: 30,
      frameCount: 500
    },
    vectorShapes: [
      {
        id: 121,
        width: 440,
        height: 220,
        paths: [
          { type: "move", x: 10, y: 10 },
          { type: "line", x: 430, y: 10 },
          { type: "line", x: 430, y: 210 },
          { type: "line", x: 10, y: 210 },
          { type: "line", x: 10, y: 10 }
        ],
        fillStyle: "#0f172a", // Dark background
        strokeStyle: "#10b981", // Emerald neon contour
        lineWidth: 3
      },
      {
        id: 122,
        width: 100,
        height: 100,
        paths: [
          { type: "move", x: 50, y: 5 },
          { type: "curve", cx: 95, cy: 5, x: 95, y: 50 },
          { type: "curve", cx: 95, cy: 95, x: 50, y: 95 },
          { type: "curve", cx: 5, cy: 95, x: 5, y: 50 },
          { type: "curve", cx: 5, cy: 5, x: 50, y: 5 }
        ],
        fillStyle: "#1e293b", // Slate gray outer dial
        strokeStyle: "#64748b",
        lineWidth: 2
      }
    ],
    images: [
      {
        id: 221,
        name: "img_visualizer_background.png",
        width: 400,
        height: 150,
        color: "#020617",
        type: "PNG",
        caption: "Pixelated equalizer grid background image for waveform graphics."
      }
    ],
    sounds: [
      {
        id: 321,
        name: "snd_electro_loop.wav",
        duration: 8.4,
        frequency: 220,
        type: "WAV",
        waveType: "square",
        caption: "Raw square oscillator bass loop sample compiled in sound block tags."
      },
      {
        id: 322,
        name: "snd_vocal_lead.wav",
        duration: 3.2,
        frequency: 330,
        type: "WAV",
        waveType: "sine",
        caption: "Melodic high lead synth sample representing processed inputs."
      }
    ],
    texts: [
      {
        id: 431,
        name: "txt_track_title",
        content: "ELECTRO OSCILLATOR CORE (SYNTH_101)",
        font: "Arial Bold / Black",
        color: "#10b981",
        align: "left"
      },
      {
        id: 432,
        name: "txt_equalizer_legend",
        content: "CH1   CH2   L-BAL   R-BAL   FREQ",
        font: "Monospace",
        color: "#475569",
        align: "center"
      }
    ],
    scripts: [
      {
        id: 521,
        name: "com.sound.EqualizerCore",
        tagType: "DoABC",
        bytecode: `// Bytecode block for EqualizerCore.as
method_info: EqualizerCore (param_count=0, return_type="void")
  instructions:
    0: getlocal_0
    1: pushscope
    2: getlocal_0
    3: constructsuper     (args_count=0)
    5: getlocal_0
    6: findpropstrict     QName(PackageNamespace("flash.media"), "SoundMixer")
    8: setproperty       QName(PackageNamespace(""), "mixer")
    10: getlocal_0
    11: findpropstrict     QName(PackageNamespace(""), "initVisualizer")
    13: callpropvoid      QName(PackageNamespace(""), "initVisualizer") (args_count=0)
    16: returnvoid

method_info: computeSpectrum (param_count=1, return_type="Array")
  instructions:
    0: getlocal_0
    1: pushscope
    2: findpropstrict     QName(PackageNamespace("flash.media"), "SoundMixer")
    4: getproperty       QName(PackageNamespace("flash.media"), "SoundMixer")
    6: findpropstrict     QName(PackageNamespace("flash.utils"), "ByteArray")
    8: constructprop     QName(PackageNamespace("flash.utils"), "ByteArray") (args_count=0)
    11: coerce           QName(PackageNamespace("flash.utils"), "ByteArray")
    13: setlocal_2
    14: getlocal_1         ; useFFT:Boolean
    15: getlocal_2
    16: callproperty     QName(PackageNamespace(""), "computeSpectrum") (args_count=2)
    19: returnvoid`,
        decompiledAS: `package com.sound {
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.media.SoundMixer;
    import flash.utils.ByteArray;
    import flash.media.SoundChannel;

    /**
     * Managed high-frequency audio visualizer processing tag and audio blocks.
     * Generates beautiful waveforms by calling computeSpectrum on SoundMixer.
     */
    public class EqualizerCore extends Sprite {
        private var spectrumData: ByteArray;
        private var visualizersList: Array;
        public var totalFilters: int = 5;

        public function EqualizerCore() {
            super();
            this.spectrumData = new ByteArray();
            this.visualizersList = [];
            
            this.addEventListener(Event.ENTER_FRAME, onSpectrumUpdate);
        }

        public function onSpectrumUpdate(event: Event): void {
            // Retrieve FFT amplitude from global SoundMixer
            try {
                spectrumData.clear();
                SoundMixer.computeSpectrum(spectrumData, true, 0);
                
                // Draw frequencies dynamically on widget canvas
                this.graphics.clear();
                this.graphics.lineStyle(2, 0x10b981); // Bright neon color
                this.graphics.moveTo(10, 110);
                
                for (var i: int = 0; i < 256; i += 8) {
                    var amp: Number = spectrumData.readFloat() * 80.0;
                    this.graphics.lineTo(10 + (i * 1.5), 110 - amp);
                }
            } catch (error: Error) {
                // Return fallback mock oscillations if speaker is system-muted
                drawMockFrequencies();
            }
        }

        private function drawMockFrequencies(): void {
            this.graphics.clear();
            this.graphics.lineStyle(2, 0x10b981);
            this.graphics.moveTo(10, 110);
            
            var time: Number = new Date().getTime() * 0.005;
            for (var col: int = 0; col < 256; col += 4) {
                var amplitude: Number = Math.sin(col * 0.05 + time) * Math.cos(col * 0.01) * 45;
                this.graphics.lineTo(10 + (col * 1.6), 110 - amplitude);
            }
        }
    }
}`
      }
    ]
  }
];

// Reconstruct tags and header dynamically based on the picked SampleSWF
export function createSWFFileFromSample(sample: SampleSWF): SWFFile {
  const fileTags: SWFTag[] = [];
  let currentOffset = 21; // typical initial tag offset after header

  // 1. SetBackgroundColor Tag (Type 9)
  const bgRed = sample.filename.includes("mario") ? 44 : sample.filename.includes("banner") ? 26 : 15;
  const bgGreen = sample.filename.includes("mario") ? 62 : sample.filename.includes("banner") ? 26 : 23;
  const bgBlue = sample.filename.includes("mario") ? 80 : sample.filename.includes("banner") ? 36 : 42;
  const bgHex = `#${bgRed.toString(16).padStart(2, "0")}${bgGreen.toString(16).padStart(2, "0")}${bgBlue.toString(16).padStart(2, "0")}`;

  fileTags.push({
    type: 9,
    typeName: "SetBackgroundColor",
    name: `Tag #1: SetBackgroundColor (${bgHex})`,
    length: 3,
    offset: currentOffset,
    content: new Uint8Array([bgRed, bgGreen, bgBlue]),
    properties: { red: bgRed, green: bgGreen, blue: bgBlue, hexColor: bgHex }
  });
  currentOffset += 5;

  // 2. FileAttributes Tag (Type 69)
  fileTags.push({
    type: 69,
    typeName: "FileAttributes",
    name: "Tag #2: FileAttributes",
    length: 8,
    offset: currentOffset,
    content: new Uint8Array([0x08 | 0x10, 0, 0, 0, 0, 0, 0, 0]), // has AS3 and Metadata flags
    properties: { useDirectBlit: false, useGPU: false, hasMetadata: true, actionScript3: true, useNetwork: false }
  });
  currentOffset += 10;

  // 3. FrameLabels
  sample.texts.forEach((txt, idx) => {
    const stringBytes = Array.from(txt.name).map(c => c.charCodeAt(0)).concat([0]);
    fileTags.push({
      type: 43,
      typeName: "FrameLabel",
      name: `Tag #${fileTags.length + 1}: FrameLabel ("${txt.name}")`,
      length: stringBytes.length,
      offset: currentOffset,
      content: new Uint8Array(stringBytes),
      properties: { label: txt.name }
    });
    currentOffset += 2 + stringBytes.length;
  });

  // 4. Sound Tags
  sample.sounds.forEach((sound) => {
    fileTags.push({
      type: 14,
      typeName: "DefineSound",
      name: `Tag #${fileTags.length + 1}: DefineSound [Sound ID: ${sound.id}]`,
      length: 120,
      offset: currentOffset,
      content: new Uint8Array(new Array(120).fill(0).map(() => Math.floor(Math.random() * 256))),
      properties: { soundId: sound.id, name: sound.name, frequency: sound.frequency, duration: sound.duration, waveType: sound.waveType }
    });
    currentOffset += 122;
  });

  // 5. Image Tags
  sample.images.forEach((img) => {
    fileTags.push({
      type: 36, // DefineBitsLossless2
      typeName: "DefineBitsLossless2",
      name: `Tag #${fileTags.length + 1}: DefineBitsLossless2 [Image ID: ${img.id}]`,
      length: 240,
      offset: currentOffset,
      content: new Uint8Array(new Array(240).fill(0).map(() => Math.floor(Math.random() * 256))),
      properties: { imageId: img.id, name: img.name, width: img.width, height: img.height, type: img.type }
    });
    currentOffset += 242;
  });

  // 6. Vector Shapes Tags
  sample.vectorShapes.forEach((shape) => {
    fileTags.push({
      type: 32, // DefineShape3
      typeName: "DefineShape3",
      name: `Tag #${fileTags.length + 1}: DefineShape3 [Shape ID: ${shape.id}]`,
      length: 180,
      offset: currentOffset,
      content: new Uint8Array(new Array(180).fill(0).map(() => Math.floor(Math.random() * 256))),
      properties: { shapeId: shape.id, width: shape.width, height: shape.height }
    });
    currentOffset += 182;
  });

  // 7. ActionScripts / ABC Bytecode Tags
  sample.scripts.forEach((script) => {
    const stringBytes = Array.from(script.name).map(c => c.charCodeAt(0)).concat([0]);
    const scriptBodyLength = 500;
    const bodyArr = new Uint8Array(4 + stringBytes.length + scriptBodyLength);
    bodyArr[0]=0x10; // flags

    fileTags.push({
      type: script.tagType === "DoABC" ? 82 : 12,
      typeName: script.tagType,
      name: `Tag #${fileTags.length + 1}: ${script.tagType} ("${script.name}")`,
      length: bodyArr.length,
      offset: currentOffset,
      content: bodyArr,
      properties: { abcName: script.name, flags: 0x10 },
      disassembly: script.bytecode
    });
    currentOffset += (bodyArr.length >= 0x3F ? 6 : 2) + bodyArr.length;
  });

  // 8. SymbolClass Tag (Type 76) Class bindings setup
  // maps sprites IDs to classes
  const symbolClassSize = 2 + (sample.scripts.length * 20);
  const symbolClassBytes = new Uint8Array(symbolClassSize);
  fileTags.push({
    type: 76,
    typeName: "SymbolClass",
    name: `Tag #${fileTags.length + 1}: SymbolClass [${sample.scripts.length} Class Bindings]`,
    length: symbolClassBytes.length,
    offset: currentOffset,
    content: symbolClassBytes,
    properties: {
      symbols: sample.scripts.map((s, idx) => ({ id: 50 + idx, name: s.name }))
    }
  });
  currentOffset += (symbolClassBytes.length >= 0x3F ? 6 : 2) + symbolClassBytes.length;

  // 9. End Tag (Type 0)
  fileTags.push({
    type: 0,
    typeName: "End",
    name: `Tag #${fileTags.length + 1}: End`,
    length: 0,
    offset: currentOffset,
    content: new Uint8Array([])
  });

  // Re-calculate file height and width
  const totalRawSize = currentOffset + 2;
  const header: SWFHeader = {
    signature: sample.header.signature,
    version: sample.header.version,
    fileLength: totalRawSize,
    frameSize: {
      xMin: 0,
      xMax: sample.header.frameSize.width * 20,
      yMin: 0,
      yMax: sample.header.frameSize.height * 20,
      width: sample.header.frameSize.width,
      height: sample.header.frameSize.height,
    },
    frameRate: sample.header.frameRate,
    frameCount: sample.header.frameCount
  };

  // Build a dummy uncompressed buffer corresponding to the structure
  const rawBytes = new Uint8Array(totalRawSize);
  rawBytes[0] = sample.header.signature.charCodeAt(0);
  rawBytes[1] = "W".charCodeAt(0);
  rawBytes[2] = "S".charCodeAt(0);
  rawBytes[3] = sample.header.version;
  rawBytes[4] = totalRawSize & 0xFF;
  rawBytes[5] = (totalRawSize >> 8) & 0xFF;
  rawBytes[6] = (totalRawSize >> 16) & 0xFF;
  rawBytes[7] = (totalRawSize >> 24) & 0xFF;

  return {
    filename: sample.filename,
    header,
    tags: fileTags,
    rawBytes
  };
}
