import {
  Activity,
  Database,
  FileClock,
  Gauge,
  ListChecks,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  PanelsTopLeft,
  Search,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

const navItems = [
  { href: "#/", label: "Overview", icon: Gauge },
  { href: "#/sessions", label: "Sessions", icon: MessagesSquare },
  { href: "#/dialogue-windows", label: "Dialogue Windows", icon: PanelsTopLeft },
  { href: "#/memory-units", label: "Memory Units", icon: Database },
  { href: "#/retrieval-preview", label: "Retrieval", icon: Search },
  { href: "#/operations", label: "Operations", icon: FileClock },
  { href: "#/index-health", label: "Index Health", icon: Activity },
];

type ShellProps = {
  children: ReactNode;
};

export function Shell({ children }: ShellProps) {
  const currentHash = window.location.hash || "#/";
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return window.localStorage.getItem("nanomem.sidebarCollapsed") === "true";
  });

  useEffect(() => {
    window.localStorage.setItem(
      "nanomem.sidebarCollapsed",
      String(sidebarCollapsed),
    );
  }, [sidebarCollapsed]);

  const ToggleIcon = sidebarCollapsed ? PanelLeftOpen : PanelLeftClose;

  return (
    <div
      className={`app-shell${
        sidebarCollapsed ? " app-shell-sidebar-collapsed" : ""
      }`}
    >
      <aside className="sidebar">
        <div className="sidebar-header">
          <a className="brand" href="#/" aria-label="NanoMem Manager">
            <ListChecks size={20} />
            <span>NanoMem</span>
          </a>
          <button
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-pressed={sidebarCollapsed}
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed((value) => !value)}
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            type="button"
          >
            <ToggleIcon aria-hidden="true" size={16} />
          </button>
        </div>
        <nav className="nav-list" aria-label="Manager sections">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "#/"
                ? currentHash === "#/" || currentHash === ""
                : currentHash.startsWith(item.href);
            return (
              <a
                aria-current={active ? "page" : undefined}
                className={`nav-link${active ? " nav-link-active" : ""}`}
                href={item.href}
                key={item.href}
                title={item.label}
              >
                <Icon size={17} />
                <span>{item.label}</span>
              </a>
            );
          })}
        </nav>
      </aside>
      <main className="main-surface">{children}</main>
    </div>
  );
}
