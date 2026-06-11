import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Protected } from "./components/Protected";
import { ClaimDetailPage } from "./pages/ClaimDetailPage";
import { ClaimsListPage } from "./pages/ClaimsListPage";
import { DlqPage } from "./pages/DlqPage";
import { LoginPage } from "./pages/LoginPage";
import { NewClaimPage } from "./pages/NewClaimPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettlementsPage } from "./pages/SettlementsPage";
import { SystemHealthPage } from "./pages/SystemHealthPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <Protected>
                <Layout />
              </Protected>
            }
          >
            <Route path="/" element={<Navigate to="/claims" replace />} />
            <Route path="/claims" element={<ClaimsListPage />} />
            <Route path="/claims/new" element={<NewClaimPage />} />
            <Route path="/claims/:claimId" element={<ClaimDetailPage />} />
            <Route
              path="/settlements"
              element={
                <Protected roles={["adjuster", "supervisor", "admin"]}>
                  <SettlementsPage />
                </Protected>
              }
            />
            <Route
              path="/admin/dlq"
              element={
                <Protected roles={["supervisor", "admin"]}>
                  <DlqPage />
                </Protected>
              }
            />
            <Route
              path="/admin/system"
              element={
                <Protected roles={["admin"]}>
                  <SystemHealthPage />
                </Protected>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/claims" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
