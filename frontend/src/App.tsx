import { useCallback, useEffect, useRef, useState } from "react";
import {
  Conversation, Message, deleteConversation, getConversation, listConversations, sendMessage,
} from "./api";
import { ConversationList } from "./components/ConversationList";
import { MessageBubble } from "./components/MessageBubble";
import { TypingIndicator } from "./components/TypingIndicator";
import { SummaryDialog } from "./components/SummaryDialog";
import { BotAvatar } from "./components/BotAvatar";
import { summaryPairs } from "./summary";
import {
  CarIcon, DownloadDocIcon, DropIcon, GlobeIcon, MenuIcon, PlaneIcon, PlusIcon, SendArrowIcon, SummaryIcon,
} from "./components/Icons";

const SUGGESTIONS = [
  { text: "יש לי נזילה בבית, איך מגישים תביעה?", icon: <DropIcon size={20} color="#FF5A23" /> },
  { text: "איך מבטלים ביטוח נסיעות לחו\"ל?", icon: <PlaneIcon size={20} color="#FF5A23" /> },
  { text: "מה עושים אחרי תאונת דרכים?", icon: <CarIcon size={20} color="#FF5A23" /> },
  { text: "איך מורידים העתק פוליסה של ביטוח דירה?", icon: <DownloadDocIcon size={20} color="#FF5A23" /> },
];

let localId = 0;
const nextId = () => `local-${++localId}`;

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // Bumped whenever the user switches conversation, so a reply that arrives later is not shown
  // in the wrong conversation (the server has already saved it in the one it belongs to).
  const viewRef = useRef(0);

  const refreshList = useCallback(() => {
    listConversations().then(setConversations).catch(() => setError("אין חיבור לשרת"));
  }, []);

  useEffect(() => { refreshList(); }, [refreshList]);
  // Braces matter: recent Chromium returns a promise from scrollIntoView, which React would treat as a cleanup.
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  const switchView = () => {
    viewRef.current += 1;
    setSending(false);
    setError(null);
    setSidebarOpen(false);
    return viewRef.current;
  };

  const openConversation = async (id: string) => {
    const view = switchView();
    setActiveId(id);
    setMessages([]);
    try {
      const loaded = await getConversation(id);
      if (viewRef.current === view) setMessages(loaded);
    } catch {
      if (viewRef.current === view) setError("לא הצלחתי לטעון את השיחה");
    }
  };

  const newConversation = () => {
    switchView();
    setActiveId(null);
    setMessages([]);
    inputRef.current?.focus();
  };

  const removeConversation = async (id: string) => {
    await deleteConversation(id).catch(() => undefined);
    if (id === activeId) newConversation();
    refreshList();
  };

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { id: nextId(), role: "user", content: message, sources: [] }]);
    setSending(true);
    const view = viewRef.current;
    try {
      const res = await sendMessage(message, activeId);
      if (viewRef.current !== view) return;  // user moved to another conversation meanwhile
      setActiveId(res.conversation_id);
      setMessages((m) => [...m, {
        id: nextId(), role: "assistant", content: res.answer, status: res.status, sources: res.sources,
      }]);
    } catch {
      if (viewRef.current === view) setError("השליחה נכשלה. בדקו שהשרת פועל ונסו שוב.");
    } finally {
      refreshList();
      if (viewRef.current === view) {
        setSending(false);
        inputRef.current?.focus();
      }
    }
  };

  /** Resend the question behind a failed ("busy") reply: drop that question and reply, then send again. */
  const retry = (errorIndex: number) => {
    const question = messages[errorIndex - 1];
    if (!question || question.role !== "user" || sending) return;
    setMessages((m) => m.filter((_, i) => i !== errorIndex && i !== errorIndex - 1));
    send(question.content);
  };

  const canSummarize = !sending && summaryPairs(messages).length > 0;

  return (
    <>
    <div className="app">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        open={sidebarOpen}
        onSelect={openConversation}
        onNew={newConversation}
        onDelete={removeConversation}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="chat">
        <header className="chat-header">
          <div className="header-main">
            <button className="icon-btn menu-btn" onClick={() => setSidebarOpen(true)} aria-label="פתיחת רשימת השיחות">
              <MenuIcon size={20} />
            </button>
            <img className="header-logo" src="/fnx-logo.png" alt="הפניקס" />
            <div className="header-titles">
              <h1>FNX AI Chatbot</h1>
              <p>הבוט החכם של הפניקס</p>
            </div>
          </div>
          <div className="header-actions">
            {canSummarize && (
              <button type="button" className="summary-open" onClick={() => setSummaryOpen(true)} aria-label="סיכום השיחה">
                <SummaryIcon size={18} /><span>סיכום השיחה</span>
              </button>
            )}
            <span className="source-badge"><GlobeIcon size={16} />מקור יחיד: fnx.co.il</span>
          </div>
          <button className="icon-btn menu-btn" onClick={newConversation} aria-label="שיחה חדשה">
            <PlusIcon size={20} />
          </button>
        </header>

        <section className="messages" aria-live="polite">
          {messages.length === 0 && (
            <div className="empty">
              <div className="empty-icon" aria-hidden="true"><BotAvatar size={84} /></div>
              <h2>איך אפשר לעזור?</h2>
              <p>שאלו על ביטוחים, תביעות, חיסכון, פנסיה או שירות. כל תשובה מגיעה עם קישור לעמוד באתר.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s.text} onClick={() => send(s.text)}>{s.icon}{s.text}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageBubble key={m.id} message={m} onRetry={m.status === "error" ? () => retry(i) : undefined} />
          ))}
          {canSummarize && (
            <div className="summary-hint">
              <span>רוצה לשמור או לשתף את השיחה?</span>
              <button type="button" onClick={() => setSummaryOpen(true)}>
                <SummaryIcon size={16} />סיכום השיחה
              </button>
            </div>
          )}
          {sending && <TypingIndicator />}
          {error && <div className="error-banner">{error}</div>}
          <div ref={endRef} />
        </section>

        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
          <div className="composer-inner">
            <label htmlFor="question" className="visually-hidden">שאלה לבוט</label>
            <textarea
              id="question"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
              }}
              placeholder="כתבו שאלה כאן…"
              rows={1}
              maxLength={1000}
              disabled={sending}
            />
            <button type="submit" className="send-btn" disabled={sending || !input.trim()}>
              שליחה<SendArrowIcon size={20} color="#FF5A23" strokeWidth={2.4} />
            </button>
          </div>
        </form>
        <p className="disclaimer">מידע כללי מתוך אתר הפניקס בלבד. אינו ייעוץ אישי ואינו מחליף את תנאי הפוליסה.</p>
      </main>
    </div>
    {/* Outside .app so print can hide the app and keep only the summary. */}
    {summaryOpen && <SummaryDialog messages={messages} onClose={() => setSummaryOpen(false)} />}
    </>
  );
}
