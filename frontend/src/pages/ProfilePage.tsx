import { useEffect, useState } from "react";
import {
  Title,
  Stack,
  Paper,
  TextInput,
  Textarea,
  Select,
  Button,
  Loader,
  Center,
  Alert,
  Text,
} from "@mantine/core";
import { api } from "../api/client";

export interface Profile {
  name: string;
  email: string;
  phone: string;
  linkedin: string;
  website: string;
  github: string;
  pitch: string;
  default_tone: string;
  default_focus: string;
  default_length: string;
}

const TONE_OPTIONS = ["neutral", "professional", "conversational"];
const FOCUS_OPTIONS = ["full-stack", "backend", "frontend", "infrastructure", "mobile"];
const LENGTH_OPTIONS = ["1 page", "2 pages"];

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    api
      .get<Profile>("/api/profile")
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      const updated = await api.put<Profile>("/api/profile", {
        name: profile.name,
        email: profile.email,
        phone: profile.phone,
        linkedin: profile.linkedin,
        website: profile.website,
        github: profile.github,
        pitch: profile.pitch,
        default_tone: profile.default_tone,
        default_focus: profile.default_focus,
        default_length: profile.default_length,
      });
      setProfile(updated);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="amber" />
      </Center>
    );
  }

  if (!profile) {
    return (
      <div className="page-container--narrow" style={{ paddingTop: "1rem" }}>
        <Alert color="red">{error || "Failed to load profile"}</Alert>
      </div>
    );
  }

  return (
    <Stack gap="xl" style={{ width: "100%", maxWidth: 560 }}>
      <Title order={3} className="font-display" style={{ fontWeight: 700 }}>
        Personalization
      </Title>
      <Text size="sm" c="dimmed">
        Contact and defaults used when generating resumes and cover letters.
      </Text>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Text size="sm" fw={600} className="font-display">
            Contact
          </Text>
          <TextInput
            label="Name"
            value={profile.name}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })}
            placeholder="Your name"
          />
          <TextInput
            label="Email"
            type="email"
            value={profile.email}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })}
            placeholder="you@example.com"
          />
          <TextInput
            label="Phone"
            value={profile.phone}
            onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            placeholder="+1 234 567 8900"
          />
          <TextInput
            label="LinkedIn"
            value={profile.linkedin}
            onChange={(e) => setProfile({ ...profile, linkedin: e.target.value })}
            placeholder="https://linkedin.com/in/..."
          />
          <TextInput
            label="Website"
            value={profile.website}
            onChange={(e) => setProfile({ ...profile, website: e.target.value })}
            placeholder="https://yoursite.com"
          />
          <TextInput
            label="GitHub"
            value={profile.github}
            onChange={(e) => setProfile({ ...profile, github: e.target.value })}
            placeholder="https://github.com/..."
          />
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Text size="sm" fw={600} className="font-display">
            Pitch
          </Text>
          <Textarea
            label="Short pitch (used in cover letters)"
            value={profile.pitch}
            onChange={(e) => setProfile({ ...profile, pitch: e.target.value })}
            placeholder="A sentence or two about your background and what you're looking for."
            minRows={3}
          />
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Text size="sm" fw={600} className="font-display">
            Defaults for generation
          </Text>
          <Select
            label="Default tone"
            data={TONE_OPTIONS}
            value={profile.default_tone}
            onChange={(v) => v && setProfile({ ...profile, default_tone: v })}
          />
          <Select
            label="Default focus"
            data={FOCUS_OPTIONS}
            value={profile.default_focus}
            onChange={(v) => v && setProfile({ ...profile, default_focus: v })}
          />
          <Select
            label="Default length"
            data={LENGTH_OPTIONS}
            value={profile.default_length}
            onChange={(v) => v && setProfile({ ...profile, default_length: v })}
          />
        </Stack>
      </Paper>

      {error && <Alert color="red">{error}</Alert>}
      {success && <Alert color="green">Profile saved.</Alert>}

      <Button onClick={handleSave} loading={saving} color="amber" variant="filled">
        Save profile
      </Button>
    </Stack>
  );
}
