import { useEffect, useState } from "react";
import {
  Title,
  Stack,
  Paper,
  TextInput,
  Textarea,
  Button,
  Loader,
  Center,
  Alert,
  Text,
  Group,
  ActionIcon,
} from "@mantine/core";
import { IconPlus, IconTrash } from "@tabler/icons-react";
import { api } from "../api/client";

export interface ResumeBaseData {
  contact: Record<string, string>;
  summary: string;
  highlights_of_qualifications: string[];
  technical_snapshot: Record<string, string[]>;
  experience: Array<{ role?: string; company?: string; dates?: string; bullets?: string[] }>;
  education: Array<{ school?: string; degree?: string; dates?: string }>;
  certifications: string[];
}

/** Template keys for technical_snapshot (match data/resume_base.yml). Shown when empty so structure is obvious. */
const TECHNICAL_SNAPSHOT_TEMPLATE: Record<string, string[]> = {
  languages: [],
  frameworks: [],
  platforms: [],
  databases: [],
  apis: [],
};

const defaultResume: ResumeBaseData = {
  contact: {},
  summary: "",
  highlights_of_qualifications: [],
  technical_snapshot: {},
  experience: [],
  education: [],
  certifications: [],
};

function ensureTechnicalSnapshot(snap: Record<string, string[]> | null | undefined): Record<string, string[]> {
  if (snap && Object.keys(snap).length > 0) return snap;
  return { ...TECHNICAL_SNAPSHOT_TEMPLATE };
}

export function ResumePage() {
  const [data, setData] = useState<ResumeBaseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    api
      .get<ResumeBaseData>("/api/resume")
      .then((res) => {
        const merged = { ...defaultResume, ...res };
        merged.technical_snapshot = ensureTechnicalSnapshot(merged.technical_snapshot);
        setData(merged);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load resume"))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      await api.put("/api/resume", data);
      setSuccess(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const updateHighlight = (index: number, value: string) => {
    if (!data) return;
    const next = [...(data.highlights_of_qualifications || [])];
    next[index] = value;
    setData({ ...data, highlights_of_qualifications: next });
  };
  const addHighlight = () => {
    if (!data) return;
    setData({
      ...data,
      highlights_of_qualifications: [...(data.highlights_of_qualifications || []), ""],
    });
  };
  const removeHighlight = (index: number) => {
    if (!data) return;
    const next = (data.highlights_of_qualifications || []).filter((_, i) => i !== index);
    setData({ ...data, highlights_of_qualifications: next });
  };

  const setTechnicalSnapshotFromJson = (raw: string) => {
    if (!data) return;
    try {
      const parsed = JSON.parse(raw || "{}");
      if (typeof parsed === "object" && parsed !== null) {
        const out: Record<string, string[]> = {};
        for (const [k, v] of Object.entries(parsed)) {
          out[k] = Array.isArray(v) ? v.map(String) : [];
        }
        setData({ ...data, technical_snapshot: out });
      }
    } catch {
      // ignore invalid JSON while typing
    }
  };

  const updateExperience = (index: number, field: "role" | "company" | "dates" | "bullets", value: string | string[]) => {
    if (!data) return;
    const next = [...(data.experience || [])];
    next[index] = { ...next[index], [field]: value };
    setData({ ...data, experience: next });
  };
  const updateExperienceBullet = (expIndex: number, bulletIndex: number, value: string) => {
    if (!data) return;
    const next = [...(data.experience || [])];
    const bullets = [...(next[expIndex]?.bullets || [])];
    bullets[bulletIndex] = value;
    next[expIndex] = { ...next[expIndex], bullets };
    setData({ ...data, experience: next });
  };
  const addExperienceBullet = (expIndex: number) => {
    if (!data) return;
    const next = [...(data.experience || [])];
    next[expIndex] = { ...next[expIndex], bullets: [...(next[expIndex]?.bullets || []), ""] };
    setData({ ...data, experience: next });
  };
  const removeExperienceBullet = (expIndex: number, bulletIndex: number) => {
    if (!data) return;
    const next = [...(data.experience || [])];
    next[expIndex] = {
      ...next[expIndex],
      bullets: (next[expIndex]?.bullets || []).filter((_, i) => i !== bulletIndex),
    };
    setData({ ...data, experience: next });
  };
  const addExperience = () => {
    if (!data) return;
    setData({ ...data, experience: [...(data.experience || []), { role: "", company: "", dates: "", bullets: [] }] });
  };
  const removeExperience = (index: number) => {
    if (!data) return;
    setData({ ...data, experience: (data.experience || []).filter((_, i) => i !== index) });
  };

  const updateEducation = (index: number, field: "school" | "degree" | "dates", value: string) => {
    if (!data) return;
    const next = [...(data.education || [])];
    next[index] = { ...next[index], [field]: value };
    setData({ ...data, education: next });
  };
  const addEducation = () => {
    if (!data) return;
    setData({ ...data, education: [...(data.education || []), { school: "", degree: "", dates: "" }] });
  };
  const removeEducation = (index: number) => {
    if (!data) return;
    setData({ ...data, education: (data.education || []).filter((_, i) => i !== index) });
  };

  const updateCertification = (index: number, value: string) => {
    if (!data) return;
    const next = [...(data.certifications || [])];
    next[index] = value;
    setData({ ...data, certifications: next });
  };
  const addCertification = () => {
    if (!data) return;
    setData({ ...data, certifications: [...(data.certifications || []), ""] });
  };
  const removeCertification = (index: number) => {
    if (!data) return;
    setData({ ...data, certifications: (data.certifications || []).filter((_, i) => i !== index) });
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
        <Alert color="red">{error || "Failed to load resume"}</Alert>
      </div>
    );
  }

  const contact = data.contact || {};
  const technicalSnapshotStr = JSON.stringify(data.technical_snapshot || {}, null, 2);

  return (
    <Stack gap="xl" style={{ width: "100%", maxWidth: 720 }}>
      <Title order={3} className="font-display" style={{ fontWeight: 700 }}>
        Resume base
      </Title>
      <Text size="sm" c="dimmed">
        Master resume data used for tailoring. Edit contact, summary, highlights, technical snapshot, experience, education, and certifications.
      </Text>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Text size="sm" fw={600} className="font-display">
            Contact
          </Text>
          <TextInput
            label="Name"
            value={contact.name ?? ""}
            onChange={(e) => setData({ ...data, contact: { ...contact, name: e.target.value } })}
            placeholder="Your name"
          />
          <TextInput
            label="Email"
            type="email"
            value={contact.email ?? ""}
            onChange={(e) => setData({ ...data, contact: { ...contact, email: e.target.value } })}
            placeholder="you@example.com"
          />
          <TextInput
            label="Phone"
            value={contact.phone ?? ""}
            onChange={(e) => setData({ ...data, contact: { ...contact, phone: e.target.value } })}
            placeholder="+1 234 567 8900"
          />
          <TextInput
            label="LinkedIn"
            value={contact.linkedin ?? ""}
            onChange={(e) => setData({ ...data, contact: { ...contact, linkedin: e.target.value } })}
            placeholder="https://linkedin.com/in/..."
          />
          <TextInput
            label="Website"
            value={contact.website ?? ""}
            onChange={(e) => setData({ ...data, contact: { ...contact, website: e.target.value } })}
            placeholder="https://yoursite.com"
          />
          <TextInput
            label="GitHub"
            value={contact.github ?? ""}
            onChange={(e) => setData({ ...data, contact: { ...contact, github: e.target.value } })}
            placeholder="https://github.com/..."
          />
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Text size="sm" fw={600} className="font-display" mb="sm">
          Summary
        </Text>
        <Textarea
          value={data.summary}
          onChange={(e) => setData({ ...data, summary: e.target.value })}
          placeholder="Short professional summary..."
          minRows={4}
          maxRows={14}
          autosize
        />
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Group justify="space-between" mb="sm">
          <Text size="sm" fw={600} className="font-display">
            Highlights of qualifications
          </Text>
          <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addHighlight}>
            Add
          </Button>
        </Group>
        <Stack gap="xs">
          {(data.highlights_of_qualifications || []).map((line, i) => (
            <Group key={i} gap="xs" wrap="nowrap" align="flex-start">
              <Textarea
                value={line}
                onChange={(e) => updateHighlight(i, e.target.value)}
                placeholder="One bullet point..."
                minRows={1}
                maxRows={6}
                autosize
                style={{ flex: 1 }}
              />
              <ActionIcon color="red" variant="subtle" onClick={() => removeHighlight(i)} aria-label="Remove">
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Text size="sm" fw={600} className="font-display" mb="xs">
          Technical snapshot
        </Text>
        <Text size="xs" c="dimmed" mb="sm">
          JSON: object with category keys (e.g. languages, frameworks, platforms, databases, apis) and arrays of strings as values.
        </Text>
        <Textarea
          value={technicalSnapshotStr}
          onChange={(e) => setTechnicalSnapshotFromJson(e.target.value)}
          placeholder={JSON.stringify(TECHNICAL_SNAPSHOT_TEMPLATE, null, 2)}
          minRows={8}
          maxRows={20}
          autosize
        />
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Group justify="space-between" mb="sm">
          <Text size="sm" fw={600} className="font-display">
            Experience
          </Text>
          <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addExperience}>
            Add role
          </Button>
        </Group>
        <Stack gap="md">
          {(data.experience || []).map((exp, expIdx) => (
            <Stack key={expIdx} gap="xs" p="sm" style={{ border: "1px solid var(--border-muted)", borderRadius: 8 }}>
              <Group justify="space-between" wrap="nowrap">
                <Text size="xs" fw={600}>Role {expIdx + 1}</Text>
                <ActionIcon color="red" variant="subtle" size="sm" onClick={() => removeExperience(expIdx)} aria-label="Remove role">
                  <IconTrash size={14} />
                </ActionIcon>
              </Group>
              <TextInput
                label="Role"
                value={exp.role ?? ""}
                onChange={(e) => updateExperience(expIdx, "role", e.target.value)}
                placeholder="Job title"
                size="xs"
              />
              <TextInput
                label="Company"
                value={exp.company ?? ""}
                onChange={(e) => updateExperience(expIdx, "company", e.target.value)}
                placeholder="Company name"
                size="xs"
              />
              <TextInput
                label="Dates"
                value={exp.dates ?? ""}
                onChange={(e) => updateExperience(expIdx, "dates", e.target.value)}
                placeholder="e.g. 2022–2024"
                size="xs"
              />
              <div>
                <Group justify="space-between" mb={4}>
                  <Text size="xs" fw={500}>Bullets</Text>
                  <Button size="xs" variant="subtle" leftSection={<IconPlus size={12} />} onClick={() => addExperienceBullet(expIdx)}>
                    Add
                  </Button>
                </Group>
                <Stack gap={4}>
                  {(exp.bullets || []).map((bullet, bIdx) => (
                    <Group key={bIdx} gap="xs" wrap="nowrap" align="flex-start">
                      <Textarea
                        value={bullet}
                        onChange={(e) => updateExperienceBullet(expIdx, bIdx, e.target.value)}
                        placeholder="Achievement or responsibility..."
                        minRows={1}
                        maxRows={4}
                        autosize
                        size="xs"
                        style={{ flex: 1 }}
                      />
                      <ActionIcon color="red" variant="subtle" size="sm" onClick={() => removeExperienceBullet(expIdx, bIdx)} aria-label="Remove bullet">
                        <IconTrash size={14} />
                      </ActionIcon>
                    </Group>
                  ))}
                </Stack>
              </div>
            </Stack>
          ))}
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Group justify="space-between" mb="sm">
          <Text size="sm" fw={600} className="font-display">
            Education
          </Text>
          <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addEducation}>
            Add
          </Button>
        </Group>
        <Stack gap="sm">
          {(data.education || []).map((edu, i) => (
            <Group key={i} gap="sm" wrap="nowrap" align="flex-start">
              <TextInput
                label="School"
                value={edu.school ?? ""}
                onChange={(e) => updateEducation(i, "school", e.target.value)}
                placeholder="School name"
                size="xs"
                style={{ flex: 1 }}
              />
              <TextInput
                label="Degree"
                value={edu.degree ?? ""}
                onChange={(e) => updateEducation(i, "degree", e.target.value)}
                placeholder="Degree or credential"
                size="xs"
                style={{ flex: 1 }}
              />
              <TextInput
                label="Dates"
                value={edu.dates ?? ""}
                onChange={(e) => updateEducation(i, "dates", e.target.value)}
                placeholder="e.g. 2024"
                size="xs"
                style={{ width: 100 }}
              />
              <ActionIcon color="red" variant="subtle" mt={22} onClick={() => removeEducation(i)} aria-label="Remove">
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
        </Stack>
      </Paper>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Group justify="space-between" mb="sm">
          <Text size="sm" fw={600} className="font-display">
            Certifications
          </Text>
          <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addCertification}>
            Add
          </Button>
        </Group>
        <Stack gap="xs">
          {(data.certifications || []).map((line, i) => (
            <Group key={i} gap="xs" wrap="nowrap" align="flex-start">
              <TextInput
                value={line}
                onChange={(e) => updateCertification(i, e.target.value)}
                placeholder="Certification name"
                size="sm"
                style={{ flex: 1 }}
              />
              <ActionIcon color="red" variant="subtle" onClick={() => removeCertification(i)} aria-label="Remove">
                <IconTrash size={16} />
              </ActionIcon>
            </Group>
          ))}
        </Stack>
      </Paper>

      {error && <Alert color="red">{error}</Alert>}
      {success && <Alert color="green">Resume base saved.</Alert>}

      <Button onClick={handleSave} loading={saving} color="amber" variant="filled">
        Save resume base
      </Button>
    </Stack>
  );
}
