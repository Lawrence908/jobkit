import { Link } from "react-router-dom";
import { Card, Group, Badge, Text, Stack, Tooltip } from "@mantine/core";
import { IconArrowRight, IconFileText, IconFiles } from "@tabler/icons-react";
import type { Job } from "../api/types";

const STATUS_COLORS: Record<string, string> = {
  "Have Not Applied": "gray",
  "Submitted - Pending Response": "cyan",
  Rejected: "red",
  Interviewing: "yellow",
  "Offer Extended - In Progress": "green",
  "Sent Follow Up Email": "teal",
  "Re-Applied With Updated Resume": "violet",
  "N/A": "dark",
  // Legacy
  New: "gray",
  Tailored: "blue",
  Applied: "cyan",
  Offer: "green",
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString();
}

/** Show first N words of title; full title in tooltip if truncated. */
function titleDisplay(role: string, maxWords: number = 14): { display: string; full: string } {
  const full = (role || "Untitled role").trim();
  const words = full.split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return { display: full, full };
  const display = words.slice(0, maxWords).join(" ") + "…";
  return { display, full };
}

export function JobCard({ job }: { job: Job }) {
  const statusColor = STATUS_COLORS[job.status] || "gray";
  const { display: titleDisplayText, full: titleFull } = titleDisplay(job.role, 14);
  const hasContent = job.has_generated_content === true;
  const hasDocs = (job.artifact_count ?? 0) > 0;

  return (
    <Card
      shadow="sm"
      padding="lg"
      radius="lg"
      withBorder
      component={Link}
      to={`/dashboard/jobs/${job.id}`}
      className="job-card"
      style={{
        textDecoration: "none",
        color: "inherit",
        backgroundColor: "var(--bg-card)",
        border: "1px solid var(--border-muted)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      <Stack gap="sm">
        <Group justify="flex-end">
          <Badge color={statusColor} variant="light" size="sm">
            {job.status}
          </Badge>
        </Group>
        <div style={{ minWidth: 0 }}>
          <Tooltip label={titleFull} openDelay={400}>
            <Text fw={600} lineClamp={3} size="md" className="font-display" style={{ lineHeight: 1.3 }}>
              {titleDisplayText}
            </Text>
          </Tooltip>
          <Text size="sm" c="dimmed" lineClamp={1} mt={4}>
            {job.company || "Unknown company"}
          </Text>
        </div>

        {job.description_preview && (
          <Text size="xs" c="dimmed" lineClamp={2} style={{ lineHeight: 1.4 }}>
            {job.description_preview}
          </Text>
        )}

        <Group gap="xs" style={{ marginTop: 2 }}>
          <Text size="xs" c="dimmed">
            {formatDate(job.created_at)}
          </Text>
          {job.location && (
            <Text size="xs" c="dimmed">
              · {job.location}
            </Text>
          )}
        </Group>

        <Group gap="sm" wrap="wrap">
          {hasContent && (
            <Tooltip label="Draft resume & docs ready (resume, cover, notes)">
              <Group gap={4} style={{ color: "var(--mantine-color-teal-6)" }}>
                <IconFileText size={14} />
                <Text size="xs" c="dimmed">
                  Content generated
                </Text>
              </Group>
            </Tooltip>
          )}
          {hasDocs && (
            <Tooltip label={`${job.artifact_count} document(s) saved`}>
              <Group gap={4} style={{ color: "var(--mantine-color-blue-6)" }}>
                <IconFiles size={14} />
                <Text size="xs" c="dimmed">
                  Documents saved
                </Text>
              </Group>
            </Tooltip>
          )}
        </Group>

        <Group justify="flex-end" mt="xs">
          <Text
            size="xs"
            c="dimmed"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              color: "var(--accent)",
            }}
          >
            View <IconArrowRight size={12} />
          </Text>
        </Group>
      </Stack>
    </Card>
  );
}
