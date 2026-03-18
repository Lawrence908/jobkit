import { useState, useEffect } from "react";
import { Button, Select, Stack, Alert, Group } from "@mantine/core";
import { api } from "../api/client";

interface ProfileDefaults {
  default_tone: string;
  default_focus: string;
  default_length: string;
}

interface GeneratePanelProps {
  jobId: number;
}

const TONE_OPTIONS = ["neutral", "confident", "direct"];
const FOCUS_OPTIONS = ["backend", "full-stack", "ML", "cloud"];
const LENGTH_OPTIONS = ["1 page", "2 pages"];

export function GeneratePanel({ jobId }: GeneratePanelProps) {
  const [tone, setTone] = useState("neutral");
  const [focus, setFocus] = useState("full-stack");
  const [length, setLength] = useState("1 page");
  useEffect(() => {
    api.get<ProfileDefaults>("/api/profile").then((p) => {
      if (p.default_tone && TONE_OPTIONS.includes(p.default_tone)) setTone(p.default_tone);
      if (p.default_focus && FOCUS_OPTIONS.includes(p.default_focus)) setFocus(p.default_focus);
      if (p.default_length && LENGTH_OPTIONS.includes(p.default_length)) setLength(p.default_length);
    }).catch(() => {});
  }, []);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleGenerate = async () => {
    setError("");
    setMessage("");
    setGenerating(true);
    try {
      await api.post(`/api/jobs/${jobId}/generate`, { tone, focus, length });
      setMessage("Generated resume, cover letter, and notes.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleUploadAndLog = async () => {
    setError("");
    setMessage("");
    setUploading(true);
    try {
      const res = await api.post<{ ok: boolean; resume_link?: string }>(`/api/jobs/${jobId}/upload-and-log`);
      setMessage(res.resume_link ? "Uploaded and logged to Sheets." : "Uploaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Connect Google first?");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Stack gap="md">
      {error && <Alert color="red" variant="light">{error}</Alert>}
      {message && <Alert color="green" variant="light">{message}</Alert>}
      <Group gap="sm" wrap="wrap">
        <Select
          label="Tone"
          data={TONE_OPTIONS}
          value={tone}
          onChange={(v) => setTone(v || "neutral")}
          size="xs"
          style={{ minWidth: 120 }}
        />
        <Select
          label="Focus"
          data={FOCUS_OPTIONS}
          value={focus}
          onChange={(v) => setFocus(v || "full-stack")}
          size="xs"
          style={{ minWidth: 120 }}
        />
        <Select
          label="Length"
          data={LENGTH_OPTIONS}
          value={length}
          onChange={(v) => setLength(v || "1 page")}
          size="xs"
          style={{ minWidth: 110 }}
        />
      </Group>
      <Group gap="sm" wrap="wrap">
        <Button size="sm" color="amber" onClick={handleGenerate} loading={generating}>
          Generate
        </Button>
        <Button size="sm" variant="light" color="amber" onClick={handleUploadAndLog} loading={uploading}>
          Upload to Drive + Log to Sheets
        </Button>
      </Group>
    </Stack>
  );
}
