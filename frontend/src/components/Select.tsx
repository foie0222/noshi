import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

export interface SelectOption {
  value: string;
  label: string;
}

/**
 * Select — デザインシステム準拠の自前ドロップダウン（固定選択肢用）。
 * ネイティブ <select> の OS 依存パネル（青ハイライト等）を避け、用途・続柄の
 * MasterSelect と同じ rel-panel スタイルで描画する。並べ替えなど追加・削除の
 * いらない単純な選択に使う。compact はトリガーを枠なしにしパネルを右寄せにする。
 */
export function Select({
  value,
  options,
  onChange,
  ariaLabel,
  id,
  compact = false,
}: {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  ariaLabel: string;
  id?: string;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const current = options.find((o) => o.value === value);

  // パネル外クリックで閉じる。
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: ラッパの Esc キー処理。実操作は内部の combobox/option ボタン。
    <div
      className={`rel${compact ? " rel-compact" : ""}`}
      ref={wrapRef}
      onKeyDown={(e) => {
        if (e.key === "Escape") setOpen(false);
      }}
    >
      <button
        type="button"
        id={id}
        className={compact ? "sort-trigger" : "select rel-trigger"}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{current?.label ?? ""}</span>
        {compact && <Icon name="chevronDown" size={16} />}
      </button>
      {!compact && (
        <span className="select-chevron">
          <Icon name="chevronDown" size={20} />
        </span>
      )}
      {open && (
        <div className="rel-panel" role="listbox" aria-label={ariaLabel}>
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              role="option"
              aria-selected={o.value === value}
              className={`rel-opt-label${o.value === value ? " on" : ""}`}
              onClick={() => {
                onChange(o.value);
                setOpen(false);
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
