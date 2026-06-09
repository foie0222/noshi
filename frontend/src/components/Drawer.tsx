import { type ReactNode, useEffect, useRef } from "react";
import { Icon } from "./Icon";

/**
 * Drawer — 左から出るオーバーレイ式メニュー（#3）。
 * スクリム/閉じるボタン/Esc で閉じ、開いている間は本文のスクロールをロックし、
 * フォーカスをパネル内に閉じ込める（フォーカストラップ）。
 */
export function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  // 開いている間は背景スクロールをロックする。
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // 開いたらパネル内の最初の操作要素へフォーカス（フォーカストラップの起点）。
  useEffect(() => {
    if (open) panelRef.current?.querySelector<HTMLElement>("button, a, [tabindex]")?.focus();
  }, [open]);

  if (!open) return null;

  // Tab がパネル外へ出ないように先頭/末尾でループさせる（簡易フォーカストラップ）。
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
      return;
    }
    if (e.key !== "Tab") return;
    const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
      'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    // biome-ignore lint/a11y/useKeyWithClickEvents: スクリムはマウス用の補助。Esc/閉じるボタンでキーボード操作可能。
    <div className="drawer-scrim" data-testid="drawer-scrim" onClick={onClose}>
      {/** biome-ignore lint/a11y/noStaticElementInteractions: ダイアログのキー処理。フォーカスはパネル内に閉じ込める。 */}
      <div
        ref={panelRef}
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onKeyDown={onKeyDown}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-head">
          <span className="drawer-title">{title}</span>
          <button type="button" className="drawer-close" aria-label="閉じる" onClick={onClose}>
            <Icon name="close" size={22} />
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </div>
  );
}
