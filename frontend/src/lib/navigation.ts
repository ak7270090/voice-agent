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

import { dashboardPath } from "@/lib/paths";

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
      { label: "Overview", href: dashboardPath("/"), icon: LayoutDashboard, available: true },
      { label: "Agents", href: dashboardPath("/agents"), icon: Bot, available: true },
      { label: "Knowledge", href: dashboardPath("/knowledge"), icon: BookOpen, available: true },
    ],
  },
  {
    title: "Deploy",
    items: [
      { label: "Phone numbers", href: dashboardPath("/numbers"), icon: Phone, available: true },
      { label: "Campaigns", href: dashboardPath("/campaigns"), icon: Send, available: true },
      { label: "Integrations", href: dashboardPath("/integrations"), icon: Plug, available: true },
    ],
  },
  {
    title: "Monitor",
    items: [
      { label: "Calls", href: dashboardPath("/calls"), icon: List, available: true },
      {
        label: "Analytics",
        href: dashboardPath("/analytics"),
        icon: ChartColumn,
        available: false,
      },
      { label: "Evals", href: dashboardPath("/evals"), icon: CircleCheck, available: false },
    ],
  },
];
