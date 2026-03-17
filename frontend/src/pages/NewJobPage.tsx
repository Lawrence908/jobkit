import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Title, Stack, TextInput, Textarea, Paper, Alert, Select } from "@mantine/core";
import { api } from "../api/client";
import { APPLICATION_STATUS_OPTIONS, DEFAULT_APPLICATION_STATUS } from "../config/job-options";

export function NewJobPage() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");
  const [applicationStatus, setApplicationStatus] = useState<string | null>(DEFAULT_APPLICATION_STATUS);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const job = await api.post<{ id: number }>("/api/jobs", {
        url: url.trim() || undefined,
        raw_text: rawText.trim() || undefined,
        status: applicationStatus || DEFAULT_APPLICATION_STATUS,
      });
      navigate(`/dashboard/jobs/${(job as { id: number }).id}`, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="xl" className="new-job-page" style={{ width: "100%", maxWidth: "40rem" }}>
      <Title order={3} className="font-display" style={{ fontWeight: 700 }}>
        New Job
      </Title>
      <Paper className="app-card" p="lg" withBorder radius="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            {error && <Alert color="red" variant="light">{error}</Alert>}
            <Select
              label="Application Status"
              data={[...APPLICATION_STATUS_OPTIONS]}
              value={applicationStatus}
              onChange={setApplicationStatus}
              size="sm"
              allowDeselect={false}
            />
            <TextInput
              label="Job URL"
              placeholder="https://..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              description="Optional. If provided, we'll try to scrape the page."
              size="sm"
            />
            <Textarea
              label="Job description (paste)"
              placeholder="Paste the full job description here. Use this if the URL doesn't work or you only have the text."
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              minRows={8}
              size="sm"
            />
            <Button
              type="submit"
              loading={loading}
              disabled={!url.trim() && !rawText.trim()}
              color="amber"
              variant="filled"
            >
              Save job
            </Button>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
