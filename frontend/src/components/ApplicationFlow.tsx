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
  Anchor,
  Box,
  Divider,
} from "@mantine/core";
import { IconFileText, IconUpload, IconCheck, IconExternalLink, IconDownload, IconBrandGoogleDrive } from "@tabler/icons-react";
import { api } from "../api/client";
import { LLM_MODEL_OPTIONS } from "../config/llm-models";

interface ProfileDefaults {
  default_tone: string;
  default_focus: string;
  default_length: string;
}

interface GeneratedContent {
  resume: string | null;
  cover_letter: string | null;
  notes: string | null;
}

interface ArtifactItem {
  id: number;
  type: string;
  path: string;
  drive_link: string | null;
  download_url: string | null;
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
  const [rendering, setRendering] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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
    api.get<ArtifactItem[]>(`/api/jobs/${jobId}/artifacts`).then(setArtifacts).catch(() => setArtifacts([]));
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
    }).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    setError("");
    setMessage("");
    setGenerating(true);
    try {
      await api.post(`/api/jobs/${jobId}/generate`, { tone, focus, length, model: model || undefined });
      setMessage("Generated. Review and edit below, then approve to create PDFs.");
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

  const handleRender = async () => {
    setError("");
    setMessage("");
    setRendering(true);
    try {
      await api.post(`/api/jobs/${jobId}/render`);
      setMessage("PDFs are being created. Check artifacts below in a few seconds.");
      setTimeout(fetchArtifacts, 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Render failed");
    } finally {
      setRendering(false);
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

      {/* Step 1: Generate */}
      <Box>
        <Text size="sm" fw={600} mb="xs" className="font-display">1. Generate tailored draft</Text>
        <Group gap="sm" wrap="wrap" align="flex-end">
          <Select label="Tone" data={TONE_OPTIONS} value={tone} onChange={(v) => setTone(v || "neutral")} size="xs" style={{ minWidth: 110 }} />
          <Select label="Focus" data={FOCUS_OPTIONS} value={focus} onChange={(v) => setFocus(v || "full-stack")} size="xs" style={{ minWidth: 110 }} />
          <Select label="Length" data={LENGTH_OPTIONS} value={length} onChange={(v) => setLength(v || "1 page")} size="xs" style={{ minWidth: 100 }} />
          <Select label="Model" data={LLM_MODEL_OPTIONS} value={model} onChange={(v) => setModel(v ?? "")} size="xs" style={{ minWidth: 140 }} />
          <Button size="sm" color="amber" onClick={handleGenerate} loading={generating}>Generate</Button>
        </Group>
      </Box>

      {/* Step 2: Preview & edit */}
      {hasGenerated && (
        <>
          <Divider />
          <Box>
            <Text size="sm" fw={600} mb="xs" className="font-display">2. Preview & edit</Text>
            <Text size="xs" c="dimmed" mb="sm">Edit the markdown below, then save. When ready, approve to create PDFs.</Text>
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

      {/* Step 3 & 4: Approve PDF, Upload */}
      {hasGenerated && (
        <>
          <Divider />
          <Box>
            <Text size="sm" fw={600} mb="xs" className="font-display">3. Approve & create PDF</Text>
            <Text size="xs" c="dimmed" mb="sm">Create PDFs from the current resume and cover letter (including your edits).</Text>
            <Button size="sm" leftSection={<IconCheck size={16} />} color="amber" onClick={handleRender} loading={rendering}>Approve & create PDF</Button>
          </Box>
          <Box>
            <Text size="sm" fw={600} mb="xs" className="font-display">4. Upload to Drive + log</Text>
            <Text size="xs" c="dimmed" mb="sm">Upload PDFs and update your tracker sheet.</Text>
            <Button size="sm" leftSection={<IconUpload size={16} />} variant="light" color="amber" onClick={handleUpload} loading={uploading}>Upload to Drive + Log to Sheets</Button>
          </Box>
        </>
      )}

      {/* Artifacts */}
      {artifacts.length > 0 && (
        <>
          <Divider />
          <Box>
            <Text size="sm" fw={600} mb="xs" className="font-display">Artifacts</Text>
            <Text size="xs" c="dimmed" mb="xs">View or download generated documents; open in Drive if uploaded.</Text>
            <Group gap="xs">
              <Button size="xs" variant="subtle" onClick={fetchArtifacts}>Refresh</Button>
            </Group>
            <Stack gap="sm" mt="xs">
              {artifacts.map((a) => {
                const isPdf = a.type.endsWith("_pdf");
                const label = a.type.replace(/_/g, " ");
                const downloadFilename = a.type.replace(/_pdf$/, ".pdf").replace(/_md$/, ".md");
                return (
                  <Group key={a.id} gap="md" wrap="wrap" align="center">
                    <Text size="sm" fw={500} style={{ minWidth: "8rem" }}>
                      {label}
                    </Text>
                    <Group gap="xs">
                      {a.download_url && (
                        <>
                          <Anchor
                            size="xs"
                            href={a.download_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                          >
                            <IconExternalLink size={14} />
                            {isPdf ? "Preview in browser" : "View"}
                          </Anchor>
                          <Anchor
                            size="xs"
                            href={a.download_url}
                            download={downloadFilename}
                            target="_blank"
                            rel="noreferrer"
                            style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                          >
                            <IconDownload size={14} />
                            Download
                          </Anchor>
                        </>
                      )}
                      {a.drive_link && (
                        <Anchor
                          size="xs"
                          href={a.drive_link}
                          target="_blank"
                          rel="noreferrer"
                          style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                        >
                          <IconBrandGoogleDrive size={14} />
                          Open in Google Drive
                        </Anchor>
                      )}
                    </Group>
                  </Group>
                );
              })}
            </Stack>
          </Box>
        </>
      )}
    </Stack>
  );
}
