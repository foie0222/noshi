import { useEffect, useRef, useState } from "react";
import type { Party } from "../types";
import { Icon } from "./Icon";
import { MasterSelect } from "./MasterSelect";

/** 相手（人）を選ぶ。同名は続柄で区別表示。「新しい相手を追加」も可能（#47）。 */
function label(p: Party): string {
  return p.relationship ? `${p.name}（${p.relationship}）` : p.name;
}

export function PartySelect({
  value,
  parties,
  onChange,
  onAdd,
  suggestedName = "",
  relOptions,
  relDefaults,
  onAddRelationship,
  onDeleteRelationship,
  id,
}: {
  value: string;
  parties: Party[];
  onChange: (partyId: string) => void;
  onAdd: (name: string, relationship: string) => void;
  suggestedName?: string;
  relOptions: string[];
  relDefaults: string[];
  onAddRelationship: (name: string, select: (v: string) => void) => void;
  onDeleteRelationship: (name: string) => void;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [rel, setRel] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  const selected = parties.find((p) => p.id === value);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  if (adding) {
    const commit = () => {
      const v = name.trim();
      if (v) onAdd(v, rel.trim());
      setName("");
      setRel("");
      setAdding(false);
    };
    return (
      <div ref={wrapRef} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          id={id}
          className="input"
          placeholder="相手のお名前"
          aria-label="相手のお名前"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <MasterSelect
          noun="続柄"
          value={rel}
          options={relOptions}
          defaults={relDefaults}
          onChange={setRel}
          onAdd={(n) => onAddRelationship(n, setRel)}
          onDelete={onDeleteRelationship}
        />
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="btn primary" style={{ flex: 1 }} onClick={commit}>
            この相手で追加
          </button>
          <button
            type="button"
            className="btn ghost"
            style={{ flex: 1 }}
            onClick={() => {
              setName("");
              setRel("");
              setAdding(false);
            }}
          >
            やめる
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rel" ref={wrapRef}>
      <button
        type="button"
        id={id}
        className="select rel-trigger"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={selected ? undefined : "rel-placeholder"}>
          {selected ? label(selected) : "相手を選ぶ"}
        </span>
      </button>
      <span className="select-chevron">
        <Icon name="chevronDown" size={20} />
      </span>
      {open && (
        <div className="rel-panel" role="listbox" aria-label="相手">
          {parties.length === 0 && (
            <div className="muted" style={{ padding: "10px 14px" }}>
              まだ相手がいません。下から追加してください。
            </div>
          )}
          {parties.map((p) => (
            <button
              key={p.id}
              type="button"
              role="option"
              className="rel-opt-label"
              onClick={() => {
                onChange(p.id);
                setOpen(false);
              }}
            >
              {label(p)}
            </button>
          ))}
          <button
            type="button"
            role="option"
            className="rel-opt-label rel-add"
            onClick={() => {
              setName(suggestedName);
              setOpen(false);
              setAdding(true);
            }}
          >
            ＋ 新しい相手を追加
          </button>
        </div>
      )}
    </div>
  );
}
