import { useState } from "react";
import { Icon } from "./Icon";

/**
 * RelationshipField — 続柄の選択フィールド（#1）。
 * マスタ（システム既定＋世帯独自）から選択でき、「＋ 新しい続柄を追加」で
 * 世帯独自の続柄をその場で追加できる。選択肢に無い既存値（自由入力/AI抽出）も
 * 現在値として表示する（後方互換）。
 */
export function RelationshipField({
  value,
  options,
  onChange,
  onAdd,
  id,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
  onAdd: (name: string) => void;
  id?: string;
}) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");

  // 現在値が選択肢に無ければ先頭に足す（自由入力データ／AI抽出のマッピング外を保持）。
  const opts = value && !options.includes(value) ? [value, ...options] : options;

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
          placeholder="新しい続柄"
          value={name}
          aria-label="新しい続柄"
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
    <div className="select-wrap">
      <select
        id={id}
        className="select"
        value={value}
        onChange={(e) => {
          if (e.target.value === "__add__") setAdding(true);
          else onChange(e.target.value);
        }}
      >
        <option value="">未選択</option>
        {opts.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
        <option value="__add__">＋ 新しい続柄を追加</option>
      </select>
      <span className="select-chevron">
        <Icon name="chevronDown" size={20} />
      </span>
    </div>
  );
}
