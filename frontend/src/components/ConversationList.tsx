import { Conversation } from "../api";
import { PlusIcon, ShieldIcon } from "./Icons";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}

/** Split into "today" and "earlier" by the server's updated_at (list arrives newest first). */
function groupByDay(conversations: Conversation[]) {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const today = conversations.filter((c) => new Date(c.updated_at) >= startOfToday);
  const earlier = conversations.filter((c) => new Date(c.updated_at) < startOfToday);
  return [
    { label: "היום", items: today },
    { label: "קודם", items: earlier },
  ].filter((g) => g.items.length > 0);
}

export function ConversationList({ conversations, activeId, open, onSelect, onNew, onDelete, onClose }: Props) {
  return (
    <>
      {open && <div className="backdrop" onClick={onClose} />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <img className="brand-logo" src="/fnx-logo.png" alt="הפניקס" />
        </div>

        <button className="new-chat" onClick={onNew}><PlusIcon strokeWidth={2.2} />שיחה חדשה</button>

        <nav className="conv-list" aria-label="שיחות קודמות">
          {conversations.length === 0 && <p className="muted">עדיין אין שיחות</p>}
          {groupByDay(conversations).map((group) => (
            <div key={group.label}>
              <div className="conv-group">{group.label}</div>
              {group.items.map((c) => (
                <div key={c.id} className={`conv-item ${c.id === activeId ? "active" : ""}`}>
                  <button className="conv-title" onClick={() => onSelect(c.id)} title={c.title}>
                    {c.id === activeId && <span className="active-dot" aria-hidden="true" />}
                    <span>{c.title || "שיחה"}</span>
                  </button>
                  <button className="icon-btn conv-delete" onClick={() => onDelete(c.id)} aria-label="מחיקת שיחה">✕</button>
                </div>
              ))}
            </div>
          ))}
        </nav>

        <div className="trust-card">
          <strong><ShieldIcon color="#FF5A23" />לא ממציא תשובות</strong>
          <p>כל תשובה מבוססת על עמוד באתר הפניקס ומצרפת אליו קישור. מה שלא כתוב באתר - הבוט אומר זאת ומפנה לשירות הלקוחות.</p>
        </div>
      </aside>
    </>
  );
}
