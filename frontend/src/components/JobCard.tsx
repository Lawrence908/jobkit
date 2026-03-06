import { Link } from "react-router-dom";
import { Card, Group, Badge, Text, Stack } from "@mantine/core";
import { IconArrowRight } from "@tabler/icons-react";
import type { Job } from "../api/types";

const STATUS_COLORS: Record<string, string> = {
  New: "gray",
  Tailored: "blue",
  Applied: "cyan",
  Interviewing: "yellow",
  Rejected: "red",
  Offer: "green",
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString();
}

export function JobCard({ job }: { job: Job }) {
  const statusColor = STATUS_COLORS[job.status] || "gray";
  return (
    <Card
      shadow="sm"
      padding="lg"
      radius="lg"
      withBorder
      component={Link}
      to={`/jobs/${job.id}`}
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
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <div style={{ minWidth: 0, flex: 1 }}>
            <Text fw={600} lineClamp={1} size="md" className="font-display">
              {job.role || "Untitled role"}
            </Text>
            <Text size="sm" c="dimmed" lineClamp={1} mt={4}>
              {job.company || "Unknown company"}
            </Text>
          </div>
          <Badge color={statusColor} variant="light" size="sm">
            {job.status}
          </Badge>
        </Group>
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
