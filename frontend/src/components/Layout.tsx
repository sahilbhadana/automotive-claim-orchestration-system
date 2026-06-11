import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  Banknote,
  FilePlus2,
  Files,
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
  section: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/claims", label: "Claims", icon: Files, roles: ["customer", "adjuster", "supervisor", "admin"], section: "Workspace" },
  { to: "/claims/new", label: "File a Claim", icon: FilePlus2, roles: ["customer", "adjuster", "supervisor", "admin"], section: "Workspace" },
  { to: "/settlements", label: "Settlements", icon: Banknote, roles: ["adjuster", "supervisor", "admin"], section: "Workspace" },
  { to: "/admin/dlq", label: "Dead-Letter Queue", icon: TriangleAlert, roles: ["supervisor", "admin"], section: "Operations" },
  { to: "/admin/system", label: "System Health", icon: Activity, roles: ["admin"], section: "Operations" },
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
  const sections = [...new Set(visibleItems.map((i) => i.section))];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo">
            <ShieldCheck size={17} />
          </div>
          <div>
            <span className="brand-name">ClaimFlow</span>
            <span className="brand-tag">Claims Platform</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          {sections.map((section) => (
            <div key={section}>
              <div className="nav-section">{section}</div>
              {visibleItems
                .filter((i) => i.section === section)
                .map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === "/claims"}
                      className={({ isActive }) =>
                        `nav-link${isActive ? " nav-link-active" : ""}`
                      }
                    >
                      <Icon size={16} />
                      {item.label}
                    </NavLink>
                  );
                })}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          {user && (
            <div className="user-card">
              <div className="user-avatar">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="user-info">
                <div className="user-name">{user.full_name}</div>
                <div className="user-role">{ROLE_LABELS[user.role]}</div>
              </div>
            </div>
          )}
          <div className="sidebar-actions">
            <button className="btn btn-ghost" onClick={handleLogout}>
              <LogOut size={14} />
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
