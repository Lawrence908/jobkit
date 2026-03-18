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
  SegmentedControl,
  Title,
  Divider,
  Box,
  Anchor,
} from "@mantine/core";
import { IconExternalLink } from "@tabler/icons-react";
import { api } from "../api/client";
import type { Job } from "../api/types";
import { ApplicationFlow } from "../components/ApplicationFlow";
import { InterviewPrepPanel } from "../components/InterviewPrepPanel";
import {
  APPLICATION_STATUS_OPTIONS,
  REJECTION_REASON_OPTIONS,
  SOURCE_PLATFORM_OPTIONS,
  WORK_ARRANGEMENT_OPTIONS,
} from "../config/job-options";

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
  const [descriptionMessage, setDescriptionMessage] = useState("");
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [detailMode, setDetailMode] = useState<"application" | "interview_prep">("application");
  const [sourcePlatform, setSourcePlatform] = useState<string | null>(null);
  const [workArrangement, setWorkArrangement] = useState<string | null>(null);

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
        setSourcePlatform(j.source_platform ?? null);
        setWorkArrangement(j.work_arrangement ?? null);
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
    source_platform?: string | null;
    work_arrangement?: string | null;
    raw_body?: string;
  }) => {
    if (!jobId) return;
    setSaving(true);
    setSaveMessage("");
    setDescriptionMessage("");
    const descriptionOnly =
      overrides &&
      overrides.raw_body !== undefined &&
      Object.keys(overrides).length === 1;
    try {
      const body: Record<string, string | undefined | null> = {};
      if (overrides) {
        if (overrides.status !== undefined) body.status = overrides.status;
        if (overrides.rejection_reason !== undefined) body.rejection_reason = overrides.rejection_reason;
        if (overrides.company !== undefined) body.company = overrides.company;
        if (overrides.role !== undefined) body.role = overrides.role;
        if (overrides.location !== undefined) body.location = overrides.location;
        if (overrides.source_platform !== undefined) body.source_platform = overrides.source_platform;
        if (overrides.work_arrangement !== undefined) body.work_arrangement = overrides.work_arrangement;
        if (overrides.raw_body !== undefined) body.raw_body = overrides.raw_body;
      } else {
        body.status = status ?? undefined;
        body.rejection_reason = rejectionReason ?? undefined;
        body.company = company;
        body.role = role;
        body.location = location;
        body.source_platform = sourcePlatform ?? undefined;
        body.work_arrangement = workArrangement ?? undefined;
        body.raw_body = rawBody;
      }
      const updated = await api.patch<Job>(`/api/jobs/${jobId}`, body);
      setJob(updated);
      if (updated.status != null) setStatus(updated.status);
      if (updated.rejection_reason !== undefined) setRejectionReason(updated.rejection_reason ?? null);
      if (updated.company != null) setCompany(updated.company);
      if (updated.role != null) setRole(updated.role);
      if (updated.location != null) setLocation(updated.location);
      if (updated.source_platform !== undefined) setSourcePlatform(updated.source_platform ?? null);
      if (updated.work_arrangement !== undefined) setWorkArrangement(updated.work_arrangement ?? null);
      if (updated.raw_body !== undefined) setRawBody(updated.raw_body ?? "");
      const savedDescription = Object.prototype.hasOwnProperty.call(body, "raw_body");
      if (savedDescription) {
        api.get<TailorPreview>(`/api/jobs/${jobId}/tailor-preview`).then(setTailorPreview).catch(() => setTailorPreview(null));
      }
      if (descriptionOnly) {
        setDescriptionMessage("Description and keywords saved.");
        setTimeout(() => setDescriptionMessage(""), 4000);
      } else {
        setSaveMessage("Saved. Tracker updated.");
        setTimeout(() => setSaveMessage(""), 4000);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Save failed";
      if (descriptionOnly) {
        setDescriptionMessage(msg);
        setTimeout(() => setDescriptionMessage(""), 5000);
      } else {
        setSaveMessage(msg);
        setTimeout(() => setSaveMessage(""), 5000);
      }
    } finally {
      setSaving(false);
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
    <Stack gap="xl" className="job-detail-page" style={{ width: "100%", minWidth: 0 }}>
      <Paper className="app-card job-detail-primary" p="lg" withBorder radius="lg" style={{ overflow: "hidden" }}>
        <Stack gap="lg" style={{ minWidth: 0 }}>
          <Box className="job-detail-hero">
            <Group justify="space-between" align="flex-start" wrap="nowrap" gap="md" style={{ minWidth: 0 }}>
              <Box style={{ minWidth: 0, flex: 1 }}>
                <Text size="xs" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb={6}>
                  Job
                </Text>
                <Title order={2} className="font-display" style={{ fontWeight: 700, lineHeight: 1.2, wordBreak: "break-word" }}>
                  {role || job.role || "Untitled role"}
                </Title>
                <Group gap="xs" mt="md" wrap="wrap">
                  <Badge size="lg" variant="light" color="gray" radius="md">
                    {company || job.company || "Company"}
                  </Badge>
                  {(location || job.location) && (
                    <Badge size="lg" variant="dot" color="amber" radius="md">
                      {location || job.location}
                    </Badge>
                  )}
                </Group>
              </Box>
              <Button
                onClick={() => saveJob()}
                loading={saving}
                color="amber"
                size="sm"
                radius="md"
                style={{ flexShrink: 0 }}
              >
                Save job
              </Button>
            </Group>
            {saveMessage && (
              <Text size="sm" c="dimmed" mt="sm">
                {saveMessage}
              </Text>
            )}
          </Box>

          <Divider label="Application" labelPosition="left" />
          <Group align="flex-end" gap="md" wrap="wrap" style={{ minWidth: 0 }}>
            <Select
              label="Application Status"
              data={[...APPLICATION_STATUS_OPTIONS]}
              value={status}
              onChange={handleStatusChange}
              disabled={saving}
              style={{ minWidth: 200, maxWidth: "100%" }}
            />
            <Select
              label="Rejection Reason"
              data={[...REJECTION_REASON_OPTIONS]}
              value={rejectionReason}
              onChange={handleRejectionReasonChange}
              disabled={saving}
              placeholder="Set when rejected or for outcome"
              clearable
              style={{ minWidth: 240, maxWidth: "100%", flex: "1 1 280px" }}
            />
          </Group>

          <Divider label="Role details" labelPosition="left" />
          <Stack gap="sm" style={{ minWidth: 0 }}>
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
          </Stack>

          <Group grow align="flex-start" gap="md" wrap="wrap" style={{ minWidth: 0 }}>
            <Select
              label="Source platform"
              data={SOURCE_PLATFORM_OPTIONS.filter(Boolean).map((s) => ({ value: s, label: s }))}
              value={sourcePlatform ?? ""}
              onChange={(v) => setSourcePlatform(v || null)}
              disabled={saving}
              clearable
              placeholder="Not set"
              style={{ minWidth: 0, flex: "1 1 200px" }}
            />
            <Select
              label="Work arrangement"
              data={WORK_ARRANGEMENT_OPTIONS.filter(Boolean).map((s) => ({ value: s, label: s }))}
              value={workArrangement ?? ""}
              onChange={(v) => setWorkArrangement(v || null)}
              disabled={saving}
              clearable
              placeholder="Not set"
              style={{ minWidth: 0, flex: "1 1 200px" }}
            />
          </Group>

          {job.url && (
            <>
              <Divider label="Posting link" labelPosition="left" />
              <Box className="job-detail-url-wrap">
                <Group justify="space-between" align="center" gap="sm" wrap="wrap" mb="xs">
                  <Text size="xs" fw={600} c="dimmed" tt="uppercase" style={{ letterSpacing: "0.05em" }}>
                    URL
                  </Text>
                  <Button
                    component="a"
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    variant="light"
                    color="amber"
                    size="xs"
                    radius="md"
                    leftSection={<IconExternalLink size={14} />}
                  >
                    Open in new tab
                  </Button>
                </Group>
                <Anchor href={job.url} target="_blank" rel="noreferrer" className="job-detail-url-link">
                  {job.url}
                </Anchor>
              </Box>
            </>
          )}

          <div className="job-detail-meta-row">
            <Text span>
              <strong style={{ color: "var(--text-primary)" }}>Source</strong> · {job.source || "—"}
            </Text>
            {job.description_word_count !== undefined && (
              <Text span>
                <strong style={{ color: "var(--text-primary)" }}>Description</strong> · {job.description_word_count} words
                {job.description_word_count < 80 && job.source === "url" && (
                  <Text component="span" size="xs" c="dimmed" ml={6}>
                    (may be incomplete)
                  </Text>
                )}
              </Text>
            )}
          </div>
          {job.description_word_count !== undefined && job.description_word_count < 80 && job.source === "url" && (
            <Text size="xs" c="dimmed" style={{ maxWidth: "42rem" }}>
              If keywords look limited to the title, the page may not have been fully parsed. Add the job again via New
              Job using pasted description for better keywords.
            </Text>
          )}

          <Divider label="Job description" labelPosition="left" />
          <Textarea
            label="Full description"
            description="Paste or edit the full description. Save below or use Save job at the top — both persist text and refresh keywords."
            placeholder="Paste the full job description from the posting..."
            value={rawBody}
            onChange={(e) => setRawBody(e.currentTarget.value)}
            minRows={8}
            autosize
            maxRows={22}
            radius="md"
            styles={{ input: { fontSize: "0.9rem", lineHeight: 1.55 } }}
          />
          <Group gap="sm" align="center" wrap="wrap">
            <Button
              variant="light"
              color="amber"
              size="sm"
              radius="md"
              onClick={() => saveJob({ raw_body: rawBody })}
              loading={saving}
            >
              Save description
            </Button>
            {descriptionMessage && (
              <Text size="sm" c="dimmed">
                {descriptionMessage}
              </Text>
            )}
            <Button
              variant="subtle"
              color="red"
              size="sm"
              radius="md"
              onClick={() => setDeleteModalOpen(true)}
              style={{ marginLeft: "auto" }}
            >
              Delete job
            </Button>
          </Group>
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
        <Paper className="app-card" p="lg" withBorder radius="lg" style={{ borderColor: "var(--border-muted)" }}>
          <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="sm">
            Keywords
          </Text>
          <Group gap="xs">
            {job.keywords.map((k) => (
              <Badge key={k} variant="light" size="md" color="amber" radius="md">
                {k}
              </Badge>
            ))}
          </Group>
        </Paper>
      )}

      {tailorPreview && tailorPreview.selected_projects.length > 0 && (
        <Paper className="app-card" p="lg" withBorder radius="lg" style={{ borderColor: "var(--border-muted)" }}>
          <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb={4}>
            Projects we&apos;ll emphasize
          </Text>
          <Text size="sm" fw={600} className="font-display" mb="sm">
            Matched to this role
          </Text>
          <Text size="xs" c="dimmed" mb="md">
            Included when you generate (by relevance to this job).
          </Text>
          <Group gap="xs">
            {tailorPreview.selected_projects.map((p) => (
              <Badge key={p.name} variant="outline" size="md" color="amber" radius="md">
                {p.name}
              </Badge>
            ))}
          </Group>
        </Paper>
      )}

      <Paper className="app-card" p="lg" withBorder radius="lg">
        <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="md">
          Next steps
        </Text>
        <SegmentedControl
          value={detailMode}
          onChange={(v) => setDetailMode(v as "application" | "interview_prep")}
          data={[
            { label: "Application", value: "application" },
            { label: "Interview prep", value: "interview_prep" },
          ]}
          mb="md"
          radius="md"
          fullWidth
        />
        {detailMode === "application" ? (
          <ApplicationFlow jobId={Number(jobId)} />
        ) : (
          <>
            {job.status === "Interviewing" && (
              <Alert color="amber" mb="md" title="Interviewing for this role">
                Generate interview prep to get likely questions, talking points, STAR answers, and more tailored to this
                job.
              </Alert>
            )}
            <InterviewPrepPanel jobId={Number(jobId)} />
          </>
        )}
      </Paper>
    </Stack>
  );
}
