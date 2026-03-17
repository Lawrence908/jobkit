import { LoadingOverlay } from "@mantine/core";
import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { Layout } from "./components/Layout";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NewJobPage } from "./pages/NewJobPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ResumePage } from "./pages/ResumePage";
import { SkillsPage } from "./pages/SkillsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SpreadsheetPage } from "./pages/SpreadsheetPage";
import { AdminPage } from "./pages/AdminPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  if (loading) return <LoadingOverlay visible />;
  if (!session) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicOnlyRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  if (loading) return <LoadingOverlay visible />;
  if (session) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <PublicOnlyRoute>
            <LoginPage />
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicOnlyRoute>
            <RegisterPage />
          </PublicOnlyRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="jobs/new" element={<NewJobPage />} />
        <Route path="jobs/:jobId" element={<JobDetailPage />} />
        <Route path="tracker" element={<SpreadsheetPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="profile/resume" element={<ResumePage />} />
        <Route path="profile/skills" element={<SkillsPage />} />
        <Route path="profile/projects" element={<ProjectsPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
