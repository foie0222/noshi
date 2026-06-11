import { LEGAL_DOCS, type LegalDocKey } from "../legal";

/**
 * LegalView — 法的文書（プライバシーポリシー／利用規約／運営者情報）の表示（#115-117）。
 * 読みやすさ優先のテキストレイアウト。本文は段落ごとに表示する。
 */
export function LegalView({ docKey }: { docKey: LegalDocKey }) {
  const doc = LEGAL_DOCS[docKey];
  return (
    <article className="legal">
      <h1 className="legal-title">{doc.title}</h1>
      <p className="legal-updated">最終更新: {doc.updated}</p>
      {doc.intro && <p className="legal-body">{doc.intro}</p>}
      {doc.sections.map((s) => (
        <section key={s.heading ?? s.body[0]} className="legal-section">
          {s.heading && <h2 className="legal-heading">{s.heading}</h2>}
          {s.body.map((p) => (
            <p key={p} className="legal-body">
              {p}
            </p>
          ))}
        </section>
      ))}
    </article>
  );
}
