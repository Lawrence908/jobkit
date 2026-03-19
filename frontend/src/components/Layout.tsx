import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Alert, AppShell, Box, Burger, Button, Drawer, Group, Stack, Title, Tooltip } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Link, useNavigate } from "react-router-dom";
import {
  IconBriefcase,
  IconChartBar,
  IconEye,
  IconLogout,
  IconRefresh,
  IconTable,
  IconUser,
  IconShield,
} from "@tabler/icons-react";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { GoogleStatus } from "./GoogleStatus";
import { HubFooter } from "./HubFooter";

const headerHeight = 56;

export function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signOut, session, isDemo } = useAuth();
  const [reloading, setReloading] = useState(false);
  const [reloadMessage, setReloadMessage] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [mobileNavOpened, { toggle: toggleMobileNav, close: closeMobileNav }] = useDisclosure(false);

  useEffect(() => {
    closeMobileNav();
  }, [location.pathname, closeMobileNav]);

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

  const onJobsSection =
    location.pathname === "/dashboard" || location.pathname.startsWith("/dashboard/jobs");

  return (
    <AppShell
      header={{ height: headerHeight }}
      padding="md"
      zIndex={150}
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
          zIndex: 150,
        }}
      >
        <div className="app-header-inner">
        <Group
          h="100%"
          justify="space-between"
          wrap="nowrap"
          gap="md"
          style={{ width: "100%", minWidth: 0 }}
          align="center"
        >
          <Group gap="sm" wrap="nowrap" align="center" style={{ minWidth: 0, flex: "1 1 auto" }}>
            <Burger
              hiddenFrom="lg"
              opened={mobileNavOpened}
              onClick={toggleMobileNav}
              size="sm"
              aria-label="Open navigation menu"
              color="var(--text-primary)"
              style={{ flexShrink: 0 }}
            />
            <Title
              order={4}
              onClick={() => {
                closeMobileNav();
                navigate("/dashboard");
              }}
              className="font-display"
              style={{
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "1.25rem",
                color: "var(--text-primary)",
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              JobKit
            </Title>
          </Group>
          <Group gap="sm" wrap="nowrap" visibleFrom="lg" justify="flex-end" style={{ flexShrink: 0 }}>
            <Button
              component={Link}
              to="/dashboard"
              variant={onJobsSection ? "filled" : "light"}
              color="amber"
              leftSection={<IconBriefcase size={16} />}
              size="sm"
            >
              Jobs
            </Button>
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
              to="/dashboard/stats"
              variant="subtle"
              color="dark"
              leftSection={<IconChartBar size={16} />}
              size="sm"
            >
              Stats
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
        <Drawer
          hiddenFrom="lg"
          opened={mobileNavOpened}
          onClose={closeMobileNav}
          position="right"
          size="min(100%, 280px)"
          title="Menu"
          styles={{
            header: { borderBottom: "1px solid var(--border-subtle)" },
            body: { paddingTop: "var(--mantine-spacing-md)" },
          }}
        >
          <Stack gap="xs">
            <Button
              component={Link}
              to="/dashboard"
              variant={onJobsSection ? "filled" : "light"}
              color="amber"
              leftSection={<IconBriefcase size={18} />}
              fullWidth
              justify="flex-start"
              size="md"
              fw={600}
              onClick={closeMobileNav}
            >
              Jobs
            </Button>
            <Box pb="sm" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
              <GoogleStatus />
            </Box>
            <Tooltip label={reloadMessage ?? "Reload resume/projects data after editing YAML"} opened={reloadMessage !== null}>
              <Button
                variant="light"
                color="dark"
                leftSection={<IconRefresh size={18} />}
                fullWidth
                justify="flex-start"
                loading={reloading}
                onClick={() => {
                  void handleReloadData();
                }}
              >
                Reload data
              </Button>
            </Tooltip>
            <Button
              component={Link}
              to="/dashboard/tracker"
              variant="light"
              color="dark"
              leftSection={<IconTable size={18} />}
              fullWidth
              justify="flex-start"
              onClick={closeMobileNav}
            >
              Tracker
            </Button>
            <Button
              component={Link}
              to="/dashboard/stats"
              variant="light"
              color="dark"
              leftSection={<IconChartBar size={18} />}
              fullWidth
              justify="flex-start"
              onClick={closeMobileNav}
            >
              Stats
            </Button>
            <Button
              component={Link}
              to="/dashboard/profile"
              variant="light"
              color="dark"
              leftSection={<IconUser size={18} />}
              fullWidth
              justify="flex-start"
              onClick={closeMobileNav}
            >
              Profile
            </Button>
            {isAdmin === true && (
              <Button
                component={Link}
                to="/dashboard/admin"
                variant="light"
                color="dark"
                leftSection={<IconShield size={18} />}
                fullWidth
                justify="flex-start"
                onClick={closeMobileNav}
              >
                Admin
              </Button>
            )}
            <Button
              variant="light"
              color="red"
              leftSection={<IconLogout size={18} />}
              fullWidth
              justify="flex-start"
              onClick={() => {
                closeMobileNav();
                void handleLogout();
              }}
            >
              Logout
            </Button>
          </Stack>
        </Drawer>
        </div>
      </AppShell.Header>
      <AppShell.Main>
        {isDemo && (
          <Alert
            icon={<IconEye size={18} />}
            color="amber"
            variant="light"
            radius={0}
            mb="md"
            styles={{ root: { maxWidth: 1100, marginLeft: "auto", marginRight: "auto" } }}
          >
            You're viewing the demo as Ada Lovelace. Everything is read-only.
          </Alert>
        )}
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
