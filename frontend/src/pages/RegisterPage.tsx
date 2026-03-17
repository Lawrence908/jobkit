import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  TextInput,
  PasswordInput,
  Button,
  Paper,
  Title,
  Stack,
  Alert,
  Text,
  Anchor,
} from "@mantine/core";
import { api } from "../api/client";

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setLoading(true);
    try {
      await api.post<{ ok: boolean }>("/api/auth/register", {
        email,
        password,
        invite_code: inviteCode.trim(),
      });
      navigate("/login?registered=1", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page__container">
        <Paper className="login-page__card" p="xl" shadow="md" radius="lg" withBorder>
          <Title order={2} mb="lg" className="font-display" style={{ fontWeight: 700 }}>
            Create account
          </Title>
          <form onSubmit={handleSubmit}>
            <Stack gap="md">
              {error && (
                <Alert color="red" variant="light">
                  {error}
                </Alert>
              )}
              <TextInput
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                size="sm"
              />
              <PasswordInput
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                size="sm"
                minLength={6}
              />
              <PasswordInput
                label="Confirm password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                size="sm"
              />
              <TextInput
                label="Invite code"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                required
                placeholder="Enter the invite code you received"
                size="sm"
              />
              <Button
                type="submit"
                loading={loading}
                color="amber"
                variant="filled"
                fullWidth
                size="md"
              >
                Register
              </Button>
              <Text size="sm" ta="center">
                Already have an account?{" "}
                <Anchor component={Link} to="/login" size="sm">
                  Log in
                </Anchor>
              </Text>
            </Stack>
          </form>
        </Paper>
      </div>
    </div>
  );
}
