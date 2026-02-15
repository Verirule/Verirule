/* eslint-disable @next/next/no-img-element */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { ImageResponse } from "next/og";

export const contentType = "image/png";
export const size = {
  width: 1200,
  height: 630,
};
export const alt = "Verirule";

const iconSvg = readFileSync(join(process.cwd(), "public", "brand", "icon.svg"), "utf8");
const iconDataUrl = `data:image/svg+xml;base64,${Buffer.from(iconSvg).toString("base64")}`;

export default function TwitterImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "56px 72px",
          background: "linear-gradient(140deg, #edf8f2 0%, #ffffff 52%, #dff4e9 100%)",
          color: "#0f3d2a",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 680 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <img src={iconDataUrl} alt="Verirule icon" width={74} height={74} />
            <div
              style={{
                fontSize: 22,
                letterSpacing: 4,
                fontWeight: 700,
                textTransform: "uppercase",
                color: "#0c7a3f",
              }}
            >
              Verirule
            </div>
          </div>
          <div style={{ fontSize: 62, lineHeight: 1.04, fontWeight: 800 }}>
            Regulatory operations with clear, audit-ready evidence.
          </div>
          <div style={{ fontSize: 30, color: "#1a5a3e" }}>
            Monitor updates. Route action. Preserve traceability.
          </div>
        </div>

        <div
          style={{
            width: 360,
            height: 360,
            borderRadius: 44,
            border: "5px solid #afd7be",
            backgroundColor: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 14px 40px rgba(15, 61, 42, 0.18)",
            flexShrink: 0,
          }}
        >
          <img src={iconDataUrl} alt="Verirule icon" width={280} height={280} />
        </div>
      </div>
    ),
    size,
  );
}
