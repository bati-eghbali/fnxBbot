import { Message, Status } from "./api";

/** Replies that add nothing to a summary: transient errors, refusals of unrelated topics, small talk. */
const SKIPPED: Status[] = ["error", "off_topic", "greeting"];

export const SUMMARY_TITLE = "סיכום שיחה עם FNX AI Chatbot · הבוט החכם של הפניקס";
const DISCLAIMER = "מידע כללי מתוך אתר הפניקס בלבד. אינו ייעוץ אישי ואינו מחליף את תנאי הפוליסה.";

function plain(text: string): string {
  return text.replace(/\*\*([^*]+)\*\*/g, "$1").trim();
}

function shortUrl(url: string): string {
  return url.replace(/^https:\/\/www\./, "").replace(/\/$/, "");
}

/** Question/answer pairs worth summarizing, in conversation order. */
export function summaryPairs(messages: Message[]): { question: Message; answer: Message }[] {
  const pairs = [];
  for (let i = 0; i + 1 < messages.length; i++) {
    const question = messages[i];
    const answer = messages[i + 1];
    if (question.role !== "user" || answer.role !== "assistant") continue;
    if (answer.status && SKIPPED.includes(answer.status)) continue;
    pairs.push({ question, answer });
  }
  return pairs;
}

/**
 * Plain-text summary built only from what the bot already said (no model call, so nothing new can
 * be invented). Used for copy, WhatsApp, share and print.
 */
export function buildSummary(messages: Message[], date: Date = new Date()): string {
  const lines = [SUMMARY_TITLE, date.toLocaleDateString("he-IL"), ""];
  summaryPairs(messages).forEach(({ question, answer }, i) => {
    lines.push(`${i + 1}. שאלה: ${plain(question.content)}`);
    if (answer.status === "not_found") lines.push("   (המידע לא מופיע באתר הפניקס)");
    lines.push(`   תשובה: ${plain(answer.content)}`);
    if (answer.sources.length > 0) {
      lines.push("   מקורות:");
      answer.sources.forEach((s) => lines.push(`   - ${s.title}: ${shortUrl(s.url)}`));
    }
    lines.push("");
  });
  lines.push(DISCLAIMER);
  return lines.join("\n");
}
