import {
  Activity,
  Database,
  FileClock,
  Gauge,
  ListChecks,
  Search,
} from "lucide-react";
import type { ReactNode } from "react";

const navItems = [
  { href: "#/", label: "Overview", icon: Gauge },
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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#/" aria-label="NanoMem Manager">
          <ListChecks size={22} />
          <span>NanoMem</span>
        </a>
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
