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
  Anchor,
  Slider,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import {
  LLM_PROVIDER_OPTIONS,
  LLM_MODEL_OPTIONS_BY_PROVIDER,
  DEFAULT_MODEL_BY_PROVIDER,
  type LLMProvider,
} from "../config/profile-llm";

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
  llm_provider?: string;
  llm_api_key?: string;
  llm_model?: string;
  llm_temperature?: number;
  google_drive_root_folder_id?: string;
  google_sheets_spreadsheet_id?: string;
  google_sheets_tab_name?: string;
  google_sheets_url_column?: string;
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
      .then((p) =>
        setProfile({
          ...p,
          llm_provider: p.llm_provider ?? "openrouter",
          llm_api_key: p.llm_api_key ?? "",
          llm_model: p.llm_model ?? "anthropic/claude-sonnet-4.6",
          llm_temperature: typeof p.llm_temperature === "number" ? p.llm_temperature : 0.2,
        })
      )
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
        llm_provider: profile.llm_provider,
        llm_api_key: profile.llm_api_key,
        llm_model: profile.llm_model,
        llm_temperature: profile.llm_temperature,
        google_drive_root_folder_id: profile.google_drive_root_folder_id ?? "",
        google_sheets_spreadsheet_id: profile.google_sheets_spreadsheet_id ?? "",
        google_sheets_tab_name: profile.google_sheets_tab_name ?? "",
        google_sheets_url_column: profile.google_sheets_url_column ?? "",
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
        Contact and defaults used when generating resumes and cover letters.{" "}
        <Anchor component={Link} to="/dashboard/profile/resume" size="sm">
          Resume base
        </Anchor>
        {" · "}
        <Anchor component={Link} to="/dashboard/profile/skills" size="sm">
          Skills
        </Anchor>
        {" · "}
        <Anchor component={Link} to="/dashboard/profile/projects" size="sm">
          Projects
        </Anchor>
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

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Text size="sm" fw={600} className="font-display">
            LLM for generation
          </Text>
          <Text size="xs" c="dimmed">
            Choose provider and API key for resume/cover letter generation. Stored in your profile.
          </Text>
          <Select
            label="Provider"
            data={LLM_PROVIDER_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
            value={profile.llm_provider || "openrouter"}
            onChange={(v) => {
              const provider = (v || "openrouter") as LLMProvider;
              const models = LLM_MODEL_OPTIONS_BY_PROVIDER[provider];
              const currentInList = models.some((m) => m.value === (profile.llm_model || ""));
              setProfile({
                ...profile,
                llm_provider: provider,
                llm_model: currentInList ? profile.llm_model : DEFAULT_MODEL_BY_PROVIDER[provider],
              });
            }}
          />
          <TextInput
            label="API key"
            type="password"
            value={profile.llm_api_key || ""}
            onChange={(e) => setProfile({ ...profile, llm_api_key: e.target.value })}
            placeholder={
              profile.llm_provider === "openai"
                ? "sk-proj-..."
                : profile.llm_provider === "anthropic"
                  ? "sk-ant-..."
                  : "sk-or-v1-..."
            }
            description="Your key is stored in your profile and used only for your generations."
          />
          <Select
            label="Model"
            data={LLM_MODEL_OPTIONS_BY_PROVIDER[(profile.llm_provider || "openrouter") as LLMProvider].map((o) => ({
              value: o.value,
              label: o.label,
            }))}
            value={profile.llm_model || DEFAULT_MODEL_BY_PROVIDER[(profile.llm_provider || "openrouter") as LLMProvider]}
            onChange={(v) => v && setProfile({ ...profile, llm_model: v })}
          />
          <Stack gap={4}>
            <Text size="sm" fw={500}>
              Temperature
            </Text>
            <Slider
              min={0}
              max={1}
              step={0.1}
              value={typeof profile.llm_temperature === "number" ? profile.llm_temperature : 0.2}
              onChange={(v) => setProfile({ ...profile, llm_temperature: v })}
              marks={[{ value: 0, label: "0" }, { value: 0.5, label: "0.5" }, { value: 1, label: "1" }]}
            />
            <Text size="xs" c="dimmed" mt="sm">
              Lower (e.g. 0.2) = more focused and consistent; higher = more varied and creative. Default 0.2.
            </Text>
          </Stack>
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Text size="sm" fw={600} className="font-display">
            Google Drive &amp; Sheets (optional)
          </Text>
          <Text size="xs" c="dimmed">
            Connect Google in the header, then set these to sync jobs to your own folder and tracker. Leave blank to never sync to Sheets.
          </Text>
          <TextInput
            label="Drive root folder ID"
            value={profile.google_drive_root_folder_id ?? ""}
            onChange={(e) => setProfile({ ...profile, google_drive_root_folder_id: e.target.value })}
            placeholder="e.g. 1ABC...xyz (from folder URL)"
            description="Uploads go under this folder. Empty = create a JobKit folder in Drive."
          />
          <TextInput
            label="Sheets spreadsheet ID"
            value={profile.google_sheets_spreadsheet_id ?? ""}
            onChange={(e) => setProfile({ ...profile, google_sheets_spreadsheet_id: e.target.value })}
            placeholder="e.g. 1tBEe... (from spreadsheet URL)"
            description="Only used when set. Job updates sync to this sheet."
          />
          <TextInput
            label="Sheet tab name"
            value={profile.google_sheets_tab_name ?? ""}
            onChange={(e) => setProfile({ ...profile, google_sheets_tab_name: e.target.value })}
            placeholder="e.g. Job Applications"
          />
          <TextInput
            label="Job URL column name"
            value={profile.google_sheets_url_column ?? ""}
            onChange={(e) => setProfile({ ...profile, google_sheets_url_column: e.target.value })}
            placeholder="Job URL (default)"
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
