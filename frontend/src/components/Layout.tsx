import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/", label: "Today", icon: "◷", end: true },
  { to: "/plan", label: "Plan", icon: "✎" },
  { to: "/account", label: "Account", icon: "✓" },
  { to: "/coach", label: "Bogi", icon: "🗣" },
  { to: "/databank", label: "Data", icon: "▢" },
];

export default function Layout() {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col">
      <header className="flex items-center justify-between px-5 pt-6 pb-3">
        <div>
          <div className="text-2xl font-extrabold tracking-tight">
            Bogi<span className="text-brand">.</span>
          </div>
          <div className="text-xs text-muted">plan vs reality — for you</div>
        </div>
        <div className="grid h-10 w-10 place-items-center rounded-full bg-brand/20 text-brand font-bold">
          H
        </div>
      </header>

      <main className="flex-1 px-4 pb-28">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20">
        <div className="mx-auto max-w-md px-4 pb-4">
          <div className="card flex items-center justify-between px-2 py-2">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `flex flex-1 flex-col items-center gap-0.5 rounded-xl py-2 text-[11px] font-semibold transition ${
                    isActive ? "bg-brand/20 text-brand" : "text-muted hover:text-white"
                  }`
                }
              >
                <span className="text-base leading-none">{n.icon}</span>
                {n.label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
    </div>
  );
}
