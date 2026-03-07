import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Stack,
  Group,
  Badge,
  Select,
  Paper,
  Text,
  TextInput,
  Button,
  Loader,
  Center,
  Alert,
} from "@mantine/core";
import { api } from "../api/client";
import type { Job } from "../api/types";
import { ApplicationFlow } from "../components/ApplicationFlow";

const STATUS_OPTIONS = ["New", "Tailored", "Applied", "Interviewing", "Rejected", "Offer"];

interface TailorPreview {
  keywords: string[];
  selected_projects: { name: string; description: string }[];
}

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [tailorPreview, setTailorPreview] = useState<TailorPreview | null>(null);

  useEffect(() => {
    if (!jobId) return;
    api
      .get<Job>(`/api/jobs/${jobId}`)
      .then((j) => {
        setJob(j);
        setStatus(j.status);
        setCompany(j.company ?? "");
        setRole(j.role ?? "");
        setLocation(j.location ?? "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load job"))
      .finally(() => setLoading(false));
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    api.get<TailorPreview>(`/api/jobs/${jobId}/tailor-preview`).then(setTailorPreview).catch(() => setTailorPreview(null));
  }, [jobId]);

  const handleStatusChange = async (value: string | null) => {
    if (!jobId || !value) return;
    await saveJob({ status: value });
    setStatus(value);
  };

  const saveJob = async (overrides?: { status?: string; company?: string; role?: string; location?: string }) => {
    if (!jobId) return;
    setSaving(true);
    setSaveMessage("");
    try {
      const body: { status?: string; company?: string; role?: string; location?: string } = {};
      if (overrides) {
        if (overrides.status !== undefined) body.status = overrides.status;
        if (overrides.company !== undefined) body.company = overrides.company;
        if (overrides.role !== undefined) body.role = overrides.role;
        if (overrides.location !== undefined) body.location = overrides.location;
      } else {
        body.status = status ?? undefined;
        body.company = company;
        body.role = role;
        body.location = location;
      }
      const updated = await api.patch<Job>(`/api/jobs/${jobId}`, body);
      setJob(updated);
      if (updated.status != null) setStatus(updated.status);
      if (updated.company != null) setCompany(updated.company);
      if (updated.role != null) setRole(updated.role);
      if (updated.location != null) setLocation(updated.location);
      setSaveMessage("Saved. Tracker updated.");
      setTimeout(() => setSaveMessage(""), 4000);
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
  if (error || !job) {
    return (
      <div className="page-container--narrow" style={{ paddingTop: "1rem" }}>
        <Alert color="red">{error || "Job not found"}</Alert>
      </div>
    );
  }

  return (
    <Stack gap="xl" style={{ width: "100%" }}>
      <Paper className="app-card" p="md" withBorder radius="lg">
        <Stack gap="md">
          <Group justify="space-between" wrap="wrap" align="flex-end" gap="md">
            <Text size="sm" fw={600} className="font-display">
              Job details
            </Text>
            <Group align="flex-end" gap="sm">
              <Select
                label="Status"
                data={STATUS_OPTIONS}
                value={status}
                onChange={handleStatusChange}
                disabled={saving}
                style={{ minWidth: 160 }}
              />
              <Button onClick={() => saveJob()} loading={saving} color="amber" size="sm">
                Save job
              </Button>
              {saveMessage && (
                <Text size="sm" c="dimmed" mb={4}>
                  {saveMessage}
                </Text>
              )}
            </Group>
          </Group>
          <TextInput
            label="Company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Company name"
          />
          <TextInput
            label="Role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="Job title / role"
          />
          <TextInput
            label="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Vancouver, Canada"
          />
          {job.url && (
            <Text size="sm">
              <strong>URL:</strong>{" "}
              <a href={job.url} target="_blank" rel="noreferrer">
                {job.url}
              </a>
            </Text>
          )}
          <Text size="sm">
            <strong>Source:</strong> {job.source || "—"}
          </Text>
        </Stack>
      </Paper>

      {job.keywords && job.keywords.length > 0 && (
        <Paper className="app-card" p="md" withBorder radius="lg">
          <Text size="sm" fw={600} mb="xs" className="font-display">
            Keywords
          </Text>
          <Group gap="xs">
            {job.keywords.map((k) => (
              <Badge key={k} variant="light" size="sm" color="amber">
                {k}
              </Badge>
            ))}
          </Group>
        </Paper>
      )}

      {tailorPreview && tailorPreview.selected_projects.length > 0 && (
        <Paper className="app-card" p="md" withBorder radius="lg">
          <Text size="sm" fw={600} mb="xs" className="font-display">
            Projects we&apos;ll emphasize
          </Text>
          <Text size="xs" c="dimmed" mb="xs">
            These projects will be included when you generate (by relevance to this job).
          </Text>
          <Group gap="xs">
            {tailorPreview.selected_projects.map((p) => (
              <Badge key={p.name} variant="outline" size="sm" color="amber">
                {p.name}
              </Badge>
            ))}
          </Group>
        </Paper>
      )}

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Text size="sm" fw={600} mb="md" className="font-display">
          Tailored application
        </Text>
        <ApplicationFlow jobId={Number(jobId)} />
      </Paper>
    </Stack>
  );
}
