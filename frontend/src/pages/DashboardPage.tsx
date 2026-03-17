import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button, Title, Stack, Grid, TextInput, Select, Loader, Center, Text, Group, Paper } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { api } from "../api/client";
import type { Job } from "../api/types";
import { JobCard } from "../components/JobCard";
import { APPLICATION_STATUS_OPTIONS } from "../config/job-options";

export function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get<Job[]>("/api/jobs").then(setJobs).catch(() => setJobs([])).finally(() => setLoading(false));
  }, []);

  const filtered = jobs.filter((j) => {
    if (statusFilter && j.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!j.company?.toLowerCase().includes(q) && !j.role?.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  if (loading) {
    return (
      <div className="page-container" style={{ display: "flex", justifyContent: "center", paddingTop: "3rem" }}>
        <Loader color="amber" />
      </div>
    );
  }

  return (
    <Stack gap="xl" style={{ width: "100%" }}>
      <Group justify="space-between" wrap="wrap" align="flex-end" gap="md">
        <Title order={3} className="font-display" style={{ fontWeight: 700, margin: 0 }}>
          Jobs
        </Title>
        <Button
          component={Link}
          to="/dashboard/jobs/new"
          variant="filled"
          leftSection={<IconPlus size={18} />}
          color="amber"
          size="sm"
        >
          New Job
        </Button>
      </Group>

      <Paper className="app-card" p="md" withBorder radius="lg">
        <Group gap="sm" wrap="wrap" align="flex-end">
          <TextInput
            placeholder="Search company or role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            size="sm"
            style={{ minWidth: 240, flex: "1 1 200px" }}
          />
          <Select
            placeholder="Application Status"
            clearable
            data={[...APPLICATION_STATUS_OPTIONS]}
            value={statusFilter}
            onChange={setStatusFilter}
            size="sm"
            style={{ minWidth: 200 }}
          />
        </Group>
      </Paper>

      {filtered.length === 0 ? (
        <Paper className="app-card" p="xl" withBorder radius="lg" style={{ borderStyle: "dashed" }}>
          <Center py="md">
            <Stack gap="xs" align="center">
              <Text c="dimmed" size="sm" ta="center">
                No jobs match your filters.
                {jobs.length === 0
                  ? " Add your first job with New Job."
                  : " Try changing the search or status filter."}
              </Text>
              {jobs.length === 0 && (
                <Button component={Link} to="/dashboard/jobs/new" variant="filled" color="amber" size="sm" leftSection={<IconPlus size={18} />}>
                  New Job
                </Button>
              )}
            </Stack>
          </Center>
        </Paper>
      ) : (
        <Grid gutter="lg">
          {filtered.map((job) => (
            <Grid.Col key={job.id} span={{ base: 12, sm: 6, md: 4 }}>
              <JobCard job={job} />
            </Grid.Col>
          ))}
        </Grid>
      )}
    </Stack>
  );
}
