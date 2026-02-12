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
          padding: "72px 84px",
          backgroundColor: "#03111f",
          backgroundImage:
            "radial-gradient(1000px 500px at 20% 35%, rgba(14,120,232,0.35), transparent 70%), radial-gradient(900px 500px at 85% 30%, rgba(69,184,76,0.35), transparent 70%)",
          color: "#e5eef9",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 620 }}>
          <div
            style={{
              fontSize: 26,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: "#6aa8ff",
            }}
          >
            Verirule
          </div>
          <div style={{ fontSize: 66, lineHeight: 1.05, fontWeight: 700 }}>
            Regulatory workflows with audit-ready evidence
          </div>
          <div style={{ fontSize: 30, color: "#a8c5e8" }}>
            Unified monitoring, tasks, and controls.
          </div>
        </div>

        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 256 256"
          style={{ width: 300, height: 300, flexShrink: 0 }}
          fill="none"
        >
          <defs>
            <linearGradient id="vrBlueOG" x1="38" y1="46" x2="152" y2="230" gradientUnits="userSpaceOnUse">
              <stop stopColor="#19A6FF" />
              <stop offset=".55" stopColor="#0C67CF" />
              <stop offset="1" stopColor="#003B98" />
            </linearGradient>
            <linearGradient id="vrGreenOG" x1="124" y1="44" x2="226" y2="230" gradientUnits="userSpaceOnUse">
              <stop stopColor="#76DD3C" />
              <stop offset=".55" stopColor="#22A849" />
              <stop offset="1" stopColor="#00773C" />
            </linearGradient>
            <linearGradient id="vrCircuitOG" x1="132" y1="143" x2="206" y2="50" gradientUnits="userSpaceOnUse">
              <stop stopColor="#28B24A" />
              <stop offset="1" stopColor="#62D955" />
            </linearGradient>
            <linearGradient id="vrBlueBevelOG" x1="75" y1="120" x2="138" y2="175" gradientUnits="userSpaceOnUse">
              <stop stopColor="#0B67C7" />
              <stop offset="1" stopColor="#073C94" />
            </linearGradient>
            <linearGradient id="vrGreenBevelOG" x1="132" y1="143" x2="210" y2="188" gradientUnits="userSpaceOnUse">
              <stop stopColor="#18A94A" />
              <stop offset="1" stopColor="#086B37" />
            </linearGradient>
            <clipPath id="vrShieldClipOG">
              <path d="M128 18C159 36 189 43 214 48V136C214 184 184 218 128 238C72 218 42 184 42 136V48C67 43 97 36 128 18Z" />
            </clipPath>
            <mask id="vrShieldMaskOG" maskUnits="userSpaceOnUse" x="0" y="0" width="256" height="256">
              <rect width="256" height="256" fill="#fff" />
              <path
                d="M82 144 108 119 133 143 206 70"
                stroke="#000"
                strokeWidth="22"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </mask>
          </defs>

          <g clipPath="url(#vrShieldClipOG)" mask="url(#vrShieldMaskOG)">
            <rect x="0" y="0" width="128" height="256" fill="url(#vrBlueOG)" />
            <rect x="128" y="0" width="128" height="256" fill="url(#vrGreenOG)" />
          </g>

          <g clipPath="url(#vrShieldClipOG)">
            <path d="M83 143 107 120 132 143V168L106 142 90 158 73 142Z" fill="url(#vrBlueBevelOG)" opacity=".95" />
            <path d="M132 143 206 70V98L132 171Z" fill="url(#vrGreenBevelOG)" opacity=".92" />
          </g>

          <path
            d="M128 18C159 36 189 43 214 48V136C214 184 184 218 128 238C72 218 42 184 42 136V48C67 43 97 36 128 18Z"
            stroke="#032534"
            strokeOpacity=".45"
            strokeWidth="1.4"
          />
          <path d="M132 143 163 112V86" stroke="url(#vrCircuitOG)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M132 143 182 93V68" stroke="url(#vrCircuitOG)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M132 143 206 69V44" stroke="url(#vrCircuitOG)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="163" cy="79" r="8" fill="none" stroke="#67DD58" strokeWidth="4" />
          <circle cx="182" cy="61" r="8" fill="none" stroke="#67DD58" strokeWidth="4" />
          <circle cx="206" cy="37" r="8" fill="none" stroke="#67DD58" strokeWidth="4" />
          <circle cx="163" cy="79" r="3.6" fill="#81EA6A" />
          <circle cx="182" cy="61" r="3.6" fill="#81EA6A" />
          <circle cx="206" cy="37" r="3.6" fill="#81EA6A" />
        </svg>
      </div>
    ),
    size,
  );
}
