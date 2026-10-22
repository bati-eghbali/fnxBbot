import { BotAvatar } from "./BotAvatar";

export function TypingIndicator() {
  return (
    <div className="row row-bot">
      <div className="avatar" aria-hidden="true"><BotAvatar size={34} thinking /></div>
      <div className="bubble bubble-bot typing" role="status" aria-label="הבוט מחפש תשובה">
        <span className="dot" /><span className="dot" /><span className="dot" />
        <em>מחפש באתר הפניקס…</em>
      </div>
    </div>
  );
}
