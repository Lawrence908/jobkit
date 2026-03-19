import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Stack,
  Text,
  Button,
  Loader,
  Alert,
  Paper,
  Title,
  List,
  Accordion,
  Box,
  Divider,
  Group,
  Anchor,
} from "@mantine/core";
import { IconBulb, IconFileText, IconDownload, IconRefresh } from "@tabler/icons-react";
import { api } from "../api/client";
import type { InterviewPrepRecord } from "../api/types";

function catchMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === "string") return err;
  return fallback;
}

interface InterviewPrepResponse {
  prep: InterviewPrepRecord | null;
}

export function InterviewPrepPanel({ jobId }: { jobId: number }) {
  const [prep, setPrep] = useState<InterviewPrepRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [renderingPdf, setRenderingPdf] = useState(false);
  const [error, setError] = useState("");
  const [pdfDownloadUrl, setPdfDownloadUrl] = useState<string | null>(null);
  /** User has saved an LLM key on profile (server-wide key is invisible here). */
  const [hasPersonalLlmKey, setHasPersonalLlmKey] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .get<{ llm_api_key?: string }>("/api/profile")
      .then((p) => setHasPersonalLlmKey(Boolean(p.llm_api_key && String(p.llm_api_key).trim())))
      .catch(() => setHasPersonalLlmKey(false));
  }, []);

  const fetchPrep = useCallback(() => {
    setLoading(true);
    api
      .get<InterviewPrepResponse>(`/api/jobs/${jobId}/interview-prep`)
      .then((r) => setPrep(r.prep))
      .catch(() => setPrep(null))
      .finally(() => setLoading(false));
  }, [jobId]);

  const fetchArtifacts = useCallback(() => {
    api.get<Array<{ id: number; type: string; download_url: string | null }>>(`/api/jobs/${jobId}/artifacts`).then((list) => {
      const pdf = list.find((a) => a.type === "interview_prep_pdf");
      setPdfDownloadUrl(pdf?.download_url ?? null);
    }).catch(() => setPdfDownloadUrl(null));
  }, [jobId]);

  useEffect(() => {
    fetchPrep();
  }, [fetchPrep]);

  useEffect(() => {
    if (prep) fetchArtifacts();
  }, [prep, fetchArtifacts]);

  const handleGenerate = async () => {
    setError("");
    setGenerating(true);
    try {
      await api.post(`/api/jobs/${jobId}/interview-prep/generate`, {});
      fetchPrep();
    } catch (err) {
      setError(catchMessage(err, "Generation failed"));
    } finally {
      setGenerating(false);
    }
  };

  const handleRenderPdf = async () => {
    if (!prep) return;
    setError("");
    setRenderingPdf(true);
    try {
      await api.post(`/api/jobs/${jobId}/interview-prep/${prep.id}/render-pdf`, {});
      setTimeout(() => {
        fetchArtifacts();
        setRenderingPdf(false);
      }, 4000);
    } catch (err) {
      setError(catchMessage(err, "PDF render failed"));
      setRenderingPdf(false);
    }
  };

  if (loading) {
    return (
      <Box py="xl">
        <Loader size="sm" />
      </Box>
    );
  }

  const summary = prep?.summary_json;

  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap">
        <Group>
          <Button
            leftSection={prep ? <IconRefresh size={16} /> : <IconBulb size={16} />}
            loading={generating}
            onClick={handleGenerate}
            variant={prep ? "light" : "filled"}
          >
            {prep ? `Regenerate (v${prep.version})` : "Generate interview prep"}
          </Button>
          {prep && (
            <Button
              leftSection={<IconFileText size={16} />}
              loading={renderingPdf}
              onClick={handleRenderPdf}
              variant="default"
            >
              Export PDF
            </Button>
          )}
        </Group>
        {pdfDownloadUrl && (
          <Anchor href={pdfDownloadUrl} target="_blank" rel="noopener noreferrer" size="sm">
            <Group gap={4}>
              <IconDownload size={14} /> Download interview prep PDF
            </Group>
          </Anchor>
        )}
      </Group>

      {error && (
        <Alert color="red" onClose={() => setError("")} withCloseButton>
          {error}
        </Alert>
      )}

      {hasPersonalLlmKey === false && (
        <Alert color="gray" variant="light" title="AI API key">
          <Text size="sm">
            Interview prep is{" "}
            <Text span fw={600}>
              AI-generated
            </Text>{" "}
            (unlike resume/cover drafts, which can run without AI). Add an OpenAI-compatible key under{" "}
            <Anchor component={Link} to="/dashboard/profile" fw={600}>
              Profile → LLM
            </Anchor>
            . If your host already configured a server key, Generate may still work.
          </Text>
        </Alert>
      )}

      {!prep && !generating && (
        <Paper p="lg" withBorder>
          <Stack gap="xs">
            <Text c="dimmed">
              Generate an interview prep package tailored to this job: likely questions, STAR prompts, talking points,
              and match analysis from your profile, resume, matched projects, and the job description. Regenerate anytime
              for a fresh take.
            </Text>
            <Text size="xs" c="dimmed" fs="italic">
              AI-powered features may become subscription-tier later; for now they use your key or server LLM config.
            </Text>
          </Stack>
        </Paper>
      )}

      {prep && summary && (
        <Stack gap="lg">
          {summary.personal_pitch && (
            <Paper p="md" withBorder>
              <Title order={4} mb="xs">
                Personal pitch (Tell me about yourself)
              </Title>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {summary.personal_pitch}
              </Text>
            </Paper>
          )}

          {summary.likely_questions && Object.keys(summary.likely_questions).length > 0 && (
            <Paper p="md" withBorder>
              <Title order={4} mb="sm">
                Likely interview questions
              </Title>
              <Accordion variant="separated">
                {Object.entries(summary.likely_questions).map(([category, questions]) =>
                  Array.isArray(questions) && questions.length > 0 ? (
                    <Accordion.Item key={category} value={category}>
                      <Accordion.Control>
                        {category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </Accordion.Control>
                      <Accordion.Panel>
                        <List size="sm">
                          {questions.map((q, i) => (
                            <List.Item key={i}>{q}</List.Item>
                          ))}
                        </List>
                      </Accordion.Panel>
                    </Accordion.Item>
                  ) : null,
                )}
              </Accordion>
            </Paper>
          )}

          {summary.talking_points && Object.keys(summary.talking_points).length > 0 && (
            <Paper p="md" withBorder>
              <Title order={4} mb="sm">
                Suggested talking points
              </Title>
              <Accordion variant="separated">
                {Object.entries(summary.talking_points).map(([category, points]) =>
                  Array.isArray(points) && points.length > 0 ? (
                    <Accordion.Item key={category} value={category}>
                      <Accordion.Control>
                        {category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </Accordion.Control>
                      <Accordion.Panel>
                        <List size="sm">
                          {points.map((p, i) => (
                            <List.Item key={i}>{p}</List.Item>
                          ))}
                        </List>
                      </Accordion.Panel>
                    </Accordion.Item>
                  ) : null,
                )}
              </Accordion>
            </Paper>
          )}

          {summary.match_analysis &&
            (summary.match_analysis.strongest_alignment?.length ||
              summary.match_analysis.weakest_alignment?.length ||
              summary.match_analysis.likely_probed_areas?.length ||
              summary.match_analysis.missing_keywords?.length) && (
              <Paper p="md" withBorder>
                <Title order={4} mb="sm">
                  Match analysis
                </Title>
                <Stack gap="xs">
                  {summary.match_analysis.strongest_alignment?.length ? (
                    <Box>
                      <Text fw={600} size="sm" c="green" mb={4}>
                        Strongest alignment
                      </Text>
                      <List size="sm">
                        {summary.match_analysis.strongest_alignment.map((s, i) => (
                          <List.Item key={i}>{s}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                  {summary.match_analysis.weakest_alignment?.length ? (
                    <Box>
                      <Text fw={600} size="sm" c="orange" mb={4}>
                        Weakest alignment
                      </Text>
                      <List size="sm">
                        {summary.match_analysis.weakest_alignment.map((w, i) => (
                          <List.Item key={i}>{w}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                  {summary.match_analysis.likely_probed_areas?.length ? (
                    <Box>
                      <Text fw={600} size="sm" mb={4}>
                        Likely probed areas
                      </Text>
                      <List size="sm">
                        {summary.match_analysis.likely_probed_areas.map((a, i) => (
                          <List.Item key={i}>{a}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                  {summary.match_analysis.missing_keywords?.length ? (
                    <Box>
                      <Text fw={600} size="sm" c="dimmed" mb={4}>
                        Missing keywords
                      </Text>
                      <List size="sm">
                        {summary.match_analysis.missing_keywords.map((k, i) => (
                          <List.Item key={i}>{k}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                </Stack>
              </Paper>
            )}

          {summary.star_responses && summary.star_responses.length > 0 && (
            <Paper p="md" withBorder>
              <Title order={4} mb="sm">
                STAR response suggestions
              </Title>
              <Accordion variant="separated">
                {summary.star_responses.map((star, i) => (
                  <Accordion.Item key={i} value={`star-${i}`}>
                    <Accordion.Control>{star.prompt || `Example ${i + 1}`}</Accordion.Control>
                    <Accordion.Panel>
                      <Stack gap="xs">
                        {star.situation && (
                          <Box>
                            <Text fw={600} size="xs" c="dimmed">
                              Situation
                            </Text>
                            <Text size="sm">{star.situation}</Text>
                          </Box>
                        )}
                        {star.task && (
                          <Box>
                            <Text fw={600} size="xs" c="dimmed">
                              Task
                            </Text>
                            <Text size="sm">{star.task}</Text>
                          </Box>
                        )}
                        {star.action && (
                          <Box>
                            <Text fw={600} size="xs" c="dimmed">
                              Action
                            </Text>
                            <Text size="sm">{star.action}</Text>
                          </Box>
                        )}
                        {star.result && (
                          <Box>
                            <Text fw={600} size="xs" c="dimmed">
                              Result
                            </Text>
                            <Text size="sm">{star.result}</Text>
                          </Box>
                        )}
                      </Stack>
                    </Accordion.Panel>
                  </Accordion.Item>
                ))}
              </Accordion>
            </Paper>
          )}

          {summary.technical_prep &&
            (summary.technical_prep.topics_to_review?.length ||
              summary.technical_prep.tools_frameworks?.length ||
              summary.technical_prep.system_design_themes?.length ||
              summary.technical_prep.coding_areas?.length) && (
              <Paper p="md" withBorder>
                <Title order={4} mb="sm">
                  Technical prep
                </Title>
                <Stack gap="sm">
                  {summary.technical_prep.topics_to_review?.length ? (
                    <Box>
                      <Text fw={600} size="xs" c="dimmed">
                        Topics to review
                      </Text>
                      <List size="sm">
                        {summary.technical_prep.topics_to_review.map((t, i) => (
                          <List.Item key={i}>{t}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                  {summary.technical_prep.tools_frameworks?.length ? (
                    <Box>
                      <Text fw={600} size="xs" c="dimmed">
                        Tools / frameworks
                      </Text>
                      <List size="sm">
                        {summary.technical_prep.tools_frameworks.map((t, i) => (
                          <List.Item key={i}>{t}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                  {summary.technical_prep.system_design_themes?.length ? (
                    <Box>
                      <Text fw={600} size="xs" c="dimmed">
                        System design themes
                      </Text>
                      <List size="sm">
                        {summary.technical_prep.system_design_themes.map((t, i) => (
                          <List.Item key={i}>{t}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                  {summary.technical_prep.coding_areas?.length ? (
                    <Box>
                      <Text fw={600} size="xs" c="dimmed">
                        Coding areas
                      </Text>
                      <List size="sm">
                        {summary.technical_prep.coding_areas.map((c, i) => (
                          <List.Item key={i}>{c}</List.Item>
                        ))}
                      </List>
                    </Box>
                  ) : null}
                </Stack>
              </Paper>
            )}

          {summary.questions_to_ask && summary.questions_to_ask.length > 0 && (
            <Paper p="md" withBorder>
              <Title order={4} mb="sm">
                Questions to ask the employer
              </Title>
              <List size="sm">
                {summary.questions_to_ask.map((q, i) => (
                  <List.Item key={i}>{q}</List.Item>
                ))}
              </List>
            </Paper>
          )}

          <Divider />
          <Paper p="md" withBorder>
            <Title order={5} mb="xs">
              Full markdown
            </Title>
            <Text size="xs" c="dimmed" mb="xs">
              Version {prep.version} · Generated {prep.created_at ? new Date(prep.created_at).toLocaleString() : ""}
            </Text>
            <Box
              component="pre"
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "monospace",
                fontSize: 12,
                maxHeight: 300,
                overflow: "auto",
                margin: 0,
                padding: 8,
                background: "var(--mantine-color-dark-6)",
                borderRadius: 4,
              }}
            >
              {prep.markdown_text}
            </Box>
          </Paper>
        </Stack>
      )}
    </Stack>
  );
}
