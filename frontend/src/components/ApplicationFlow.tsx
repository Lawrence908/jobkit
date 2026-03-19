import { useState, useEffect, useCallback } from "react";
import {
  Stack,
  Text,
  Button,
  Select,
  Group,
  Alert,
  Tabs,
  Textarea,
  Loader,
  Box,
  Divider,
  SimpleGrid,
} from "@mantine/core";
import { IconFileText, IconUpload, IconRefresh } from "@tabler/icons-react";
import { api } from "../api/client";
import { JobArtifactCard, sortJobArtifacts, type JobArtifactItem } from "./JobArtifactCard";
import { LLM_MODEL_OPTIONS } from "../config/llm-models";

interface ProfileDefaults {
  default_tone: string;
  default_focus: string;
  default_length: string;
  llm_api_key?: string;
}

interface GeneratedContent {
  resume: string | null;
  cover_letter: string | null;
  notes: string | null;
}

const TONE_OPTIONS = ["neutral", "confident", "direct"];
const FOCUS_OPTIONS = ["backend", "full-stack", "ML", "cloud"];
const LENGTH_OPTIONS = ["1 page", "2 pages"];

export function ApplicationFlow({ jobId }: { jobId: number }) {
  const [tone, setTone] = useState("neutral");
  const [focus, setFocus] = useState("full-stack");
  const [length, setLength] = useState("1 page");
  const [model, setModel] = useState("");
  const [generating, setGenerating] = useState(false);
  const [content, setContent] = useState<GeneratedContent>({ resume: null, cover_letter: null, notes: null });
  const [loadingContent, setLoadingContent] = useState(true);
  const [savingDoc, setSavingDoc] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [artifacts, setArtifacts] = useState<JobArtifactItem[]>([]);
  const [artifactsPreviewKey, setArtifactsPreviewKey] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [hasLlmKey, setHasLlmKey] = useState<boolean | null>(null);

  const hasGenerated = content.resume != null;

  const fetchGenerated = useCallback(() => {
    setLoadingContent(true);
    api
      .get<GeneratedContent>(`/api/jobs/${jobId}/generated`)
      .then(setContent)
      .catch(() => setContent({ resume: null, cover_letter: null, notes: null }))
      .finally(() => setLoadingContent(false));
  }, [jobId]);

  const fetchArtifacts = useCallback(() => {
    api
      .get<JobArtifactItem[]>(`/api/jobs/${jobId}/artifacts`)
      .then((list) => {
        setArtifacts(list);
        setArtifactsPreviewKey((k) => k + 1);
      })
      .catch(() => setArtifacts([]));
  }, [jobId]);

  useEffect(() => {
    fetchGenerated();
  }, [fetchGenerated]);

  useEffect(() => {
    fetchArtifacts();
  }, [fetchArtifacts]);

  useEffect(() => {
    api.get<ProfileDefaults>("/api/profile").then((p) => {
      if (p.default_tone && TONE_OPTIONS.includes(p.default_tone)) setTone(p.default_tone);
      if (p.default_focus && FOCUS_OPTIONS.includes(p.default_focus)) setFocus(p.default_focus);
      if (p.default_length && LENGTH_OPTIONS.includes(p.default_length)) setLength(p.default_length);
      const key = (p as { llm_api_key?: string }).llm_api_key;
      setHasLlmKey(Boolean(key && String(key).trim()));
    }).catch(() => setHasLlmKey(false));
  }, []);

  const handleGenerate = async () => {
    setError("");
    setMessage("");
    setGenerating(true);
    try {
      await api.post(`/api/jobs/${jobId}/generate`, { tone, focus, length, model: model || undefined });
      setMessage(hasLlmKey ? "Generated. Review and edit below if you like, then use Upload to Drive + Log." : "Draft built. Review and edit below, then use Upload to Drive + Log.");
      fetchGenerated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveDoc = async (docKey: "resume" | "cover_letter" | "notes") => {
    const value = content[docKey];
    if (value == null) return;
    setError("");
    setSavingDoc(docKey);
    try {
      await api.put(`/api/jobs/${jobId}/generated/${docKey}`, { content: value });
      setMessage(`${docKey === "cover_letter" ? "Cover letter" : docKey === "notes" ? "Notes" : "Resume"} saved.`);
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSavingDoc(null);
    }
  };

  const handleUpload = async () => {
    setError("");
    setMessage("");
    setUploading(true);
    try {
      const res = await api.post<{ ok: boolean; resume_link?: string }>(`/api/jobs/${jobId}/upload-and-log`);
      setMessage(res.resume_link ? "Uploaded and logged to Sheets." : "Uploaded.");
      fetchArtifacts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Connect Google first?");
    } finally {
      setUploading(false);
    }
  };

  const updateContent = (docKey: keyof GeneratedContent, value: string) => {
    setContent((prev) => ({ ...prev, [docKey]: value }));
  };

  return (
    <Stack gap="lg">
      {error && <Alert color="red" variant="light" onClose={() => setError("")} withCloseButton>{error}</Alert>}
      {message && <Alert color="green" variant="light">{message}</Alert>}

      {/* Step 1: Build draft / Generate */}
      <Box>
        <Text size="sm" fw={600} mb="xs" className="font-display">1. {hasLlmKey ? "Generate tailored draft" : "Build draft"}</Text>
        {hasLlmKey === false && (
          <Alert color="gray" variant="light" mb="sm" title="No API key">
            Draft is built from your profile and job match (no AI). Add an API key in Profile to optionally refine wording.
          </Alert>
        )}
        <Group gap="sm" wrap="wrap" align="flex-end">
          <Select label="Tone" data={TONE_OPTIONS} value={tone} onChange={(v) => setTone(v || "neutral")} size="xs" style={{ minWidth: 110 }} />
          <Select label="Focus" data={FOCUS_OPTIONS} value={focus} onChange={(v) => setFocus(v || "full-stack")} size="xs" style={{ minWidth: 110 }} />
          <Select label="Length" data={LENGTH_OPTIONS} value={length} onChange={(v) => setLength(v || "1 page")} size="xs" style={{ minWidth: 100 }} />
          {hasLlmKey === true && (
            <Select label="Model" data={LLM_MODEL_OPTIONS} value={model} onChange={(v) => setModel(v ?? "")} size="xs" style={{ minWidth: 140 }} />
          )}
          <Button size="sm" color="amber" onClick={handleGenerate} loading={generating}>{hasLlmKey ? "Generate" : "Build draft"}</Button>
        </Group>
      </Box>

      {/* Step 2: Preview & edit */}
      {hasGenerated && (
        <>
          <Divider />
          <Box>
            <Text size="sm" fw={600} mb="xs" className="font-display">2. Preview & edit</Text>
            <Text size="xs" c="dimmed" mb="sm">Edit the markdown below and save if you make changes. Then use Upload to Drive + Log to create PDFs and update your tracker.</Text>
            {loadingContent ? (
              <Loader size="sm" color="amber" />
            ) : (
              <Tabs defaultValue="resume">
                <Tabs.List>
                  <Tabs.Tab value="resume" leftSection={<IconFileText size={14} />}>Resume</Tabs.Tab>
                  <Tabs.Tab value="cover_letter">Cover letter</Tabs.Tab>
                  <Tabs.Tab value="notes">Notes</Tabs.Tab>
                </Tabs.List>
                <Tabs.Panel value="resume" pt="sm">
                  <Textarea
                    minRows={18}
                    maxRows={32}
                    value={content.resume ?? ""}
                    onChange={(e) => updateContent("resume", e.target.value)}
                    styles={{ input: { fontSize: 13, fontFamily: "monospace", minHeight: 360 } }}
                  />
                  <Button size="xs" variant="light" color="amber" mt="xs" loading={savingDoc === "resume"} onClick={() => handleSaveDoc("resume")}>Save resume</Button>
                </Tabs.Panel>
                <Tabs.Panel value="cover_letter" pt="sm">
                  <Textarea
                    minRows={15}
                    maxRows={28}
                    value={content.cover_letter ?? ""}
                    onChange={(e) => updateContent("cover_letter", e.target.value)}
                    styles={{ input: { fontSize: 13, fontFamily: "monospace", minHeight: 320 } }}
                  />
                  <Button size="xs" variant="light" color="amber" mt="xs" loading={savingDoc === "cover_letter"} onClick={() => handleSaveDoc("cover_letter")}>Save cover letter</Button>
                </Tabs.Panel>
                <Tabs.Panel value="notes" pt="sm">
                  <Textarea
                    minRows={12}
                    maxRows={20}
                    value={content.notes ?? ""}
                    onChange={(e) => updateContent("notes", e.target.value)}
                    styles={{ input: { fontSize: 13, fontFamily: "monospace", minHeight: 280 } }}
                  />
                  <Button size="xs" variant="light" color="amber" mt="xs" loading={savingDoc === "notes"} onClick={() => handleSaveDoc("notes")}>Save notes</Button>
                </Tabs.Panel>
              </Tabs>
            )}
          </Box>
        </>
      )}

      {/* Step 3: Upload (creates PDFs and logs) */}
      {hasGenerated && (
        <>
          <Divider />
          <Box>
            <Text size="sm" fw={600} mb="xs" className="font-display">3. Upload to Drive + log</Text>
            <Text size="xs" c="dimmed" mb="sm">Creates PDFs from your resume and cover letter, uploads them to Drive, and updates your tracker sheet with PDF links.</Text>
            <Button size="sm" leftSection={<IconUpload size={16} />} color="amber" onClick={handleUpload} loading={uploading}>Upload to Drive + Log to Sheets</Button>
          </Box>
        </>
      )}

      {/* Artifacts — card grid with PDF previews (WeasyPrint) and markdown source previews */}
      {artifacts.length > 0 && (
        <>
          <Divider />
          <Box>
            <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm" mb="xs">
              <Box style={{ minWidth: 0 }}>
                <Text size="sm" fw={600} className="font-display">
                  Artifacts
                </Text>
                <Text size="xs" c="dimmed" mt={4}>
                  PDFs render like your Profile resume preview; markdown shows as source. Open in Drive when uploaded.
                </Text>
              </Box>
              <Button
                size="xs"
                variant="subtle"
                color="gray"
                leftSection={<IconRefresh size={14} />}
                onClick={fetchArtifacts}
              >
                Refresh
              </Button>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
              {sortJobArtifacts(artifacts).map((a) => (
                <JobArtifactCard key={a.id} artifact={a} refreshKey={artifactsPreviewKey} />
              ))}
            </SimpleGrid>
          </Box>
        </>
      )}
    </Stack>
  );
}
