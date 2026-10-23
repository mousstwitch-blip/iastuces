import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Fonts are bundled locally (Inter Tight & JetBrains Mono, SIL OFL, from @fontsource)
// so rendering never depends on a font CDN.
export const display = "Inter Tight";
export const mono = "JetBrains Mono";

for (const weight of ["500", "700", "800", "900"]) {
  loadFont({ family: display, url: staticFile(`fonts/inter-tight-latin-${weight}-normal.woff2`), weight });
}
for (const weight of ["400", "500", "700"]) {
  loadFont({ family: mono, url: staticFile(`fonts/jetbrains-mono-latin-${weight}-normal.woff2`), weight });
}

export const C = {
  night: "#05080D",
  navy: "#0A1322",
  deep: "#0E1B2D",
  steel: "#9FB4C7",
  steelDim: "#4E6276",
  paper: "#EEF2F6",
  amber: "#FFB547",
  red: "#FF4D3D",
  phosphor: "#63FFB4",
  phosphorDim: "#1C6E4C",
  ocean: "#0B2236",
};

// TikTok UI overlaps the top bar, the right-hand buttons and the bottom caption.
export const SAFE = { top: 220, side: 80, right: 150, bottom: 470 };
