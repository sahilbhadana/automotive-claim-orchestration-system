import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
  roles: string[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/claims", label: "Claims", roles: ["customer", "adjuster", "supervisor", "admin"] },
  { to: "/claims/new", label: "File a Claim", roles: ["customer", "adjuster", "supervisor", "admin"] },
  { to: "/settlements", label: "Settlements", roles: ["adjuster", "supervisor", "admin"] },
  { to: "/admin/dlq", label: "Dead-Letter Queue", roles: ["supervisor", "admin"] },
  { to: "/admin/system", label: "System Health", roles: ["admin"] },
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
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">🛡️</span>
          <span className="brand-name">ClaimFlow</span>
        </div>
        <nav className="sidebar-nav">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/claims"}
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link-active" : ""}`
              }
            >
              {item.label}
            </NavLink>
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
          <button className="btn btn-ghost btn-full" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
