import { useEffect, useState } from "react";
import { Badge, Button } from "@mantine/core";
import { IconBrandGoogle } from "@tabler/icons-react";
import { api, getGoogleOAuthStartUrl } from "../api/client";

export function GoogleStatus() {
  const [connected, setConnected] = useState<boolean | null>(null);
  useEffect(() => {
    api.get<{ connected: boolean }>("/api/google/status").then((r) => setConnected(r.connected)).catch(() => setConnected(false));
  }, []);
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
      component="a"
      href={getGoogleOAuthStartUrl()}
      variant="light"
      color="amber"
      size="sm"
      leftSection={<IconBrandGoogle size={16} />}
      style={{ textDecoration: "none" }}
    >
      Connect Google
    </Button>
  );
}
