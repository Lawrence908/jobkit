import { useEffect, useState } from "react";
import {
  Title,
  Stack,
  TextInput,
  Textarea,
  Button,
  Loader,
  Center,
  Alert,
  Text,
  Group,
  Card,
  ActionIcon,
  Modal,
} from "@mantine/core";
import { IconPlus, IconTrash, IconEdit } from "@tabler/icons-react";
import { api } from "../api/client";

export interface ProjectData {
  id?: number;
  name: string;
  description: string;
  link: string;
  status: string;
  dates: string;
  tags: string[];
  tech_stack: string[];
  bullets: string[];
}

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ProjectData | null>(null);
  const [form, setForm] = useState<ProjectData>({
    name: "",
    description: "",
    link: "",
    status: "",
    dates: "",
    tags: [],
    tech_stack: [],
    bullets: [],
  });

  const load = () => {
    setLoading(true);
    api
      .get<ProjectData[]>("/api/projects")
      .then(setProjects)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load projects"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", description: "", link: "", status: "", dates: "", tags: [], tech_stack: [], bullets: [] });
    setModalOpen(true);
  };

  const openEdit = (p: ProjectData) => {
    setEditing(p);
    setForm({
      name: p.name || "",
      description: p.description || "",
      link: p.link || "",
      status: p.status || "",
      dates: p.dates || "",
      tags: p.tags || [],
      tech_stack: p.tech_stack || [],
      bullets: p.bullets || [],
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    setError("");
    try {
      if (editing?.id) {
        await api.put(`/api/projects/${editing.id}`, form);
      } else {
        await api.post("/api/projects", form);
      }
      setModalOpen(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this project?")) return;
    try {
      await api.delete(`/api/projects/${id}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  if (loading && projects.length === 0) {
    return (
      <Center py="xl">
        <Loader color="amber" />
      </Center>
    );
  }

  return (
    <Stack gap="xl" style={{ width: "100%", maxWidth: 800 }}>
      <Group justify="space-between">
        <div>
          <Title order={3} className="font-display" style={{ fontWeight: 700 }}>
            Projects
          </Title>
          <Text size="sm" c="dimmed">
            Projects used when tailoring resumes. When using Postgres, add and edit here.
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} color="amber" variant="filled" onClick={openCreate}>
          Add project
        </Button>
      </Group>

      {error && <Alert color="red">{error}</Alert>}

      {Array.isArray(projects) && projects.length === 0 ? (
        <Text size="sm" c="dimmed">
          No projects yet. Add one to use in tailoring.
        </Text>
      ) : (
        <Stack gap="md">
          {(projects || []).map((p) => (
            <Card key={p.id ?? p.name} withBorder padding="md" radius="lg">
              <Group justify="space-between">
                <div>
                  <Text fw={600}>{p.name || "Untitled"}</Text>
                  <Text size="sm" c="dimmed" lineClamp={2}>
                    {p.description}
                  </Text>
                </div>
                <Group>
                  <ActionIcon variant="subtle" onClick={() => openEdit(p)} aria-label="Edit">
                    <IconEdit size={16} />
                  </ActionIcon>
                  {p.id != null && (
                    <ActionIcon color="red" variant="subtle" onClick={() => handleDelete(p.id!)} aria-label="Delete">
                      <IconTrash size={16} />
                    </ActionIcon>
                  )}
                </Group>
              </Group>
            </Card>
          ))}
        </Stack>
      )}

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Edit project" : "New project"} size="md">
        <Stack gap="md">
          <TextInput
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Project name"
          />
          <Textarea
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Short description (grows with content)"
            minRows={3}
            maxRows={12}
            autosize
          />
          <TextInput
            label="Link"
            value={form.link}
            onChange={(e) => setForm({ ...form, link: e.target.value })}
            placeholder="https://..."
          />
          <TextInput
            label="Status"
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
            placeholder="e.g. Production"
          />
          <TextInput
            label="Dates"
            value={form.dates}
            onChange={(e) => setForm({ ...form, dates: e.target.value })}
            placeholder="e.g. 2024–present"
          />
          <Textarea
            label="Tags (one per line)"
            value={(form.tags || []).join("\n")}
            onChange={(e) => setForm({ ...form, tags: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
            placeholder="python&#10;docker&#10;react"
            minRows={2}
            maxRows={6}
            autosize
          />
          <Textarea
            label="Tech stack (one per line)"
            value={(form.tech_stack || []).join("\n")}
            onChange={(e) => setForm({ ...form, tech_stack: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
            placeholder="Python&#10;FastAPI&#10;PostgreSQL"
            minRows={2}
            maxRows={8}
            autosize
          />
          <Textarea
            label="Bullets (one per line)"
            value={(form.bullets || []).join("\n")}
            onChange={(e) => setForm({ ...form, bullets: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
            placeholder="Key achievement or outcome..."
            minRows={3}
            maxRows={12}
            autosize
          />
          <Button onClick={handleSave} color="amber">
            {editing ? "Save" : "Create"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
