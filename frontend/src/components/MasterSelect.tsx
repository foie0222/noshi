import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

/**
 * MasterSelect — マスタ（システム既定＋世帯独自）から1つ選ぶ汎用フィールド（#1, #37）。
 * 続柄・用途など `noun`（例「続柄」「用途」）で文言を切り替えて共用する。
 * 「＋ 新しい{noun}を追加」でその場で追加でき、世帯独自の項目は行を左スワイプ（タッチ）
 * または行ホバー（マウス）で現れる削除ボタンから消せる（既定は削除不可）。
 * 選択肢に無い既存値（自由入力/AI抽出/削除済み）も現在値として表示する（後方互換）。
 */
export function MasterSelect({
  value,
  options,
  defaults,
  noun,
  onChange,
  onAdd,
  onDelete,
  id,
}: {
  value: string;
  options: string[];
  defaults: string[];
  noun: string;
  onChange: (v: string) => void;
  onAdd: (name: string) => void;
  onDelete: (name: string) => void;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [swiped, setSwiped] = useState<string | null>(null);
  const startX = useRef(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  // 現在値が選択肢に無ければ先頭に足す（自由入力/AI抽出/削除済みマスタを保持）。
  const opts = value && !options.includes(value) ? [value, ...options] : options;
  const isCustom = (o: string) => options.includes(o) && !defaults.includes(o);

  // パネル外クリックで閉じる。
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSwiped(null);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const select = (v: string) => {
    onChange(v);
    setOpen(false);
    setSwiped(null);
  };

  if (adding) {
    const commit = () => {
      const v = name.trim();
      if (v) onAdd(v);
      setName("");
      setAdding(false);
    };
    return (
      <div style={{ display: "flex", gap: 8 }}>
        <input
          id={id}
          className="input"
          style={{ flex: 1 }}
          placeholder={`新しい${noun}`}
          value={name}
          aria-label={`新しい${noun}`}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          type="button"
          className="btn primary"
          style={{ width: "auto", padding: "0 16px" }}
          onClick={commit}
        >
          追加
        </button>
        <button
          type="button"
          className="btn ghost"
          style={{ width: "auto", padding: "0 14px" }}
          onClick={() => {
            setName("");
            setAdding(false);
          }}
        >
          やめる
        </button>
      </div>
    );
  }

  return (
    <div
      className="rel"
      ref={wrapRef}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          setOpen(false);
          setSwiped(null);
        }
      }}
    >
      <button
        type="button"
        id={id}
        className="select rel-trigger"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={value ? undefined : "rel-placeholder"}>{value || "未選択"}</span>
      </button>
      <span className="select-chevron">
        <Icon name="chevronDown" size={20} />
      </span>

      {open && (
        <div className="rel-panel" role="listbox" aria-label={noun}>
          <button type="button" role="option" className="rel-opt-label" onClick={() => select("")}>
            未選択
          </button>
          {opts.map((o) =>
            isCustom(o) ? (
              <div
                key={o}
                className="rel-opt"
                onTouchStart={(e) => {
                  startX.current = e.touches[0].clientX;
                }}
                onTouchEnd={(e) => {
                  const dx = e.changedTouches[0].clientX - startX.current;
                  if (dx < -30) setSwiped(o);
                  else if (dx > 30) setSwiped(null);
                }}
              >
                <button
                  type="button"
                  role="option"
                  className={`rel-opt-label${swiped === o ? " swiped" : ""}`}
                  onClick={() => select(o)}
                >
                  {o}
                </button>
                <button
                  type="button"
                  className="rel-opt-del"
                  aria-label={`${o} を削除`}
                  onClick={() => {
                    onDelete(o);
                    setSwiped(null);
                  }}
                >
                  <Icon name="trash" size={18} color="#fff" />
                </button>
              </div>
            ) : (
              <button
                key={o}
                type="button"
                role="option"
                className="rel-opt-label"
                onClick={() => select(o)}
              >
                {o}
              </button>
            ),
          )}
          <button
            type="button"
            role="option"
            className="rel-opt-label rel-add"
            onClick={() => {
              setOpen(false);
              setAdding(true);
            }}
          >
            ＋ 新しい{noun}を追加
          </button>
        </div>
      )}
    </div>
  );
}
