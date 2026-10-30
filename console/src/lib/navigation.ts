import {
  BookOpen,
  Bot,
  ChartColumn,
  CircleCheck,
  LayoutDashboard,
  List,
  type LucideIcon,
  Phone,
  Plug,
  Send,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  available: boolean;
};

export type NavSection = {
  title: string;
  items: NavItem[];
};

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Build",
    items: [
      { label: "Overview", href: "/", icon: LayoutDashboard, available: true },
      { label: "Agents", href: "/agents", icon: Bot, available: true },
      { label: "Knowledge", href: "/knowledge", icon: BookOpen, available: false },
    ],
  },
  {
    title: "Deploy",
    items: [
      { label: "Phone numbers", href: "/numbers", icon: Phone, available: false },
      { label: "Campaigns", href: "/campaigns", icon: Send, available: false },
      { label: "Integrations", href: "/integrations", icon: Plug, available: false },
    ],
  },
  {
    title: "Monitor",
    items: [
      { label: "Calls", href: "/calls", icon: List, available: false },
      { label: "Analytics", href: "/analytics", icon: ChartColumn, available: false },
      { label: "Evals", href: "/evals", icon: CircleCheck, available: false },
    ],
  },
];
