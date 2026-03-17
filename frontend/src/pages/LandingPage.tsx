import { Link, Navigate } from "react-router-dom";
import {
  Title,
  Text,
  Button,
  Stack,
  Group,
  SimpleGrid,
  Card,
  ThemeIcon,
  Container,
  Anchor,
  Box,
} from "@mantine/core";
import {
  IconBriefcase,
  IconFileDescription,
  IconCloudUpload,
  IconDatabase,
  IconServer,
  IconArrowRight,
  IconPlus,
  IconWand,
  IconUpload,
} from "@tabler/icons-react";
import { useAuth } from "../contexts/AuthContext";
import { HubFooter } from "../components/HubFooter";

const features = [
  {
    icon: IconBriefcase,
    title: "Job ingestion",
    description: "Paste a job URL or raw description. JobKit extracts role, company, keywords, and stores everything for tailoring.",
  },
  {
    icon: IconWand,
    title: "AI tailoring",
    description: "LLM generates tailored resume, cover letter, and notes from your truth store—no hallucinated facts.",
  },
  {
    icon: IconFileDescription,
    title: "PDF rendering",
    description: "WeasyPrint turns your markdown into clean, professional PDFs ready to submit.",
  },
  {
    icon: IconCloudUpload,
    title: "Google integration",
    description: "Upload artifacts to Drive and log applications to a Google Sheet tracker with one click.",
  },
  {
    icon: IconDatabase,
    title: "Truth store",
    description: "Master resume, skills, and projects in YAML. One source of truth for every application.",
  },
  {
    icon: IconServer,
    title: "Self-hosted",
    description: "Run on your own infrastructure. Own your data and tailor your stack.",
  },
];

const steps = [
  { icon: IconPlus, label: "Add job", text: "Paste a URL or description" },
  { icon: IconWand, label: "Generate", text: "Tailor resume & cover letter" },
  { icon: IconUpload, label: "Export", text: "PDF, Drive, Sheets" },
];

export function LandingPage() {
  const { session, loading } = useAuth();

  if (loading) return null;
  if (session) return <Navigate to="/dashboard" replace />;

  return (
    <Box style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Container size="md" style={{ flex: "1 1 auto" }}>
        {/* Hero */}
        <Stack align="center" gap="xl" py={60} px="md">
          <Title
            order={1}
            className="font-display"
            style={{ fontWeight: 700, fontSize: "clamp(2rem, 5vw, 3rem)", textAlign: "center" }}
          >
            JobKit
          </Title>
          <Text size="xl" c="dimmed" ta="center" maw={520}>
            Your AI-powered job application toolkit. Ingest jobs, tailor resumes and cover letters, render PDFs, and track everything.
          </Text>
          <Group gap="md">
            <Button
              component={Link}
              to="/register"
              color="amber"
              size="lg"
              rightSection={<IconArrowRight size={18} />}
            >
              Get started
            </Button>
            <Button component={Link} to="/login" variant="light" color="gray" size="lg">
              Log in
            </Button>
          </Group>
        </Stack>

        {/* Features */}
        <Box py={48}>
          <Title order={2} ta="center" mb="xl" className="font-display">
            What you get
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
            {features.map(({ icon: Icon, title, description }) => (
              <Card key={title} padding="lg" radius="md" withBorder>
                <ThemeIcon size={40} radius="md" color="amber">
                  <Icon size={22} />
                </ThemeIcon>
                <Text fw={600} mt="sm" className="font-display">
                  {title}
                </Text>
                <Text size="sm" c="dimmed" mt="xs">
                  {description}
                </Text>
              </Card>
            ))}
          </SimpleGrid>
        </Box>

        {/* How it works */}
        <Box py={48}>
          <Title order={2} ta="center" mb="xl" className="font-display">
            How it works
          </Title>
          <Group justify="center" gap="xl" wrap="wrap">
            {steps.map(({ icon: Icon, label, text }) => (
              <Stack key={label} align="center" gap="xs">
                <ThemeIcon size={48} radius="xl" color="amber">
                  <Icon size={24} />
                </ThemeIcon>
                <Text fw={600} size="sm">
                  {label}
                </Text>
                <Text size="xs" c="dimmed">
                  {text}
                </Text>
              </Stack>
            ))}
          </Group>
        </Box>

        {/* Footer CTA */}
        <Stack align="center" gap="md" py={48}>
          <Title order={3} ta="center" className="font-display">
            Ready to get started?
          </Title>
          <Text size="sm" c="dimmed" ta="center">
            Create an account with an invite code to start tailoring your applications.
          </Text>
          <Button
            component={Link}
            to="/register"
            color="amber"
            size="md"
          >
            Register
          </Button>
          <Text size="xs" c="dimmed">
            <Anchor href="https://chrislawrence.ca" target="_blank" rel="noopener noreferrer">
              chrislawrence.ca
            </Anchor>
          </Text>
        </Stack>
      </Container>

      <footer style={{ flexShrink: 0 }}>
        <HubFooter />
      </footer>
    </Box>
  );
}
