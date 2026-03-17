import { useEffect, useState } from "react";
import { Badge, Button } from "@mantine/core";
import { IconBrandGoogle } from "@tabler/icons-react";
import { api } from "../api/client";

export function GoogleStatus() {
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
    return (
      <Badge
        variant="outline"
        color="green"
        size="sm"
        styles={{ root: { fontWeight: 500 } }}
      >
        Google: Connected
      </Badge>
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
