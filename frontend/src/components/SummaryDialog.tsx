import { useEffect, useMemo, useRef, useState } from "react";
import { Message } from "../api";
import { buildSummary, SUMMARY_TITLE } from "../summary";
import { CloseIcon, CopyIcon, PrintIcon, ShareIcon, WhatsAppIcon } from "./Icons";

// wa.me links get unreliable beyond a few thousand characters; long summaries are cut with a note.
const WHATSAPP_MAX_CHARS = 3000;

interface Props {
  messages: Message[];
  onClose: () => void;
}

export function SummaryDialog({ messages, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [copied, setCopied] = useState(false);
  const summary = useMemo(() => buildSummary(messages), [messages]);
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  useEffect(() => {
    dialogRef.current?.showModal();  // native modal: focus trap and Esc come for free
  }, []);

  const whatsappText = summary.length > WHATSAPP_MAX_CHARS
    ? `${summary.slice(0, WHATSAPP_MAX_CHARS)}…\n(הסיכום קוצר)`
    : summary;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const share = async () => {
    try {
      await navigator.share({ title: SUMMARY_TITLE, text: summary });
    } catch {
      // user dismissed the share sheet
    }
  };

  return (
    <dialog ref={dialogRef} className="summary-dialog" aria-labelledby="summary-title" onClose={onClose}>
      <div className="summary-head">
        <h2 id="summary-title">סיכום השיחה</h2>
        <button type="button" className="icon-btn summary-close" onClick={() => dialogRef.current?.close()} aria-label="סגירה">
          <CloseIcon size={20} />
        </button>
      </div>
      <p className="summary-note">הסיכום כולל את השאלות, את התשובות ואת קישורי המקור מהשיחה, בדיוק כפי שנענו.</p>
      <pre className="summary-text">{summary}</pre>
      <div className="summary-actions">
        <button type="button" className="summary-btn primary" onClick={copy}>
          <CopyIcon size={18} />{copied ? "הועתק ✓" : "העתקה"}
        </button>
        <a className="summary-btn" href={`https://wa.me/?text=${encodeURIComponent(whatsappText)}`}
          target="_blank" rel="noopener noreferrer">
          <WhatsAppIcon size={18} />וואטסאפ
        </a>
        {canShare && (
          <button type="button" className="summary-btn" onClick={share}><ShareIcon size={18} />שיתוף</button>
        )}
        <button type="button" className="summary-btn" onClick={() => window.print()}>
          <PrintIcon size={18} />הדפסה
        </button>
      </div>
    </dialog>
  );
}
