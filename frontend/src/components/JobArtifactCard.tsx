import { useEffect, useRef, useState } from "react";
import { Box, Center, Group, Paper, Text, ThemeIcon, Anchor, Loader } from "@mantine/core";
import {
  IconBrandGoogleDrive,
  IconDownload,
  IconExternalLink,
  IconFileText,
  IconFileTypePdf,
  IconMarkdown,
} from "@tabler/icons-react";
import { api } from "../api/client";

export interface JobArtifactItem {
  id: number;
  type: string;
  path: string;
  drive_link: string | null;
  download_url: string | null;
}

function artifactKind(type: string): "pdf" | "markdown" | "other" {
  if (type.endsWith("_pdf")) return "pdf";
  if (type.endsWith("_md")) return "markdown";
  return "other";
}

function labelForType(type: string): string {
  const map: Record<string, string> = {
    resume_md: "Resume · Markdown",
    resume_pdf: "Resume · PDF",
    cover_letter_md: "Cover letter · Markdown",
    cover_letter_pdf: "Cover letter · PDF",
    notes_md: "Notes · Markdown",
    interview_prep_md: "Interview prep · Markdown",
    interview_prep_pdf: "Interview prep · PDF",
  };
  return map[type] ?? type.replace(/_/g, " ");
}

export function JobArtifactCard({ artifact, refreshKey }: { artifact: JobArtifactItem; refreshKey: number }) {
  const { id, type, download_url, drive_link } = artifact;
  const kind = artifactKind(type);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [mdText, setMdText] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(download_url && kind !== "other"));
  const [loadError, setLoadError] = useState(false);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!download_url || kind === "other") {
      setLoading(false);
      setMdText(null);
      setPdfUrl(null);
      setLoadError(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(false);
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    setPdfUrl(null);
    setMdText(null);

    if (kind === "pdf") {
      api
        .getBlob(download_url)
        .then((blob) => {
          if (cancelled) return;
          const u = URL.createObjectURL(blob);
          objectUrlRef.current = u;
          setPdfUrl(u);
        })
        .catch(() => {
          if (!cancelled) setLoadError(true);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    } else {
      api
        .getBlob(download_url)
        .then((blob) => blob.text())
        .then((text) => {
          if (!cancelled) setMdText(text);
        })
        .catch(() => {
          if (!cancelled) setLoadError(true);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }

    return () => {
      cancelled = true;
    };
  }, [download_url, kind, refreshKey, id]);

  useEffect(
    () => () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    },
    [],
  );

  const downloadFilename = type.replace(/_pdf$/, ".pdf").replace(/_md$/, ".md");
  const label = labelForType(type);
  const previewHeight = kind === "markdown" ? 260 : kind === "pdf" ? 300 : 120;

  return (
    <Paper
      className="app-card job-artifact-card"
      p="md"
      withBorder
      radius="lg"
      style={{
        borderColor: "var(--border-muted)",
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm" mb="sm">
        <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
          <ThemeIcon
            variant="light"
            size="lg"
            radius="md"
            color={kind === "pdf" ? "red" : kind === "markdown" ? "cyan" : "gray"}
          >
            {kind === "pdf" ? (
              <IconFileTypePdf size={22} stroke={1.5} />
            ) : kind === "markdown" ? (
              <IconMarkdown size={22} stroke={1.5} />
            ) : (
              <IconFileText size={22} stroke={1.5} />
            )}
          </ThemeIcon>
          <Box style={{ minWidth: 0 }}>
            <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }}>
              Artifact
            </Text>
            <Text fw={600} className="font-display" size="sm" mt={2} lineClamp={2} style={{ wordBreak: "break-word" }}>
              {label}
            </Text>
          </Box>
        </Group>
      </Group>

      {download_url && (
        <Box
          style={{
            width: "100%",
            height: previewHeight,
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            background: "#525252",
            border: "1px solid var(--border-muted)",
            position: "relative",
            flexShrink: 0,
          }}
        >
          {loading && (
            <Center h="100%">
              <Loader color="amber" />
            </Center>
          )}
          {!loading && loadError && (
            <Center h="100%" p="sm">
              <Text size="xs" c="dimmed" ta="center">
                Couldn&apos;t load preview. Use Download or open in a new tab.
              </Text>
            </Center>
          )}
          {!loading && !loadError && kind === "pdf" && pdfUrl && (
            <iframe
              title={`${label} preview`}
              src={`${pdfUrl}#view=FitH`}
              style={{
                width: "100%",
                height: "100%",
                border: "none",
                display: "block",
                background: "#fff",
              }}
            />
          )}
          {!loading && !loadError && kind === "markdown" && mdText !== null && (
            <Box
              component="pre"
              className="job-artifact-md-preview"
              style={{
                margin: 0,
                height: "100%",
                overflow: "auto",
                padding: "0.75rem",
                fontSize: "0.7rem",
                lineHeight: 1.45,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                color: "var(--mantine-color-gray-2)",
                background: "#1f1f1f",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {mdText.length > 12000 ? `${mdText.slice(0, 12000)}…` : mdText}
            </Box>
          )}
          {!loading && !loadError && kind === "other" && (
            <Center h="100%">
              <Text size="xs" c="dimmed" ta="center" px="sm">
                No inline preview for this file type.
              </Text>
            </Center>
          )}
        </Box>
      )}

      {!download_url && drive_link && (
        <Text size="xs" c="dimmed" mb="xs">
          Available on Drive — use the link below.
        </Text>
      )}

      <Group gap="xs" mt="md" wrap="wrap" style={{ marginTop: "auto", paddingTop: "var(--mantine-spacing-xs)" }}>
        {download_url && (
          <>
            <Anchor
              size="xs"
              href={download_url}
              target="_blank"
              rel="noreferrer"
              c="amber"
              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
            >
              <IconExternalLink size={14} />
              {kind === "pdf" ? "Open in tab" : "View raw"}
            </Anchor>
            <Anchor
              size="xs"
              href={download_url}
              download={downloadFilename}
              target="_blank"
              rel="noreferrer"
              c="amber"
              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
            >
              <IconDownload size={14} />
              Download
            </Anchor>
          </>
        )}
        {drive_link && (
          <Anchor
            size="xs"
            href={drive_link}
            target="_blank"
            rel="noreferrer"
            c="amber"
            style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
          >
            <IconBrandGoogleDrive size={14} />
            Google Drive
          </Anchor>
        )}
      </Group>
    </Paper>
  );
}

/** Stable order: MD before its PDF sibling where applicable, then notes, then interview prep. */
const ARTIFACT_ORDER: string[] = [
  "resume_md",
  "resume_pdf",
  "cover_letter_md",
  "cover_letter_pdf",
  "notes_md",
  "interview_prep_md",
  "interview_prep_pdf",
];

export function sortJobArtifacts(list: JobArtifactItem[]): JobArtifactItem[] {
  return [...list].sort((a, b) => {
    const ia = ARTIFACT_ORDER.indexOf(a.type);
    const ib = ARTIFACT_ORDER.indexOf(b.type);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}
