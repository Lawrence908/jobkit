import { useEffect, useMemo, useState } from "react";
import {
  Title,
  Stack,
  Paper,
  Textarea,
  Button,
  Loader,
  Center,
  Alert,
  Text,
  Group,
  TextInput,
  ActionIcon,
  Accordion,
  SegmentedControl,
  ScrollArea,
  Badge,
} from "@mantine/core";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { api } from "../api/client";
import { flattenSkillPool } from "../utils/skills";

interface SkillsData {
  categories: Record<string, string[]>;
  items: string[];
  skills_spotlight?: string[] | null;
}

const DEFAULT_CATEGORIES_STRUCTURE: Record<string, string[]> = {
  languages_frameworks: [],
  apis_services: [],
  tools_platforms: [],
  databases_orm: [],
  testing_quality: [],
  concepts: [],
  visualization_ui: [],
  domain_expertise: [],
};

const CATEGORY_LABELS: Record<string, string> = {
  languages_frameworks: "Languages & frameworks",
  apis_services: "APIs & services",
  tools_platforms: "Tools & platforms",
  databases_orm: "Databases & ORM",
  testing_quality: "Testing & quality",
  concepts: "Concepts",
  visualization_ui: "Visualization & UI",
  domain_expertise: "Domain expertise",
};

function humanizeCategory(key: string): string {
  return CATEGORY_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function ensureCategories(categories: Record<string, string[]> | null | undefined): Record<string, string[]> {
  const base = { ...DEFAULT_CATEGORIES_STRUCTURE };
  if (categories && typeof categories === "object") {
    for (const [k, v] of Object.entries(categories)) {
      if (Array.isArray(v)) base[k] = [...v];
      else if (!(k in base)) base[k] = [];
    }
  }
  return base;
}

export function SkillsPage() {
  const [data, setData] = useState<SkillsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [profileMode, setProfileMode] = useState<"all" | "pick">("all");
  const [spotlightPick, setSpotlightPick] = useState<Set<string>>(new Set());
  const [skillFilter, setSkillFilter] = useState("");

  useEffect(() => {
    api
      .get<SkillsData>("/api/skills")
      .then((res) => {
        const categories = ensureCategories(res.categories);
        const items = res.items || [];
        setData({ categories, items, skills_spotlight: res.skills_spotlight ?? null });
        const pool = flattenSkillPool(categories, items);
        if (res.skills_spotlight && res.skills_spotlight.length > 0) {
          setProfileMode("pick");
          setSpotlightPick(new Set(res.skills_spotlight.filter((x) => pool.includes(x))));
        } else {
          setProfileMode("all");
          setSpotlightPick(new Set(pool));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load skills"))
      .finally(() => setLoading(false));
  }, []);

  const pool = useMemo(() => (data ? flattenSkillPool(data.categories, data.items) : []), [data]);

  const filteredPool = useMemo(() => {
    const q = skillFilter.trim().toLowerCase();
    if (!q) return pool;
    return pool.filter((t) => t.toLowerCase().includes(q));
  }, [pool, skillFilter]);

  const categoryKeys = useMemo(() => {
    if (!data) return [];
    return [...new Set([...Object.keys(DEFAULT_CATEGORIES_STRUCTURE), ...Object.keys(data.categories)])].sort();
  }, [data]);

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setError("");
    setSuccess(false);
    const spotlight =
      profileMode === "all" ? null : [...spotlightPick].filter((x) => pool.includes(x));
    try {
      await api.put("/api/skills", {
        categories: data.categories,
        items: data.items,
        skills_spotlight: spotlight && spotlight.length > 0 ? spotlight : null,
      });
      setSuccess(true);
      setData((d) => (d ? { ...d, skills_spotlight: spotlight } : d));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const setCategoryLines = (key: string, lines: string[]) => {
    if (!data) return;
    setData({
      ...data,
      categories: { ...data.categories, [key]: lines.map((s) => s.trim()).filter(Boolean) },
    });
  };

  const addCategoryLine = (key: string) => {
    if (!data) return;
    const cur = data.categories[key] || [];
    setCategoryLines(key, [...cur, ""]);
  };

  const updateCategoryLine = (key: string, index: number, value: string) => {
    if (!data) return;
    const cur = [...(data.categories[key] || [])];
    while (cur.length <= index) cur.push("");
    cur[index] = value;
    setData({ ...data, categories: { ...data.categories, [key]: cur } });
  };

  const removeCategoryLine = (key: string, index: number) => {
    if (!data) return;
    const cur = [...(data.categories[key] || [])];
    cur.splice(index, 1);
    setCategoryLines(key, cur);
  };

  const toggleSpotlight = (tag: string) => {
    setSpotlightPick((prev) => {
      const n = new Set(prev);
      if (n.has(tag)) n.delete(tag);
      else n.add(tag);
      return n;
    });
  };

  const selectAllSpotlight = () => setSpotlightPick(new Set(pool));
  const clearSpotlight = () => setSpotlightPick(new Set());

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="amber" />
      </Center>
    );
  }

  if (!data) {
    return (
      <div className="page-container--narrow" style={{ paddingTop: "1rem" }}>
        <Alert color="red">{error || "Failed to load skills"}</Alert>
      </div>
    );
  }

  const itemsStr = (data.items || []).join("\n");

  return (
    <Stack gap="xl" className="profile-page" style={{ maxWidth: 880 }}>
      <div>
        <Title order={3} className="font-display" style={{ fontWeight: 700 }}>
          Skills
        </Title>
        <Text size="sm" c="dimmed" mt={6}>
          Edit by category, flat keywords for matching, and choose what appears on your JobKit profile card.
        </Text>
      </div>

      <Paper className="app-card" p="lg" withBorder radius="lg" style={{ borderColor: "var(--border-muted)" }}>
        <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="md">
          Profile card (dashboard)
        </Text>
        <Text size="sm" c="dimmed" mb="md">
          Match how badges look on your profile. <strong>Show all skills</strong> lists every unique skill from
          categories + flat list. <strong>Pick for profile</strong> lets you highlight only selected skills.
        </Text>
        <SegmentedControl
          value={profileMode}
          onChange={(v) => {
            const m = v as "all" | "pick";
            setProfileMode(m);
            if (m === "pick" && spotlightPick.size === 0) setSpotlightPick(new Set(pool));
          }}
          data={[
            { label: "Show all on profile", value: "all" },
            { label: "Pick for profile", value: "pick" },
          ]}
          fullWidth
          mb="md"
          radius="md"
        />
        {profileMode === "pick" && (
          <>
            <Group mb="sm" wrap="wrap">
              <TextInput
                placeholder="Filter skills…"
                value={skillFilter}
                onChange={(e) => setSkillFilter(e.target.value)}
                style={{ flex: "1 1 200px" }}
                radius="md"
              />
              <Button variant="light" size="xs" onClick={selectAllSpotlight}>
                Select all
              </Button>
              <Button variant="default" size="xs" onClick={clearSpotlight}>
                Clear
              </Button>
            </Group>
            <Text size="xs" c="dimmed" mb="xs">
              Click a skill to toggle. Amber = shown on profile ({spotlightPick.size} selected).
            </Text>
            <ScrollArea h={280} type="auto" offsetScrollbars>
              <Group gap={8} wrap="wrap">
                {filteredPool.map((tag) => (
                  <Badge
                    key={tag}
                    variant={spotlightPick.has(tag) ? "filled" : "outline"}
                    color="amber"
                    size="lg"
                    radius="md"
                    style={{ cursor: "pointer", maxWidth: "100%", height: "auto", whiteSpace: "normal", padding: "8px 12px" }}
                    onClick={() => toggleSpotlight(tag)}
                  >
                    {tag}
                  </Badge>
                ))}
              </Group>
            </ScrollArea>
            {filteredPool.length === 0 && <Text size="sm" c="dimmed">No skills match filter.</Text>}
          </>
        )}
      </Paper>

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="md">
          By category
        </Text>
        <Text size="sm" c="dimmed" mb="md">
          One entry per line per category. Add rows for longer descriptions (e.g. &quot;Python — FastAPI, Django&quot;).
        </Text>
        <Accordion variant="separated" radius="md">
          {categoryKeys.map((key) => {
            const lines = data.categories[key] || [];
            const displayLines = lines.length > 0 ? lines : [""];
            return (
              <Accordion.Item key={key} value={key}>
                <Accordion.Control>{humanizeCategory(key)}</Accordion.Control>
                <Accordion.Panel>
                  <Stack gap="sm">
                    {displayLines.map((line, i) => (
                      <Group key={i} gap="xs" wrap="nowrap" align="flex-start">
                        <TextInput
                          value={line}
                          onChange={(e) => updateCategoryLine(key, i, e.target.value)}
                          placeholder="Skill or stack description"
                          style={{ flex: 1 }}
                          radius="md"
                        />
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          onClick={() => removeCategoryLine(key, i)}
                          aria-label="Remove"
                          disabled={displayLines.length <= 1 && !line}
                        >
                          <IconTrash size={18} />
                        </ActionIcon>
                      </Group>
                    ))}
                    <Button
                      variant="light"
                      size="xs"
                      leftSection={<IconPlus size={14} />}
                      onClick={() => addCategoryLine(key)}
                    >
                      Add line
                    </Button>
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            );
          })}
        </Accordion>
      </Paper>

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Text size="sm" fw={600} className="font-display" mb="sm">
          Flat keywords (one per line)
        </Text>
        <Text size="xs" c="dimmed" mb="sm">
          Short tokens used for job keyword matching (Python, Docker, …). Appear in the profile pool and pick list.
        </Text>
        <Textarea
          value={itemsStr}
          onChange={(e) => setData({ ...data, items: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
          placeholder="Python&#10;FastAPI&#10;Docker"
          minRows={8}
          maxRows={24}
          autosize
          radius="md"
        />
      </Paper>

      {error && <Alert color="red">{error}</Alert>}
      {success && <Alert color="green">Skills saved.</Alert>}

      <Button onClick={handleSave} loading={saving} color="amber" variant="filled" radius="md" size="md">
        Save skills
      </Button>
    </Stack>
  );
}
