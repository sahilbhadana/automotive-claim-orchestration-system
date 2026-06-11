import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  Banknote,
  FilePlus2,
  Files,
  House,
  LogOut,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Files;
  roles: string[];
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Home", icon: House, roles: ["customer", "adjuster", "supervisor", "admin"], end: true },
  { to: "/claims", label: "Claims", icon: Files, roles: ["customer", "adjuster", "supervisor", "admin"], end: true },
  { to: "/claims/new", label: "New Claim", icon: FilePlus2, roles: ["customer", "adjuster", "supervisor", "admin"] },
  { to: "/settlements", label: "Settlements", icon: Banknote, roles: ["adjuster", "supervisor", "admin"] },
  { to: "/admin/dlq", label: "DLQ", icon: TriangleAlert, roles: ["supervisor", "admin"] },
  { to: "/admin/system", label: "Health", icon: Activity, roles: ["admin"] },
];

const ROLE_LABELS: Record<string, string> = {
  customer: "Customer",
  adjuster: "Adjuster",
  supervisor: "Supervisor",
  admin: "Administrator",
};

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const visibleItems = NAV_ITEMS.filter(
    (item) => user && item.roles.includes(user.role),
  );

  return (
    <div className="app-shell">
      <header className="topbar-wrap">
        <div className="topbar">
          <Link to="/" className="topbar-brand">
            <div className="brand-logo">
              <ShieldCheck size={17} />
            </div>
            <span className="brand-name">ClaimFlow</span>
          </Link>
          <nav className="topbar-nav">
            {visibleItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `nav-link${isActive ? " nav-link-active" : ""}`
                  }
                >
                  <Icon size={15} />
                  <span className="nav-label">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
          <div className="topbar-user">
            {user && (
              <div className="topbar-identity" title={user.full_name}>
                <div className="user-avatar">
                  {user.full_name.charAt(0).toUpperCase()}
                </div>
                <div className="topbar-identity-text">
                  <span className="user-name">{user.full_name}</span>
                  <span className="user-role">{ROLE_LABELS[user.role]}</span>
                </div>
              </div>
            )}
            <button
              className="btn btn-ghost btn-small"
              onClick={handleLogout}
              title="Sign out"
            >
              <LogOut size={14} />
              <span className="nav-label">Sign out</span>
            </button>
          </div>
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
