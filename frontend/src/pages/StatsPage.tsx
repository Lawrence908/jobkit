import { useEffect, useMemo, useState } from "react";
import {
  Stack,
  Paper,
  Title,
  Text,
  SimpleGrid,
  Loader,
  Center,
  Alert,
  Group,
  Textarea,
  Button,
  CopyButton,
  Tooltip,
  Grid,
  Box,
  ThemeIcon,
} from "@mantine/core";
import { useClipboard, useMediaQuery } from "@mantine/hooks";
import {
  IconExternalLink,
  IconBriefcase,
  IconSend,
  IconMessages,
  IconTrophy,
  IconGitBranch,
  IconChartBar,
} from "@tabler/icons-react";
import { BarChart, AreaChart, DonutChart } from "@mantine/charts";
import { api } from "../api/client";
import sankeyPreviewSrc from "../assets/landing/sankey-preview.png";

interface Summary {
  total_saved: number;
  total_applied: number;
  total_interviewing: number;
  total_rejected: number;
  total_offers: number;
  total_withdrawn: number;
  active_pipeline: number;
}

interface FunnelResponse {
  by_status: Record<string, number>;
}

interface TimelineResponse {
  period: string;
  labels: string[];
  counts: number[];
}

interface SourcesResponse {
  by_source: Record<string, number>;
}

interface InsightsResponse {
  insights: string[];
}

interface SankeyResponse {
  flow_text: string;
  sankeymatic_build_url: string;
}

const CHART_COLORS = ["amber.6", "cyan.6", "yellow.6", "red.6", "green.6", "violet.6", "teal.6"];

const KPI_CONFIG: Array<{
  key: keyof Summary;
  label: string;
  icon: typeof IconBriefcase;
  accent?: boolean;
}> = [
  { key: "total_saved", label: "Saved", icon: IconBriefcase },
  { key: "total_applied", label: "Applied", icon: IconSend },
  { key: "total_interviewing", label: "Interviewing", icon: IconMessages },
  { key: "total_offers", label: "Offers", icon: IconTrophy },
  { key: "active_pipeline", label: "Active pipeline", icon: IconGitBranch, accent: true },
];

function SankeyPreviewVisual() {
  return (
    <Box className="stats-sankey-visual">
      <img
        src={sankeyPreviewSrc}
        alt="Example application funnel (Sankey diagram)"
        width={340}
        height={220}
        decoding="async"
      />
      <Text size="sm" c="dimmed" ta="center" maw={340} mx="auto" style={{ position: "relative", zIndex: 1 }} lh={1.55}>
        Copy your pipeline flow data from the text area and paste it into{" "}
        <Text component="span" fw={600} c="var(--text-secondary)">
          SankeyMATIC
        </Text>{" "}
        to build a diagram you can tweak and share.
      </Text>
    </Box>
  );
}

export function StatsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [funnel, setFunnel] = useState<FunnelResponse | null>(null);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [insights, setInsights] = useState<string[]>([]);
  const [sankey, setSankey] = useState<SankeyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const clipboard = useClipboard({ timeout: 2000 });
  const funnelCompact = useMediaQuery("(max-width: 48em)");

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      api.get<Summary>("/api/stats/summary"),
      api.get<FunnelResponse>("/api/stats/funnel"),
      api.get<TimelineResponse>("/api/stats/timeline?period=day"),
      api.get<SourcesResponse>("/api/stats/sources"),
      api.get<InsightsResponse>("/api/stats/insights"),
      api.get<SankeyResponse>("/api/stats/sankey"),
    ])
      .then(([s, f, t, src, i, sk]) => {
        setSummary(s);
        setFunnel(f);
        setTimeline(t);
        setSources(src);
        setInsights(i.insights || []);
        setSankey(sk);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  const funnelMaxLabel = funnelCompact ? 26 : 42;
  const funnelData = useMemo(() => {
    if (!funnel?.by_status) return null;
    return Object.entries(funnel.by_status).map(([status, count]) => ({
      status: status.length > funnelMaxLabel ? status.slice(0, funnelMaxLabel - 1) + "…" : status,
      count,
    }));
  }, [funnel, funnelMaxLabel]);

  if (loading) {
    return (
      <Center py="xl">
        <Loader color="amber" />
      </Center>
    );
  }

  if (error) {
    return (
      <div className="page-container--narrow" style={{ paddingTop: "1rem" }}>
        <Alert color="red">{error}</Alert>
      </div>
    );
  }

  const timelineData =
    timeline?.labels?.map((label, i) => ({
      period: label,
      jobs: timeline.counts[i] ?? 0,
    })) ?? [];

  const donutData =
    sources?.by_source &&
    Object.entries(sources.by_source)
      .filter(([, v]) => v > 0)
      .map(([name, value], i) => ({
        name: name === "Not set" ? "Not set" : name,
        value,
        color: CHART_COLORS[i % CHART_COLORS.length],
      }));

  return (
    <Stack gap="xl" className="stats-page">
      <Box className="stats-hero">
        <Group gap="sm" mb="xs" wrap="nowrap">
          <ThemeIcon variant="light" color="amber" size="lg" radius="md">
            <IconChartBar size={22} />
          </ThemeIcon>
          <div>
            <Title order={2} className="font-display" style={{ fontWeight: 800, lineHeight: 1.15 }}>
              Application stats
            </Title>
            <Text size="sm" c="dimmed" mt={6}>
              Pipeline counts, sources, and a Sankey export for sharing your funnel.
            </Text>
          </div>
        </Group>
      </Box>

      <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing={{ base: "sm", sm: "md" }}>
        {KPI_CONFIG.map(({ key, label, icon: Icon, accent }) => {
          const v = summary?.[key] ?? 0;
          return (
            <Paper
              key={key}
              className="app-card stats-kpi-card"
              p={{ base: "sm", sm: "lg" }}
              withBorder
              radius="lg"
              style={{
                borderColor: accent ? "rgba(245, 158, 11, 0.25)" : undefined,
                background: accent ? "var(--accent-subtle)" : undefined,
                minWidth: 0,
              }}
            >
              <ThemeIcon variant={accent ? "filled" : "light"} color="amber" size="md" radius="md">
                <Icon size={18} />
              </ThemeIcon>
              <Text
                size="xs"
                c="dimmed"
                tt="uppercase"
                fw={700}
                style={{ letterSpacing: "0.05em", lineHeight: 1.25 }}
                mt="sm"
                lineClamp={2}
              >
                {label}
              </Text>
              <Text
                size="1.75rem"
                fw={800}
                className="font-display stats-kpi-value"
                c={accent ? "amber" : undefined}
                lh={1.05}
                style={{ fontSize: "clamp(1.35rem, 4vw, 2rem)" }}
              >
                {v}
              </Text>
            </Paper>
          );
        })}
      </SimpleGrid>

      <Grid gutter="md">
        {funnelData && funnelData.length > 0 && (
          <Grid.Col span={{ base: 12, lg: 7 }}>
            <Paper className="app-card stats-chart-card" p={{ base: "md", sm: "lg" }} withBorder radius="lg">
              <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="xs">
                Funnel
              </Text>
              <Title order={4} className="font-display" mb={{ base: "md", sm: "lg" }} fw={700} style={{ fontSize: "clamp(1rem, 4vw, 1.25rem)" }}>
                Applications by status
              </Title>
              <Box style={{ width: "100%", minWidth: 0, overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
                <BarChart
                  data={funnelData}
                  dataKey="status"
                  series={[{ name: "count", color: "amber.6" }]}
                  withBarValueLabel
                  orientation="vertical"
                  h={funnelCompact ? Math.min(420, Math.max(240, (funnelData?.length ?? 4) * 44)) : 340}
                  gridAxis="x"
                  tickLine="x"
                  yAxisProps={{
                    width: funnelCompact ? 118 : 200,
                    tickMargin: funnelCompact ? 6 : 10,
                    tick: { fontSize: funnelCompact ? 10 : 12 },
                    interval: 0,
                  }}
                  xAxisProps={{ fontSize: funnelCompact ? 10 : 12 }}
                  barChartProps={{
                    margin: funnelCompact
                      ? { left: 0, right: 20, top: 8, bottom: 8 }
                      : { left: 4, right: 28, top: 4, bottom: 4 },
                  }}
                />
              </Box>
            </Paper>
          </Grid.Col>
        )}

        {donutData && donutData.length > 0 && (
          <Grid.Col span={{ base: 12, lg: funnelData?.length ? 5 : 12 }}>
            <Paper className="app-card stats-chart-card" p="lg" withBorder radius="lg" h="100%">
              <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="xs">
                Mix
              </Text>
              <Title order={4} className="font-display" mb="lg" fw={700}>
                Applications by source
              </Title>
              <Group justify="center" py="md">
                <DonutChart
                  data={donutData}
                  size={240}
                  thickness={28}
                  withLabels
                  labelsType="percent"
                  chartLabel={`${donutData.reduce((a, c) => a + c.value, 0)} total`}
                />
              </Group>
            </Paper>
          </Grid.Col>
        )}
      </Grid>

      {timelineData.length > 0 && (
        <Paper className="app-card stats-chart-card" p="lg" withBorder radius="lg">
          <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="xs">
            Timeline
          </Text>
          <Title order={4} className="font-display" mb="xs" fw={700}>
            Jobs saved over time
          </Title>
          <Text size="xs" c="dimmed" mb="lg">
            Count per day (when each job was added). Days with no saves show as 0 so the line stays continuous.
          </Text>
          <AreaChart
            data={timelineData}
            dataKey="period"
            series={[{ name: "jobs", color: "cyan.6" }]}
            curveType="monotone"
            withDots
            h={300}
            gridAxis="x"
          />
        </Paper>
      )}

      {insights.length > 0 && (
        <Paper className="app-card" p="lg" withBorder radius="lg" style={{ borderColor: "var(--border-muted)" }}>
          <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="md">
            Insights
          </Text>
          <Stack gap="sm">
            {insights.map((line, i) => (
              <Alert key={i} color="amber" variant="light" radius="md" styles={{ message: { lineHeight: 1.55 } }}>
                {line}
              </Alert>
            ))}
          </Stack>
        </Paper>
      )}

      <Paper className="app-card" p={0} withBorder radius="lg" style={{ borderColor: "var(--border-muted)", overflow: "hidden" }}>
        <Grid gutter={0}>
          <Grid.Col span={{ base: 12, md: 5 }} p={0}>
            <SankeyPreviewVisual />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 7 }} p="lg">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase" style={{ letterSpacing: "0.06em" }} mb="xs">
              Export
            </Text>
            <Title order={4} className="font-display" mb="sm" fw={700}>
              Sankey diagram
            </Title>
            <Text size="sm" c="dimmed" mb="lg" lh={1.6}>
              Copy the flow data and paste it into{" "}
              <a href={sankey?.sankeymatic_build_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)" }}>
                SankeyMATIC
              </a>{" "}
              to build a shareable diagram: applications → interviews → outcomes.
            </Text>
            <Textarea
              label="Your pipeline (from your jobs)"
              value={sankey?.flow_text ?? ""}
              readOnly
              minRows={6}
              autosize
              maxRows={14}
              radius="md"
              styles={{ input: { fontFamily: "ui-monospace, monospace", fontSize: 13 } }}
            />
            <Group mt="md" gap="sm" wrap="wrap">
              <CopyButton value={sankey?.flow_text ?? ""}>
                {({ copied, copy }) => (
                  <Button variant="default" radius="md" onClick={copy} color={copied ? "green" : undefined}>
                    {copied ? "Copied" : "Copy flow data"}
                  </Button>
                )}
              </CopyButton>
              <Tooltip label="Copies data and opens SankeyMATIC — paste into the Inputs box (Ctrl+V)">
                <Button
                  variant="filled"
                  color="amber"
                  radius="md"
                  leftSection={<IconExternalLink size={18} />}
                  onClick={() => {
                    if (sankey?.flow_text) clipboard.copy(sankey.flow_text);
                    window.open(sankey?.sankeymatic_build_url ?? "https://sankeymatic.com/build/", "_blank");
                  }}
                >
                  Copy & open SankeyMATIC
                </Button>
              </Tooltip>
            </Group>
          </Grid.Col>
        </Grid>
      </Paper>

      {(!summary || summary.total_saved === 0) && (
        <Alert color="gray" variant="light" radius="md" title="No data yet">
          Add and track jobs to populate stats. Set source platform on job details for richer source breakdowns.
        </Alert>
      )}
    </Stack>
  );
}
