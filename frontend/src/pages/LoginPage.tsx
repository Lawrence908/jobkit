import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { TextInput, PasswordInput, Button, Paper, Title, Stack, Alert } from "@mantine/core";
import { api } from "../api/client";

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post<{ ok: boolean; detail?: string }>("/api/auth/login", {
        username,
        password,
      });
      if ((res as { ok: boolean }).ok) {
        navigate("/", { replace: true });
        return;
      }
      setError((res as { detail?: string }).detail || "Login failed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page__container">
        <Paper className="login-page__card" p="xl" shadow="md" radius="lg" withBorder>
        <Title order={2} mb="lg" className="font-display" style={{ fontWeight: 700 }}>
          JobKit
        </Title>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            {error && <Alert color="red" variant="light">{error}</Alert>}
            <TextInput
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              size="sm"
            />
            <PasswordInput
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              size="sm"
            />
            <Button type="submit" loading={loading} color="amber" variant="filled" fullWidth size="md">
              Log in
            </Button>
          </Stack>
        </form>
        </Paper>
      </div>
    </div>
  );
}
