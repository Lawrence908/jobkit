import { useEffect, useState } from "react";
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
} from "@mantine/core";
import { api } from "../api/client";

interface SkillsData {
  categories: Record<string, string[]>;
  items: string[];
}

/** Category headings for Skills JSON (match data/skills.yml). Pre-filled when empty so structure is obvious. */
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

function ensureCategories(categories: Record<string, string[]> | null | undefined): Record<string, string[]> {
  if (categories && Object.keys(categories).length > 0) return categories;
  return { ...DEFAULT_CATEGORIES_STRUCTURE };
}

export function SkillsPage() {
  const [data, setData] = useState<SkillsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    api
      .get<SkillsData>("/api/skills")
      .then((res) => {
        setData({
          categories: ensureCategories(res.categories),
          items: res.items || [],
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load skills"))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      await api.put("/api/skills", data);
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

  if (!data) {
    return (
      <div className="page-container--narrow" style={{ paddingTop: "1rem" }}>
        <Alert color="red">{error || "Failed to load skills"}</Alert>
      </div>
    );
  }

  const categoriesStr = JSON.stringify(data.categories || {}, null, 2);
  const itemsStr = (data.items || []).join("\n");

  return (
    <Stack gap="xl" style={{ width: "100%", maxWidth: 720 }}>
      <Title order={3} className="font-display" style={{ fontWeight: 700 }}>
        Skills
      </Title>
      <Text size="sm" c="dimmed">
        Categorized skills and flat keyword list used for tailoring. When using Postgres, edits are saved here.
      </Text>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Text size="sm" fw={600} className="font-display" mb="xs">
          Categories (JSON)
        </Text>
        <Text size="xs" c="dimmed" mb="sm">
          Object with category names as keys, arrays of skill strings as values. Example keys: languages_frameworks, apis_services, tools_platforms, databases_orm, testing_quality, concepts, visualization_ui, domain_expertise.
        </Text>
        <Textarea
          value={categoriesStr}
          onChange={(e) => {
            try {
              const categories = JSON.parse(e.target.value || "{}");
              if (typeof categories === "object" && categories !== null) {
                setData({ ...data, categories });
              }
            } catch {
              // ignore invalid JSON while typing
            }
          }}
          placeholder={JSON.stringify(DEFAULT_CATEGORIES_STRUCTURE, null, 2)}
          minRows={12}
          maxRows={28}
          autosize
        />
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Text size="sm" fw={600} className="font-display" mb="sm">
          Flat keywords (one per line)
        </Text>
        <Textarea
          value={itemsStr}
          onChange={(e) => setData({ ...data, items: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
          placeholder="Python&#10;JavaScript&#10;Docker"
          minRows={6}
          maxRows={20}
          autosize
        />
      </Paper>

      {error && <Alert color="red">{error}</Alert>}
      {success && <Alert color="green">Skills saved.</Alert>}

      <Button onClick={handleSave} loading={saving} color="amber" variant="filled">
        Save skills
      </Button>
    </Stack>
  );
}
