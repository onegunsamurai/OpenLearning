import { ImageResponse } from "next/og";

export const ogAlt = "OpenLearning — AI-Powered Learning Engineer";
export const ogSize = { width: 1200, height: 630 };
export const ogContentType = "image/png";

export async function generateOGImage(): Promise<ImageResponse> {
  const syneBold = await fetch(
    new URL(
      "https://fonts.gstatic.com/s/syne/v22/8vIS7w4qzmVxsWxjBZRjr0FKM_0KuT6kR47NCV5Z.woff",
    ),
  ).then((res) => res.arrayBuffer());

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0a0b0d",
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          position: "relative",
        }}
      >
        <div
          style={{
            display: "flex",
            fontSize: 72,
            fontFamily: "Syne",
            fontWeight: 700,
          }}
        >
          <span style={{ color: "#00d4ff" }}>Open</span>
          <span style={{ color: "#e4e4e7" }}>Learning</span>
        </div>

        <div
          style={{
            display: "flex",
            fontSize: 28,
            color: "#71717a",
            marginTop: 16,
            fontFamily: "Syne",
          }}
        >
          AI-Powered Learning Engineer
        </div>

        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 6,
            background: "linear-gradient(90deg, #00d4ff, #a855f7)",
          }}
        />
      </div>
    ),
    {
      ...ogSize,
      fonts: [
        {
          name: "Syne",
          data: syneBold,
          style: "normal",
          weight: 700,
        },
      ],
    },
  );
}
