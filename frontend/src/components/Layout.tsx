import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { AppShell, Button, Group, Title } from "@mantine/core";
import { Link, useNavigate } from "react-router-dom";
import { IconLogout, IconUser } from "@tabler/icons-react";
import { api, refreshCsrfToken } from "../api/client";
import { GoogleStatus } from "./GoogleStatus";
import { HubFooter } from "./HubFooter";

const headerHeight = 56;

export function Layout() {
  const navigate = useNavigate();

  useEffect(() => {
    refreshCsrfToken().catch(() => {});
  }, []);

  const handleLogout = async () => {
    await api.post("/api/auth/logout");
    window.location.href = "/login";
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
            onClick={() => navigate("/")}
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
            <Button
              component={Link}
              to="/profile"
              variant="subtle"
              color="dark"
              leftSection={<IconUser size={16} />}
              size="sm"
            >
              Profile
            </Button>
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
