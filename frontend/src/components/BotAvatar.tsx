/** The bot's character: a friendly support robot in the brand colours (navy head, orange accents). */
interface Props {
  size?: number;
  /** Blinks the antenna light while the bot is searching. */
  thinking?: boolean;
}

export function BotAvatar({ size = 40, thinking = false }: Props) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="4 2 56 56" className={thinking ? "bot-thinking" : undefined}>
      {/* antenna */}
      <path d="M32 10v7" stroke="#222774" strokeWidth="2.6" strokeLinecap="round" />
      <circle className="bot-antenna" cx="32" cy="8" r="3.6" fill="#FF5A23" />
      {/* headset ear pieces */}
      <rect x="7.5" y="26" width="6" height="12" rx="3" fill="#FF5A23" />
      <rect x="50.5" y="26" width="6" height="12" rx="3" fill="#FF5A23" />
      {/* head and face screen */}
      <rect x="11" y="16" width="42" height="33" rx="13" fill="#222774" />
      <rect x="16.5" y="21.5" width="31" height="21" rx="9" fill="#FFFFFF" />
      {/* eyes with highlights */}
      <ellipse cx="26" cy="30.5" rx="3.2" ry="3.8" fill="#222774" />
      <ellipse cx="38" cy="30.5" rx="3.2" ry="3.8" fill="#222774" />
      <circle cx="27.1" cy="29.2" r="1.1" fill="#FFFFFF" />
      <circle cx="39.1" cy="29.2" r="1.1" fill="#FFFFFF" />
      {/* smile */}
      <path d="M27 36.5q5 4 10 0" stroke="#FF5A23" strokeWidth="2.4" strokeLinecap="round" fill="none" />
      {/* headset mic */}
      <path d="M53.5 38v3.5a6 6 0 0 1-6 6H41" stroke="#FF5A23" strokeWidth="2.2" strokeLinecap="round" fill="none" />
      <circle cx="40" cy="47.5" r="2.2" fill="#FF5A23" />
      {/* neck */}
      <rect x="25" y="49" width="14" height="6" rx="3" fill="#222774" />
    </svg>
  );
}
