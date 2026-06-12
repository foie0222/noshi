import type { CSSProperties } from "react";

/**
 * Logo — noshi のし ブランドマーク。朱赤の丸印「の」＋ 明朝の「し」。
 * variant: full（印＋文字）/ mark（印のみ）/ word（文字のみ）。
 * onDark でも印は朱赤のまま。デザインシステムの Logo を TS に移植。
 *
 * 印が既に「の」を担うので、隣の文字は「し」だけ（続けて「のし」と読める）。
 * 単体の `word` だけは可読性のため「のし」を綴る。
 */
export function Logo({
  variant = "full",
  size = 32,
  onDark = false,
  style,
}: {
  variant?: "full" | "mark" | "word";
  size?: number;
  onDark?: boolean;
  style?: CSSProperties;
}) {
  const sealSize = Math.round(size * 1.15);
  const wordColor = onDark ? "var(--color-accent)" : "var(--color-accent)";

  const seal = (
    <span
      data-part="seal"
      style={{
        width: sealSize,
        height: sealSize,
        // 印の形は favicon と同じ角丸比率（22%）。デザインシステム Logo に合わせる（#163）
        borderRadius: Math.round(sealSize * 0.22),
        background: "var(--color-accent)",
        color: "#fff",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-display)",
        fontWeight: "var(--fw-heavy)",
        fontSize: sealSize * 0.55,
        lineHeight: 1, // 継承の行高だと「の」が下にズレる（#163）
        flex: "none",
      }}
    >
      {/* 明朝の「の」は字面が下寄りなので、視覚的中心に少し持ち上げる（デザインシステム準拠） */}
      <span style={{ display: "block", transform: "translateY(-0.03em)" }}>の</span>
    </span>
  );

  const word = (
    <span
      data-part="word"
      style={{
        fontFamily: "var(--font-display)",
        fontWeight: "var(--fw-heavy)",
        fontSize: size,
        color: wordColor,
        letterSpacing: "0.04em",
        lineHeight: 1,
      }}
    >
      {variant === "word" ? "のし" : "し"}
    </span>
  );

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: Math.round(size * 0.32),
        ...style,
      }}
    >
      {variant !== "word" && seal}
      {variant !== "mark" && word}
    </span>
  );
}
