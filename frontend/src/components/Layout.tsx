import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { AppShell, Button, Group, Title, Tooltip } from "@mantine/core";
import { Link, useNavigate } from "react-router-dom";
import { IconLogout, IconRefresh, IconTable, IconUser, IconShield } from "@tabler/icons-react";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { GoogleStatus } from "./GoogleStatus";
import { HubFooter } from "./HubFooter";

const headerHeight = 56;

export function Layout() {
  const navigate = useNavigate();
  const { signOut, session } = useAuth();
  const [reloading, setReloading] = useState(false);
  const [reloadMessage, setReloadMessage] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  useEffect(() => {
    if (!session) {
      setIsAdmin(null);
      return;
    }
    api
      .get<{ admin: boolean }>("/api/admin/check")
      .then((res) => setIsAdmin(res?.admin ?? false))
      .catch(() => setIsAdmin(false));
  }, [session]);

  const handleReloadData = async () => {
    setReloadMessage(null);
    setReloading(true);
    try {
      const res = await api.post<{ ok: boolean; project_count?: number }>("/api/truth-store/reload");
      setReloadMessage(res.project_count != null ? `Data reloaded (${res.project_count} projects).` : "Data reloaded.");
      setTimeout(() => setReloadMessage(null), 3000);
    } catch {
      setReloadMessage("Reload failed");
      setTimeout(() => setReloadMessage(null), 3000);
    } finally {
      setReloading(false);
    }
  };

  const handleLogout = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };

  return (
    <AppShell
      header={{ height: headerHeight }}
      padding="md"
      styles={{
        main: {
          backgroundColor: "var(--bg-base)",
          maxWidth: 1100,
          marginLeft: "auto",
          marginRight: "auto",
          width: "100%",
          paddingLeft: "var(--mantine-spacing-md)",
          paddingRight: "var(--mantine-spacing-md)",
          display: "flex",
          flexDirection: "column",
          minHeight: `calc(100vh - ${headerHeight}px - 3.5rem)`,
        },
      }}
    >
      <AppShell.Header
        style={{
          borderBottom: "1px solid var(--border-subtle)",
          backgroundColor: "var(--bg-elevated)",
        }}
      >
        <div className="app-header-inner">
        <Group h="100%" justify="space-between" wrap="nowrap" gap="md" style={{ width: "100%" }}>
          <Title
            order={4}
            onClick={() => navigate("/dashboard")}
            className="font-display"
            style={{
              cursor: "pointer",
              fontWeight: 700,
              fontSize: "1.25rem",
              color: "var(--text-primary)",
            }}
          >
            JobKit
          </Title>
          <Group gap="sm" wrap="nowrap">
            <GoogleStatus />
            <Tooltip label={reloadMessage ?? "Reload resume/projects data after editing YAML"} opened={reloadMessage !== null}>
              <Button
                variant="subtle"
                color="dark"
                leftSection={<IconRefresh size={16} />}
                size="sm"
                loading={reloading}
                onClick={handleReloadData}
              >
                Reload data
              </Button>
            </Tooltip>
            <Button
              component={Link}
              to="/dashboard/tracker"
              variant="subtle"
              color="dark"
              leftSection={<IconTable size={16} />}
              size="sm"
            >
              Tracker
            </Button>
            <Button
              component={Link}
              to="/dashboard/profile"
              variant="subtle"
              color="dark"
              leftSection={<IconUser size={16} />}
              size="sm"
            >
              Profile
            </Button>
            {isAdmin === true && (
              <Button
                component={Link}
                to="/dashboard/admin"
                variant="subtle"
                color="dark"
                leftSection={<IconShield size={16} />}
                size="sm"
              >
                Admin
              </Button>
            )}
            <Button
              variant="subtle"
              color="dark"
              leftSection={<IconLogout size={16} />}
              onClick={handleLogout}
              size="sm"
            >
              Logout
            </Button>
          </Group>
        </Group>
        </div>
      </AppShell.Header>
      <AppShell.Main>
        <div className="page-container page-container--content" style={{ flex: "1 1 auto", minHeight: 0 }}>
          <Outlet />
        </div>
        <footer style={{ flexShrink: 0 }}>
          <HubFooter />
        </footer>
      </AppShell.Main>
    </AppShell>
  );
}
