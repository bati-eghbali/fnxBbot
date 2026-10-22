import { Message, Status } from "../api";
import { BotAvatar } from "./BotAvatar";
import {
  BlockIcon, BulbIcon, ClockIcon, DocIcon, ExternalIcon, PersonIcon, PhoneIcon, SearchOffIcon,
} from "./Icons";

const STATUS_TAG: Partial<Record<Status, { label: string; icon: JSX.Element }>> = {
  not_found: { label: "לא מופיע באתר", icon: <SearchOffIcon size={14} /> },
  refer: { label: "הפניה לשירות הלקוחות", icon: <PhoneIcon size={14} /> },
  personal: { label: "מידע אישי נבדק בשירות הלקוחות", icon: <PersonIcon size={14} /> },
  advice: { label: "ללא ייעוץ אישי", icon: <BulbIcon size={14} /> },
  off_topic: { label: "מחוץ לתחום", icon: <BlockIcon size={14} /> },
  error: { label: "עמוס כרגע", icon: <ClockIcon size={14} /> },
};

const CONTACT_URL = "https://www.fnx.co.il/customer-service/contact-us/";

/** Render the model's **bold** markers as <strong>; everything else stays plain text (no HTML injection). */
function formatText(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  );
}

interface Props {
  message: Message;
  /** Shown on error replies: resends the question that failed. */
  onRetry?: () => void;
}

export function MessageBubble({ message, onRetry }: Props) {
  if (message.role === "user") {
    return (
      <div className="row row-user">
        <p className="bubble bubble-user content">{message.content}</p>
      </div>
    );
  }

  const tag = message.status ? STATUS_TAG[message.status] : undefined;
  const grounded = message.status === "answered" || message.status === "personal";
  return (
    <div className="row row-bot">
      <div className="avatar" aria-hidden="true"><BotAvatar size={34} /></div>
      <div className={`bubble bubble-bot status-${message.status ?? "answered"}`}>
        {tag && <span className="status-tag">{tag.icon}{tag.label}</span>}
        <p className="content">{formatText(message.content)}</p>
        {message.sources.length > 0 && (
          <div className="sources">
            <span className="sources-label">{grounded ? "המקור" : "לפרטים"}</span>
            {message.sources.map((s) => (
              <a key={s.url} className="source-card" href={s.url} target="_blank" rel="noopener noreferrer">
                {s.url === CONTACT_URL ? <PhoneIcon size={20} color="#FF5A23" /> : <DocIcon size={20} color="#FF5A23" />}
                <span className="source-text">
                  <span className="source-title">{s.title}</span>
                  <span className="source-url">{s.url.replace(/^https:\/\/www\./, "").replace(/\/$/, "")}</span>
                </span>
                <ExternalIcon size={16} color="#5A5F7A" />
              </a>
            ))}
          </div>
        )}
        {message.status === "error" && onRetry && (
          <button type="button" className="retry-btn" onClick={onRetry}>לנסות שוב</button>
        )}
      </div>
    </div>
  );
}
