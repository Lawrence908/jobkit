import { useEffect, useRef, useState } from "react";
import {
  Title,
  Stack,
  Paper,
  TextInput,
  Textarea,
  Select,
  Button,
  FileButton,
  Loader,
  Center,
  Alert,
  Text,
  Anchor,
  Slider,
  Avatar,
  Group,
  Flex,
  Box,
  Badge,
  Divider,
  SimpleGrid,
  ThemeIcon,
} from "@mantine/core";
import { Link } from "react-router-dom";
import {
  IconBrandLinkedin,
  IconBrandGithub,
  IconMail,
  IconPhone,
  IconWorld,
  IconBriefcase,
  IconCode,
  IconFolder,
  IconArrowRight,
  IconPencil,
  IconRefresh,
  IconPhoto,
  IconTrash,
} from "@tabler/icons-react";
import { useMediaQuery } from "@mantine/hooks";
import { api } from "../api/client";
import { GoogleStatus } from "../components/GoogleStatus";
import { flattenSkillPool } from "../utils/skills";
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
  has_avatar?: boolean;
}

const TONE_OPTIONS = ["neutral", "professional", "conversational"];
const FOCUS_OPTIONS = ["full-stack", "backend", "frontend", "infrastructure", "mobile"];
const LENGTH_OPTIONS = ["1 page", "2 pages"];

type ResumeSpotlight = { summary?: string; experience?: unknown[]; education?: unknown[] };
type SkillsSpotlight = {
  items?: string[];
  categories?: Record<string, string[]>;
  skills_spotlight?: string[] | null;
};

const EMPTY_RESUME: ResumeSpotlight = {};
const EMPTY_SKILLS: SkillsSpotlight = {};

function initialsFromName(name: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [resumePeek, setResumePeek] = useState<{
    summary: string;
    expCount: number;
    eduCount: number;
  } | null>(null);
  const [skillTags, setSkillTags] = useState<string[]>([]);
  const [skillsCurated, setSkillsCurated] = useState(false);
  const [projectPeek, setProjectPeek] = useState<Array<{ name: string; description: string }>>([]);
  const [spotlightLoading, setSpotlightLoading] = useState(true);
  const [resumePreviewKey, setResumePreviewKey] = useState(0);
  const [resumePdfUrl, setResumePdfUrl] = useState<string | null>(null);
  const [resumePdfLoading, setResumePdfLoading] = useState(true);
  const [resumePdfError, setResumePdfError] = useState(false);
  const resumePdfObjectUrlRef = useRef<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const avatarObjectUrlRef = useRef<string | null>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const resumeSpotlightRef = useRef<HTMLDivElement>(null);
  const isSpotlight3Col = useMediaQuery("(min-width: 48em)");
  const [spotlightRowHeightPx, setSpotlightRowHeightPx] = useState(600);

  useEffect(() => {
    if (!isSpotlight3Col) return;
    const node = resumeSpotlightRef.current;
    if (!node) return;
    const update = () => {
      const h = node.getBoundingClientRect().height;
      if (h >= 240) setSpotlightRowHeightPx(Math.round(h));
    };
    update();
    const ro = new ResizeObserver(() => requestAnimationFrame(update));
    ro.observe(node);
    return () => ro.disconnect();
  }, [
    isSpotlight3Col,
    resumePdfUrl,
    resumePreviewKey,
    resumePdfLoading,
    resumePdfError,
    spotlightLoading,
    profile,
  ]);

  useEffect(() => {
    let cancelled = false;
    setResumePdfLoading(true);
    setResumePdfError(false);
    if (resumePdfObjectUrlRef.current) {
      URL.revokeObjectURL(resumePdfObjectUrlRef.current);
      resumePdfObjectUrlRef.current = null;
    }
    setResumePdfUrl(null);
    api
      .getBlob("/api/resume/preview.pdf")
      .then((blob) => {
        if (cancelled) return;
        const u = URL.createObjectURL(blob);
        resumePdfObjectUrlRef.current = u;
        setResumePdfUrl(u);
      })
      .catch(() => {
        if (!cancelled) setResumePdfError(true);
      })
      .finally(() => {
        if (!cancelled) setResumePdfLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [resumePreviewKey]);

  useEffect(
    () => () => {
      if (resumePdfObjectUrlRef.current) {
        URL.revokeObjectURL(resumePdfObjectUrlRef.current);
        resumePdfObjectUrlRef.current = null;
      }
      if (avatarObjectUrlRef.current) {
        URL.revokeObjectURL(avatarObjectUrlRef.current);
        avatarObjectUrlRef.current = null;
      }
    },
    [],
  );

  useEffect(() => {
    if (!profile?.has_avatar) {
      if (avatarObjectUrlRef.current) {
        URL.revokeObjectURL(avatarObjectUrlRef.current);
        avatarObjectUrlRef.current = null;
      }
      setAvatarUrl(null);
      return;
    }
    let cancelled = false;
    api
      .getBlob("/api/profile/avatar")
      .then((blob) => {
        if (cancelled) return;
        if (avatarObjectUrlRef.current) {
          URL.revokeObjectURL(avatarObjectUrlRef.current);
        }
        const u = URL.createObjectURL(blob);
        avatarObjectUrlRef.current = u;
        setAvatarUrl(u);
      })
      .catch(() => {
        if (!cancelled) setAvatarUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [profile?.has_avatar]);

  useEffect(() => {
    api
      .get<Profile>("/api/profile")
      .then((p) =>
        setProfile({
          ...p,
          llm_provider: p.llm_provider ?? "openrouter",
          llm_api_key: p.llm_api_key ?? "",
          llm_model: p.llm_model ?? "anthropic/claude-sonnet-4.7",
          llm_temperature: typeof p.llm_temperature === "number" ? p.llm_temperature : 0.2,
        })
      )
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setSpotlightLoading(true);
    Promise.all([
      api.get<ResumeSpotlight>("/api/resume").catch(() => EMPTY_RESUME),
      api.get<SkillsSpotlight>("/api/skills").catch(() => EMPTY_SKILLS),
      api
        .get<Array<{ name?: string; description?: string }>>("/api/projects")
        .catch((): Array<{ name?: string; description?: string }> => []),
    ]).then(([r, s, projs]) => {
      if (cancelled) return;
      const summary = String(r.summary || "").trim();
      setResumePeek({
        summary: summary.length > 300 ? `${summary.slice(0, 297)}…` : summary,
        expCount: Array.isArray(r.experience) ? r.experience.length : 0,
        eduCount: Array.isArray(r.education) ? r.education.length : 0,
      });
      const pool = flattenSkillPool(s.categories || {}, s.items || []);
      const spot = s.skills_spotlight && s.skills_spotlight.length > 0 ? s.skills_spotlight : null;
      const tags = spot ? spot.filter((x) => pool.includes(x)) : pool;
      setSkillTags(tags);
      setSkillsCurated(!!spot);
      const list = Array.isArray(projs) ? projs : [];
      setProjectPeek(
        list.slice(0, 4).map((p) => ({
          name: p.name || "Untitled project",
          description: (p.description || "").trim().slice(0, 160),
        }))
      );
      setSpotlightLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      const updated = await api.put<Profile & { has_avatar?: boolean }>("/api/profile", {
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

  const handleAvatarUpload = async (file: File | null) => {
    if (!file || !profile) return;
    setAvatarBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.postForm("/api/profile/avatar", fd);
      setProfile({ ...profile, has_avatar: true });
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not upload photo");
    } finally {
      setAvatarBusy(false);
    }
  };

  const handleAvatarRemove = async () => {
    if (!profile) return;
    setAvatarBusy(true);
    setError("");
    try {
      await api.delete("/api/profile/avatar");
      setProfile({ ...profile, has_avatar: false });
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove photo");
    } finally {
      setAvatarBusy(false);
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

  const headline =
    (profile.pitch || "").split(/[.!\n]/)[0]?.trim() ||
    `${profile.default_focus || "Professional"} · ${profile.default_length || "resume"} defaults`;

  return (
    <Stack gap="xl" className="profile-page">
      <Paper className="app-card profile-hero-card" p={0} withBorder radius="lg">
        <Box className="profile-hero-cover" />
        <Box className="profile-hero-body">
          <Flex
            direction={{ base: "column", sm: "row" }}
            align={{ base: "stretch", sm: "flex-end" }}
            justify="space-between"
            gap={{ base: "lg", sm: "md" }}
            wrap="nowrap"
            style={{ minWidth: 0 }}
          >
            <Flex
              direction={{ base: "column", sm: "row" }}
              align={{ base: "center", sm: "flex-end" }}
              gap={{ base: "md", sm: "lg" }}
              style={{ minWidth: 0, flex: 1, width: "100%" }}
            >
              <Stack gap={6} align="center" style={{ flexShrink: 0 }}>
                <Avatar
                  className="profile-hero-avatar"
                  size={88}
                  radius="999"
                  color="amber"
                  variant="filled"
                  src={avatarUrl ?? undefined}
                >
                  {!avatarUrl ? initialsFromName(profile.name) : null}
                </Avatar>
                <Text size="xs" c="dimmed" ta="center" maw={280} lh={1.35}>
                  Optional—profile only, not your resume PDF.
                </Text>
                <Group gap={4} wrap="wrap" justify="center">
                  <FileButton onChange={handleAvatarUpload} accept="image/png,image/jpeg,image/webp,image/gif">
                    {(props) => (
                      <Button
                        {...props}
                        variant="light"
                        color="gray"
                        size="compact-xs"
                        leftSection={<IconPhoto size={14} />}
                        loading={avatarBusy}
                        disabled={avatarBusy}
                      >
                        {profile.has_avatar ? "Replace" : "Add photo"}
                      </Button>
                    )}
                  </FileButton>
                  {profile.has_avatar && (
                    <Button
                      variant="subtle"
                      color="gray"
                      size="compact-xs"
                      leftSection={<IconTrash size={14} />}
                      loading={avatarBusy}
                      disabled={avatarBusy}
                      onClick={handleAvatarRemove}
                    >
                      Remove
                    </Button>
                  )}
                </Group>
              </Stack>
              <Box
                style={{
                  minWidth: 0,
                  paddingBottom: 4,
                  width: "100%",
                  maxWidth: "100%",
                  flex: "1 1 auto",
                }}
              >
                <Title
                  order={2}
                  className="font-display"
                  ta={{ base: "center", sm: "left" }}
                  style={{ fontWeight: 800, lineHeight: 1.15, wordBreak: "break-word", overflowWrap: "anywhere" }}
                >
                  {profile.name || "Your name"}
                </Title>
                <Text className="profile-hero-headline" mt={6} ta={{ base: "center", sm: "left" }} style={{ maxWidth: "none" }}>
                  {headline}
                </Text>
                <Group gap="xs" mt="md" wrap="wrap" className="profile-hero-links">
                  {profile.email && (
                    <Anchor href={`mailto:${profile.email}`} size="sm" c="dimmed" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <IconMail size={16} style={{ opacity: 0.8 }} />
                      Email
                    </Anchor>
                  )}
                  {profile.linkedin && (
                    <Anchor href={profile.linkedin} target="_blank" rel="noreferrer" size="sm" c="dimmed" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <IconBrandLinkedin size={16} style={{ opacity: 0.8 }} />
                      LinkedIn
                    </Anchor>
                  )}
                  {profile.github && (
                    <Anchor href={profile.github} target="_blank" rel="noreferrer" size="sm" c="dimmed" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <IconBrandGithub size={16} style={{ opacity: 0.8 }} />
                      GitHub
                    </Anchor>
                  )}
                  {profile.website && (
                    <Anchor href={profile.website} target="_blank" rel="noreferrer" size="sm" c="dimmed" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <IconWorld size={16} style={{ opacity: 0.8 }} />
                      Website
                    </Anchor>
                  )}
                  {profile.phone && (
                    <Text size="sm" c="dimmed" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <IconPhone size={16} style={{ opacity: 0.8 }} />
                      {profile.phone}
                    </Text>
                  )}
                </Group>
              </Box>
            </Flex>
            <Button
              className="profile-hero-save"
              onClick={handleSave}
              loading={saving}
              color="amber"
              radius="md"
              size="sm"
              style={{ flexShrink: 0 }}
            >
              Save profile
            </Button>
          </Flex>
        </Box>
      </Paper>

      {success && (
        <Alert color="green" variant="light" radius="md">
          Profile saved.
        </Alert>
      )}
      {error && <Alert color="red">{error}</Alert>}

      <SimpleGrid
        cols={{ base: 1, sm: 3 }}
        spacing="md"
        style={{ alignItems: isSpotlight3Col ? "flex-start" : "stretch" }}
      >
        <Paper
          ref={resumeSpotlightRef}
          className="app-card profile-spotlight-card"
          p="lg"
          withBorder
          radius="lg"
          style={{
            borderColor: "var(--border-muted)",
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm" mb="sm">
            <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
              <ThemeIcon variant="light" color="blue" size="lg" radius="md">
                <IconBriefcase size={22} />
              </ThemeIcon>
              <Box style={{ minWidth: 0 }}>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }}>
                  Resume base
                </Text>
                <Text fw={600} className="font-display" mt={2}>
                  Preview
                </Text>
              </Box>
            </Group>
            <Button
              variant="subtle"
              size="xs"
              color="gray"
              leftSection={<IconRefresh size={14} />}
              onClick={() => setResumePreviewKey((k) => k + 1)}
              loading={resumePdfLoading}
            >
              Refresh
            </Button>
          </Group>
          <Text size="xs" c="dimmed" mb="sm">
            How your resume base looks as a PDF (same style as generated resumes). Edit the source on Resume base.
          </Text>
          <Box
            style={{
              width: "100%",
              height: 380,
              borderRadius: "var(--radius-md)",
              overflow: "hidden",
              background: "#525252",
              border: "1px solid var(--border-muted)",
              position: "relative",
            }}
          >
            {resumePdfLoading && (
              <Center h="100%">
                <Loader color="amber" />
              </Center>
            )}
            {resumePdfError && !resumePdfLoading && (
              <Center h="100%" p="md">
                <Stack align="center" gap="sm">
                  <Text size="sm" c="dimmed" ta="center">
                    Couldn&apos;t load preview. Try Refresh, or open Resume base below.
                  </Text>
                  <Button component={Link} to="/dashboard/profile/resume" size="xs" variant="light" color="amber">
                    Open Resume base
                  </Button>
                </Stack>
              </Center>
            )}
            {resumePdfUrl && !resumePdfLoading && !resumePdfError && (
              <iframe
                title="Resume base PDF preview"
                src={`${resumePdfUrl}#view=FitH`}
                style={{
                  width: "100%",
                  height: "100%",
                  border: "none",
                  display: "block",
                  background: "#fff",
                }}
              />
            )}
          </Box>
          <Button
            component={Link}
            to="/dashboard/profile/resume"
            fullWidth
            mt="md"
            color="amber"
            radius="md"
            leftSection={<IconPencil size={18} />}
            rightSection={<IconArrowRight size={16} />}
          >
            Edit resume base
          </Button>
          {!spotlightLoading && resumePeek && (resumePeek.expCount > 0 || resumePeek.eduCount > 0) && (
            <Text size="xs" c="dimmed" mt="sm" ta="center">
              {resumePeek.expCount > 0 && `${resumePeek.expCount} role${resumePeek.expCount === 1 ? "" : "s"}`}
              {resumePeek.expCount > 0 && resumePeek.eduCount > 0 && " · "}
              {resumePeek.eduCount > 0 && `${resumePeek.eduCount} education`}
            </Text>
          )}
        </Paper>

        <Paper
          component={Link}
          to="/dashboard/profile/skills"
          className="app-card profile-spotlight-card"
          p="lg"
          withBorder
          radius="lg"
          style={{
            textDecoration: "none",
            color: "inherit",
            borderColor: "var(--border-muted)",
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            ...(isSpotlight3Col
              ? {
                  height: spotlightRowHeightPx,
                  maxHeight: spotlightRowHeightPx,
                  overflow: "hidden",
                }
              : {}),
          }}
        >
          <Box style={{ flexShrink: 0 }}>
            <ThemeIcon variant="light" color="amber" size="lg" radius="md" mb="sm">
              <IconCode size={22} />
            </ThemeIcon>
            <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }}>
              Skills
            </Text>
            <Text fw={600} className="font-display" mt={4}>
              Your toolkit
            </Text>
            <Text size="xs" c="dimmed" mt={4}>
              {skillsCurated
                ? `${skillTags.length} selected for profile — pick more on Skills.`
                : skillTags.length > 0
                  ? `All ${skillTags.length} skills — curate on Skills if you want fewer badges.`
                  : ""}
            </Text>
          </Box>
          <Box
            style={{
              flex: isSpotlight3Col ? "1 1 0%" : undefined,
              minHeight: isSpotlight3Col ? 0 : undefined,
              maxHeight: isSpotlight3Col ? undefined : 320,
              marginTop: "var(--mantine-spacing-md)",
              overflowY: "auto",
              overflowX: "hidden",
              WebkitOverflowScrolling: "touch",
            }}
          >
            <Group gap={6} wrap="wrap" align="flex-start">
              {spotlightLoading ? (
                <Loader size="sm" color="amber" />
              ) : skillTags.length === 0 ? (
                <Text size="xs" c="dimmed">
                  Add skills for better keyword matching.
                </Text>
              ) : (
                skillTags.map((t) => (
                  <Badge
                    key={t}
                    variant="light"
                    color="amber"
                    size="sm"
                    radius="md"
                    style={{ maxWidth: "100%", height: "auto", whiteSpace: "normal" }}
                  >
                    {t}
                  </Badge>
                ))
              )}
            </Group>
          </Box>
          <Group gap={4} mt="md" c="amber" style={{ flexShrink: 0, marginTop: "auto", paddingTop: "var(--mantine-spacing-md)" }}>
            <Text size="xs" fw={600}>
              Manage skills
            </Text>
            <IconArrowRight size={14} />
          </Group>
        </Paper>

        <Paper
          component={Link}
          to="/dashboard/profile/projects"
          className="app-card profile-spotlight-card"
          p="lg"
          withBorder
          radius="lg"
          style={{
            textDecoration: "none",
            color: "inherit",
            borderColor: "var(--border-muted)",
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            ...(isSpotlight3Col
              ? {
                  height: spotlightRowHeightPx,
                  maxHeight: spotlightRowHeightPx,
                  overflow: "hidden",
                }
              : {}),
          }}
        >
          <Box style={{ flexShrink: 0 }}>
            <ThemeIcon variant="light" color="grape" size="lg" radius="md" mb="sm">
              <IconFolder size={22} />
            </ThemeIcon>
            <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }}>
              Projects
            </Text>
            <Text fw={600} className="font-display" mt={4}>
              Featured work
            </Text>
          </Box>
          <Box
            style={{
              flex: isSpotlight3Col ? "1 1 0%" : undefined,
              minHeight: isSpotlight3Col ? 0 : undefined,
              maxHeight: isSpotlight3Col ? undefined : 280,
              marginTop: "var(--mantine-spacing-sm)",
              overflowY: "auto",
              overflowX: "hidden",
            }}
          >
            <Stack gap="xs">
              {spotlightLoading ? (
                <Loader size="sm" color="amber" />
              ) : projectPeek.length === 0 ? (
                <Text size="xs" c="dimmed">
                  Add projects to highlight in tailored resumes.
                </Text>
              ) : (
                projectPeek.map((p, i) => (
                  <Box key={`${p.name}-${i}`} className="profile-project-snippet">
                    <Text size="sm" fw={600} lineClamp={1}>
                      {p.name}
                    </Text>
                    {p.description && (
                      <Text size="xs" c="dimmed" lineClamp={2} mt={4}>
                        {p.description}
                      </Text>
                    )}
                  </Box>
                ))
              )}
            </Stack>
          </Box>
          <Group gap={4} c="amber" style={{ flexShrink: 0, marginTop: "auto", paddingTop: "var(--mantine-spacing-md)" }}>
            <Text size="xs" fw={600}>
              All projects
            </Text>
            <IconArrowRight size={14} />
          </Group>
        </Paper>
      </SimpleGrid>

      <Paper className="app-card" p="lg" withBorder radius="lg" style={{ borderColor: "var(--border-muted)" }}>
        <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="md">
          About
        </Text>
        <Textarea
          label="Headline & pitch"
          description="Shown in cover letters and as your profile tagline above when you add more detail."
          value={profile.pitch}
          onChange={(e) => setProfile({ ...profile, pitch: e.target.value })}
          placeholder="e.g. Senior backend engineer · Python, distributed systems · Open to remote roles."
          minRows={4}
          radius="md"
        />
      </Paper>

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Divider label="Contact & links" labelPosition="left" mb="lg" />
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <TextInput
            label="Name"
            value={profile.name}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })}
            placeholder="Your name"
            radius="md"
          />
          <TextInput
            label="Email"
            type="email"
            value={profile.email}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })}
            placeholder="you@example.com"
            radius="md"
          />
          <TextInput
            label="Phone"
            value={profile.phone}
            onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            placeholder="+1 234 567 8900"
            radius="md"
          />
          <TextInput
            label="LinkedIn"
            value={profile.linkedin}
            onChange={(e) => setProfile({ ...profile, linkedin: e.target.value })}
            placeholder="https://linkedin.com/in/..."
            radius="md"
          />
          <TextInput
            label="Website"
            value={profile.website}
            onChange={(e) => setProfile({ ...profile, website: e.target.value })}
            placeholder="https://yoursite.com"
            radius="md"
          />
          <TextInput
            label="GitHub"
            value={profile.github}
            onChange={(e) => setProfile({ ...profile, github: e.target.value })}
            placeholder="https://github.com/..."
            radius="md"
          />
        </SimpleGrid>
      </Paper>

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Divider label="Generation defaults" labelPosition="left" mb="lg" />
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <Select
            label="Default tone"
            data={TONE_OPTIONS}
            value={profile.default_tone}
            onChange={(v) => v && setProfile({ ...profile, default_tone: v })}
            radius="md"
          />
          <Select
            label="Default focus"
            data={FOCUS_OPTIONS}
            value={profile.default_focus}
            onChange={(v) => v && setProfile({ ...profile, default_focus: v })}
            radius="md"
          />
          <Select
            label="Default length"
            data={LENGTH_OPTIONS}
            value={profile.default_length}
            onChange={(v) => v && setProfile({ ...profile, default_length: v })}
            radius="md"
          />
        </SimpleGrid>
      </Paper>

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Divider label="Optional: AI-assisted wording" labelPosition="left" mb="md" />
        <Text size="xs" c="dimmed" mb="lg">
          Add a provider and API key to refine resume and cover letter wording with AI. Without a key, JobKit builds drafts from your profile and job match; you edit and export as usual.
        </Text>
        <Stack gap="md">
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
            radius="md"
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
            description="Stored in your profile; used only when you generate (optional)."
            radius="md"
          />
          <Select
            label="Model"
            data={LLM_MODEL_OPTIONS_BY_PROVIDER[(profile.llm_provider || "openrouter") as LLMProvider].map((o) => ({
              value: o.value,
              label: o.label,
            }))}
            value={profile.llm_model || DEFAULT_MODEL_BY_PROVIDER[(profile.llm_provider || "openrouter") as LLMProvider]}
            onChange={(v) => v && setProfile({ ...profile, llm_model: v })}
            radius="md"
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

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Divider label="Google Drive & Sheets" labelPosition="left" mb="md" />
        <Text size="xs" c="dimmed" mb="md">
          Connect (or reconnect) Google here, then set these to sync jobs to your folder and tracker sheet. If a sync ever reports your connection expired, use Reconnect below.
        </Text>
        <Box mb="lg">
          <GoogleStatus allowReconnect />
        </Box>
        <Stack gap="md">
          <TextInput
            label="Drive root folder ID"
            value={profile.google_drive_root_folder_id ?? ""}
            onChange={(e) => setProfile({ ...profile, google_drive_root_folder_id: e.target.value })}
            placeholder="e.g. 1ABC...xyz (from folder URL)"
            description="Uploads go under this folder. Empty = create a JobKit folder in Drive."
            radius="md"
          />
          <TextInput
            label="Sheets spreadsheet ID"
            value={profile.google_sheets_spreadsheet_id ?? ""}
            onChange={(e) => setProfile({ ...profile, google_sheets_spreadsheet_id: e.target.value })}
            placeholder="e.g. 1tBEe... (from spreadsheet URL)"
            description="Only used when set. Job updates sync to this sheet."
            radius="md"
          />
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <TextInput
              label="Sheet tab name"
              value={profile.google_sheets_tab_name ?? ""}
              onChange={(e) => setProfile({ ...profile, google_sheets_tab_name: e.target.value })}
              placeholder="e.g. Job Applications"
              radius="md"
            />
            <TextInput
              label="Job URL column name"
              value={profile.google_sheets_url_column ?? ""}
              onChange={(e) => setProfile({ ...profile, google_sheets_url_column: e.target.value })}
              placeholder="Job URL (default)"
              radius="md"
            />
          </SimpleGrid>
        </Stack>
      </Paper>

      <Group justify="flex-end">
        <Button onClick={handleSave} loading={saving} color="amber" radius="md" size="md">
          Save profile
        </Button>
      </Group>
    </Stack>
  );
}
