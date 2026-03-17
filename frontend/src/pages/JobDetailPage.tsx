import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Stack,
  Group,
  Badge,
  Select,
  Paper,
  Text,
  TextInput,
  Textarea,
  Button,
  Loader,
  Center,
  Alert,
  Modal,
} from "@mantine/core";
import { api } from "../api/client";
import type { Job } from "../api/types";
import { ApplicationFlow } from "../components/ApplicationFlow";
import { APPLICATION_STATUS_OPTIONS, REJECTION_REASON_OPTIONS } from "../config/job-options";

interface TailorPreview {
  keywords: string[];
  selected_projects: { name: string; description: string }[];
}

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState<string | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [tailorPreview, setTailorPreview] = useState<TailorPreview | null>(null);
  const [rawBody, setRawBody] = useState("");
  const [updatingDescription, setUpdatingDescription] = useState(false);
  const [descriptionMessage, setDescriptionMessage] = useState("");
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    api
      .get<Job>(`/api/jobs/${jobId}`)
      .then((j) => {
        setJob(j);
        setStatus(j.status);
        setRejectionReason(j.rejection_reason ?? null);
        setCompany(j.company ?? "");
        setRole(j.role ?? "");
        setLocation(j.location ?? "");
        setRawBody(j.raw_body ?? "");
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

  const handleRejectionReasonChange = async (value: string | null) => {
    if (!jobId) return;
    await saveJob({ rejection_reason: value ?? undefined });
    setRejectionReason(value);
  };

  const saveJob = async (overrides?: {
    status?: string;
    rejection_reason?: string;
    company?: string;
    role?: string;
    location?: string;
  }) => {
    if (!jobId) return;
    setSaving(true);
    setSaveMessage("");
    try {
      const body: {
        status?: string;
        rejection_reason?: string;
        company?: string;
        role?: string;
        location?: string;
      } = {};
      if (overrides) {
        if (overrides.status !== undefined) body.status = overrides.status;
        if (overrides.rejection_reason !== undefined) body.rejection_reason = overrides.rejection_reason;
        if (overrides.company !== undefined) body.company = overrides.company;
        if (overrides.role !== undefined) body.role = overrides.role;
        if (overrides.location !== undefined) body.location = overrides.location;
      } else {
        body.status = status ?? undefined;
        body.rejection_reason = rejectionReason ?? undefined;
        body.company = company;
        body.role = role;
        body.location = location;
      }
      const updated = await api.patch<Job>(`/api/jobs/${jobId}`, body);
      setJob(updated);
      if (updated.status != null) setStatus(updated.status);
      if (updated.rejection_reason !== undefined) setRejectionReason(updated.rejection_reason ?? null);
      if (updated.company != null) setCompany(updated.company);
      if (updated.role != null) setRole(updated.role);
      if (updated.location != null) setLocation(updated.location);
      setSaveMessage("Saved. Tracker updated.");
      setTimeout(() => setSaveMessage(""), 4000);
    } finally {
      setSaving(false);
    }
  };

  const updateDescription = async () => {
    if (!jobId) return;
    setUpdatingDescription(true);
    setDescriptionMessage("");
    try {
      const updated = await api.post<Job>(`/api/jobs/${jobId}/update-description`, { raw_body: rawBody });
      setJob(updated);
      setRawBody(updated.raw_body ?? rawBody);
      setDescriptionMessage("Description and keywords updated.");
      setTimeout(() => setDescriptionMessage(""), 4000);
      api.get<TailorPreview>(`/api/jobs/${jobId}/tailor-preview`).then(setTailorPreview).catch(() => setTailorPreview(null));
    } catch (err) {
      setDescriptionMessage(err instanceof Error ? err.message : "Update failed");
      setTimeout(() => setDescriptionMessage(""), 5000);
    } finally {
      setUpdatingDescription(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!jobId) return;
    setDeleting(true);
    try {
      await api.delete(`/api/jobs/${jobId}`);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setDescriptionMessage(err instanceof Error ? err.message : "Delete failed");
      setTimeout(() => setDescriptionMessage(""), 5000);
      setDeleteModalOpen(false);
    } finally {
      setDeleting(false);
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
          <Text size="sm" fw={600} className="font-display" style={{ flexShrink: 0 }}>
            Job details
          </Text>
          <Group align="flex-end" gap="sm" wrap="wrap">
            <Select
              label="Application Status"
              data={[...APPLICATION_STATUS_OPTIONS]}
              value={status}
              onChange={handleStatusChange}
              disabled={saving}
              style={{ minWidth: 220 }}
            />
            <Select
              label="Rejection Reason"
              data={[...REJECTION_REASON_OPTIONS]}
              value={rejectionReason}
              onChange={handleRejectionReasonChange}
              disabled={saving}
              placeholder="Set when rejected or for outcome"
              clearable
              style={{ minWidth: 280 }}
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
          {job.description_word_count !== undefined && (
            <>
              <Text size="sm">
                <strong>Description parsed:</strong> {job.description_word_count} words
                {job.description_word_count < 80 && job.source === "url" && (
                  <Text component="span" size="xs" c="dimmed" ml="xs">
                    (may be incomplete)
                  </Text>
                )}
              </Text>
              {job.description_word_count < 80 && job.source === "url" && (
                <Text size="xs" c="dimmed">
                  If keywords look limited to the title, the page may not have been fully parsed. Add the job again via
                  New Job using pasted description for better keywords.
                </Text>
              )}
            </>
          )}
          <Textarea
            label="Job description"
            description="Paste or edit the full description; click Update to refresh keywords."
            placeholder="Paste the full job description from the posting..."
            value={rawBody}
            onChange={(e) => setRawBody(e.currentTarget.value)}
            minRows={6}
            autosize
            maxRows={20}
          />
          <Group gap="sm">
            <Button
              variant="light"
              color="amber"
              size="sm"
              onClick={updateDescription}
              loading={updatingDescription}
            >
              Update description
            </Button>
            {descriptionMessage && (
              <Text size="sm" c="dimmed">
                {descriptionMessage}
              </Text>
            )}
          </Group>
          <Button
            variant="subtle"
            color="red"
            size="sm"
            onClick={() => setDeleteModalOpen(true)}
            style={{ alignSelf: "flex-start" }}
          >
            Delete job
          </Button>
        </Stack>
      </Paper>

      <Modal
        opened={deleteModalOpen}
        onClose={() => !deleting && setDeleteModalOpen(false)}
        title="Delete this job?"
      >
        <Text size="sm" c="dimmed" mb="md">
          This will remove the job, its description, generated drafts, PDFs, and any artifact records. This cannot be
          undone.
        </Text>
        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={() => setDeleteModalOpen(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button color="red" onClick={handleDeleteJob} loading={deleting}>
            Delete
          </Button>
        </Group>
      </Modal>

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
