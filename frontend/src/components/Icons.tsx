/** Inline stroke icons (decorative: always aria-hidden; buttons carry their own labels). */
interface IconProps {
  size?: number;
  color?: string;
  strokeWidth?: number;
}

function Svg({ size = 18, color = "currentColor", strokeWidth = 2, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

export const ChatIcon = (p: IconProps) => (
  <Svg {...p}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" /></Svg>
);
export const PlusIcon = (p: IconProps) => <Svg {...p}><path d="M12 5v14" /><path d="M5 12h14" /></Svg>;
export const MenuIcon = (p: IconProps) => <Svg {...p}><path d="M4 7h16" /><path d="M4 12h16" /><path d="M4 17h16" /></Svg>;
export const ShieldIcon = (p: IconProps) => (
  <Svg {...p}><path d="M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6l7-3Z" /><path d="m9 12 2 2 4-4" /></Svg>
);
export const GlobeIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3a14 14 0 0 1 0 18" /><path d="M12 3a14 14 0 0 0 0 18" /></Svg>
);
export const DocIcon = (p: IconProps) => (
  <Svg {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" /><path d="M14 3v5h5" /><path d="M9 13h6" /><path d="M9 17h4" /></Svg>
);
export const ExternalIcon = (p: IconProps) => (
  <Svg {...p}><path d="M14 4h6v6" /><path d="M20 4 11 13" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></Svg>
);
export const PhoneIcon = (p: IconProps) => (
  <Svg {...p}><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z" /></Svg>
);
export const SearchOffIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /><path d="M8 11h6" /></Svg>
);
export const PersonIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></Svg>;
export const BulbIcon = (p: IconProps) => (
  <Svg {...p}><path d="M9 18h6" /><path d="M10 21h4" /><path d="M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3Z" /></Svg>
);
export const BlockIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></Svg>;
export const ClockIcon = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Svg>;
/** Points left: "send" in a right-to-left layout. */
export const SendArrowIcon = (p: IconProps) => <Svg {...p}><path d="M19 12H5" /><path d="m11 6-6 6 6 6" /></Svg>;
export const DropIcon = (p: IconProps) => <Svg {...p}><path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z" /></Svg>;
export const CarIcon = (p: IconProps) => (
  <Svg {...p}><path d="M5 17h14l-1.5-6.5A2 2 0 0 0 15.6 9H8.4a2 2 0 0 0-1.9 1.5L5 17Z" /><circle cx="8" cy="17" r="2" /><circle cx="16" cy="17" r="2" /></Svg>
);
export const PlaneIcon = (p: IconProps) => <Svg {...p}><path d="M2 16l20-6-4-2-5 1.5L8 4 6 5l3 6-4 1.2L3 10l-1 1 2 3Z" /></Svg>;
export const SummaryIcon = (p: IconProps) => (
  <Svg {...p}><path d="M8 6h12" /><path d="M8 12h12" /><path d="M8 18h8" /><path d="M4 6h.01" /><path d="M4 12h.01" /><path d="M4 18h.01" /></Svg>
);
export const CopyIcon = (p: IconProps) => (
  <Svg {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 0 1 2-2h8" /></Svg>
);
export const ShareIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="18" cy="5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="19" r="2.5" /><path d="m8.2 10.8 7.6-4.4" /><path d="m8.2 13.2 7.6 4.4" /></Svg>
);
export const PrintIcon = (p: IconProps) => (
  <Svg {...p}><path d="M7 9V3h10v6" /><rect x="3" y="9" width="18" height="8" rx="2" /><path d="M7 14h10v7H7z" /></Svg>
);
export const WhatsAppIcon = (p: IconProps) => (
  <Svg {...p}><path d="M20 12a8 8 0 0 1-11.9 7L4 20l1.1-4A8 8 0 1 1 20 12Z" /><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-1.8-.9-.9.9a3.6 3.6 0 0 1-2.3-2.3l.9-.9-.9-1.8z" /></Svg>
);
export const CloseIcon = (p: IconProps) => <Svg {...p}><path d="M6 6l12 12" /><path d="M18 6 6 18" /></Svg>;
export const DownloadDocIcon = (p: IconProps) => (
  <Svg {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" /><path d="M14 3v5h5" /><path d="M12 12v6" /><path d="m9 15 3 3 3-3" /></Svg>
);
