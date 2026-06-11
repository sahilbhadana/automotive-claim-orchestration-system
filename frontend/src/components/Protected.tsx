import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../api/types";

export function Protected({
  children,
  roles,
}: {
  children: ReactNode;
  roles?: UserRole[];
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="page-loading">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="page">
        <div className="empty-state">
          <h2>Access denied</h2>
          <p>Your role ({user.role}) does not have permission to view this page.</p>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
