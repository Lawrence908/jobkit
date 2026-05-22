import { useEffect, useState } from "react";
import { Badge, Button, Group } from "@mantine/core";
import { IconBrandGoogle } from "@tabler/icons-react";
import { api } from "../api/client";

/**
 * Google connection control.
 *
 * Default (header) shows a green "Connected" badge or a "Connect Google" button.
 * With `allowReconnect`, the connected state also offers a "Reconnect" button so a
 * user whose token expired can re-authorize in place (e.g. on the Profile page,
 * where the expired-sync warning sends them).
 */
export function GoogleStatus({ allowReconnect = false }: { allowReconnect?: boolean }) {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    api
      .get<{ connected: boolean }>("/api/google/status")
      .then((r) => setConnected(r.connected))
      .catch(() => setConnected(false));
  }, []);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const res = await api.get<{ auth_url: string }>("/api/google/oauth/start");
      window.location.href = res.auth_url;
    } catch {
      setConnecting(false);
    }
  };

  if (connected === null) return null;

  if (connected) {
    const badge = (
      <Badge
        variant="outline"
        color="green"
        size="sm"
        styles={{ root: { fontWeight: 500 } }}
      >
        Google: Connected
      </Badge>
    );
    if (!allowReconnect) return badge;
    return (
      <Group gap="sm" wrap="wrap">
        {badge}
        <Button
          variant="subtle"
          color="gray"
          size="compact-sm"
          leftSection={<IconBrandGoogle size={14} />}
          loading={connecting}
          onClick={handleConnect}
        >
          Reconnect
        </Button>
      </Group>
    );
  }

  return (
    <Button
      variant="light"
      color="amber"
      size="sm"
      leftSection={<IconBrandGoogle size={16} />}
      loading={connecting}
      onClick={handleConnect}
    >
      Connect Google
    </Button>
  );
}
