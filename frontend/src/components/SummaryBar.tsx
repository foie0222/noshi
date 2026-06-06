import { yen, diffLabel } from "../lib/format";

export function SummaryBar({
  received,
  given,
  diff,
}: {
  received: number;
  given: number;
  diff: number;
}) {
  return (
    <div className="summary">
      <div className="s">
        <span className="label">もらった</span>
        <span className="amount">{yen(received)}</span>
      </div>
      <div className="s">
        <span className="label">あげた</span>
        <span className="amount">{yen(given)}</span>
      </div>
      <div className="s">
        <span className="label">差分</span>
        <span className="amount pos">{diffLabel(diff)}</span>
      </div>
    </div>
  );
}
