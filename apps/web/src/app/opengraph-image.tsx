import { ImageResponse } from "next/og";

export const contentType = "image/png";
export const size = {
  width: 1200,
  height: 630,
};
export const alt = "Verirule";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "64px 80px",
          backgroundColor: "#F1F9F4",
          backgroundImage:
            "repeating-linear-gradient(0deg, rgba(18,83,52,0.08) 0 1px, transparent 1px 30px), repeating-linear-gradient(90deg, rgba(18,83,52,0.08) 0 1px, transparent 1px 30px)",
          color: "#113D2A",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 650 }}>
          <div
            style={{
              fontSize: 24,
              letterSpacing: 6,
              fontWeight: 700,
              textTransform: "uppercase",
              color: "#0B7A3F",
            }}
          >
            Verirule
          </div>
          <div style={{ fontSize: 68, lineHeight: 1.05, fontWeight: 800 }}>
            Regulatory workflows with audit-ready evidence
          </div>
          <div style={{ fontSize: 32, color: "#245A41" }}>
            Unified monitoring, tasks, and controls.
          </div>
        </div>

        <div
          style={{
            width: 360,
            height: 360,
            borderRadius: 48,
            border: "6px solid #B7D8C4",
            backgroundColor: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" style={{ width: 280, height: 280 }} fill="none">
            <rect x="8" y="8" width="240" height="240" rx="56" fill="#E8F7EE" />
            <defs>
              <clipPath id="vrShieldClipOG2">
                <path d="M128 28C151 44 177 51 208 58V124C208 171 179 210 128 230C77 210 48 171 48 124V58C79 51 105 44 128 28Z" />
              </clipPath>
            </defs>
            <g clipPath="url(#vrShieldClipOG2)">
              <rect x="0" y="0" width="128" height="256" fill="#0B7A3F" />
              <rect x="128" y="0" width="128" height="256" fill="#16A34A" />
            </g>
            <path
              d="M128 28C151 44 177 51 208 58V124C208 171 179 210 128 230C77 210 48 171 48 124V58C79 51 105 44 128 28Z"
              stroke="#0F5132"
              strokeWidth="8"
            />
            <path d="M84 139L113 110L137 133L192 78" stroke="#FFFFFF" strokeWidth="20" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    ),
    size,
  );
}