import { type ReactNode, useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
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
  IconChartSankey,
  IconArrowRight,
  IconPlus,
  IconWand,
  IconUpload,
  IconTable,
} from "@tabler/icons-react";
import { useAuth } from "../contexts/AuthContext";
import { HubFooter } from "../components/HubFooter";
import sankeyPreviewSrc from "../assets/landing/sankey-preview.png";

/** Vite serves `public/landing/*` at `{BASE_URL}landing/*` (e.g. `frontend/public/landing/yaml-preview.png`). */
function landingPublicUrl(file: string): string {
  const b = import.meta.env.BASE_URL;
  const base = b.endsWith("/") ? b : `${b}/`;
  return `${base}${file.replace(/^\//, "")}`;
}

const LANDING_YAML_PREVIEW = landingPublicUrl("landing/yaml-preview.png");

/** URL or paste → parse → saved job (ingestion only). */
function JobIngestionDiagram() {
  return (
    <svg
      viewBox="0 0 328 104"
      style={{ width: "100%", maxHeight: 108, marginTop: 12, overflow: "visible" }}
      aria-hidden
    >
      <defs>
        <marker id="ingest-arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0 0 L6 3 L0 6 Z" fill="var(--text-muted)" />
        </marker>
      </defs>
      {/* Posting — extra horizontal inset via narrower inner label width */}
      <rect x="4" y="16" width="86" height="56" rx="8" fill="var(--border-muted)" stroke="var(--border-strong)" strokeWidth="1" />
      <text x="47" y="38" textAnchor="middle" fill="var(--text-secondary)" fontSize="10" fontWeight="600" fontFamily="var(--font-display), system-ui, sans-serif">
        Posting
      </text>
      <text x="47" y="54" textAnchor="middle" fill="var(--text-muted)" fontSize="8" fontFamily="var(--font-body), system-ui, sans-serif">
        URL or paste
      </text>
      <text x="47" y="66" textAnchor="middle" fill="var(--text-muted)" fontSize="7" fontFamily="var(--font-body), system-ui, sans-serif">
        copy-paste friendly
      </text>

      <path d="M92 44 L102 44" stroke="var(--text-muted)" strokeWidth="1.2" fill="none" markerEnd="url(#ingest-arr)" />

      <rect x="106" y="14" width="118" height="60" rx="8" fill="var(--accent-subtle)" stroke="var(--accent)" strokeWidth="1" />
      <text x="165" y="36" textAnchor="middle" fill="var(--text-secondary)" fontSize="9" fontFamily="var(--font-body), system-ui, sans-serif">
        JobKit extracts
      </text>
      <text x="165" y="56" textAnchor="middle" fill="var(--text-muted)" fontSize="7.5" fontFamily="var(--font-body), system-ui, sans-serif">
        role · company · keywords
      </text>

      <path d="M226 44 L236 44" stroke="var(--text-muted)" strokeWidth="1.2" fill="none" markerEnd="url(#ingest-arr)" />

      <rect x="240" y="18" width="76" height="52" rx="8" fill="var(--border-muted)" stroke="var(--border-strong)" strokeWidth="1" />
      <text x="278" y="40" textAnchor="middle" fill="var(--text-secondary)" fontSize="9" fontWeight="600" fontFamily="var(--font-display), system-ui, sans-serif">
        Saved job
      </text>
      <text x="278" y="56" textAnchor="middle" fill="var(--text-muted)" fontSize="7" fontFamily="var(--font-body), system-ui, sans-serif">
        ready to tailor
      </text>
    </svg>
  );
}

/** Job + career facts → match & assemble → draft docs (optional AI refine in Profile). */
function TailoringFlowDiagram() {
  return (
    <svg
      viewBox="0 0 292 148"
      style={{ width: "100%", maxHeight: 152, marginTop: 12, overflow: "visible" }}
      aria-hidden
    >
      <defs>
        <linearGradient id="tailor-draft-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.12" />
        </linearGradient>
        <marker id="tailor-arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0 0 L6 3 L0 6 Z" fill="var(--text-muted)" />
        </marker>
        <marker id="tailor-arr2" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0 0 L6 3 L0 6 Z" fill="var(--text-muted)" />
        </marker>
      </defs>
      <rect x="6" y="10" width="76" height="38" rx="6" fill="var(--border-muted)" stroke="var(--border-strong)" strokeWidth="1" />
      <text x="44" y="28" textAnchor="middle" fill="var(--text-secondary)" fontSize="8.5" fontFamily="var(--font-body), system-ui, sans-serif">
        Job description
      </text>
      <text x="44" y="40" textAnchor="middle" fill="var(--text-muted)" fontSize="7" fontFamily="var(--font-body), system-ui, sans-serif">
        from saved job
      </text>

      <rect x="6" y="56" width="76" height="38" rx="6" fill="var(--border-muted)" stroke="var(--border-strong)" strokeWidth="1" />
      <text x="44" y="74" textAnchor="middle" fill="var(--text-secondary)" fontSize="8.5" fontFamily="var(--font-body), system-ui, sans-serif">
        Career facts
      </text>
      <text x="44" y="86" textAnchor="middle" fill="var(--text-muted)" fontSize="7" fontFamily="var(--font-body), system-ui, sans-serif">
        your profile
      </text>

      <rect x="6" y="102" width="76" height="32" rx="6" fill="var(--border-muted)" stroke="var(--border-strong)" strokeWidth="1" />
      <text x="44" y="122" textAnchor="middle" fill="var(--text-secondary)" fontSize="8" fontFamily="var(--font-body), system-ui, sans-serif">
        Keywords
      </text>

      <path d="M84 29 L120 58" stroke="var(--text-muted)" strokeWidth="1.2" fill="none" markerEnd="url(#tailor-arr)" />
      <path d="M84 75 L120 68" stroke="var(--text-muted)" strokeWidth="1.2" fill="none" />
      <path d="M84 118 L120 78" stroke="var(--text-muted)" strokeWidth="1.2" fill="none" />

      <rect x="120" y="50" width="58" height="46" rx="8" fill="url(#tailor-draft-grad)" stroke="var(--accent)" strokeWidth="1.5" />
      <text x="149" y="68" textAnchor="middle" fill="var(--text-primary)" fontSize="9" fontWeight="600" fontFamily="var(--font-display), system-ui, sans-serif">
        Match &
      </text>
      <text x="149" y="82" textAnchor="middle" fill="var(--text-primary)" fontSize="9" fontWeight="600" fontFamily="var(--font-display), system-ui, sans-serif">
        assemble
      </text>

      <path d="M180 73 L194 73" stroke="var(--text-muted)" strokeWidth="1.2" fill="none" markerEnd="url(#tailor-arr2)" />

      <rect x="198" y="44" width="92" height="58" rx="8" fill="var(--accent-muted)" stroke="var(--accent)" strokeWidth="1" opacity="0.9" />
      <text x="244" y="66" textAnchor="middle" fill="var(--text-secondary)" fontSize="9" fontFamily="var(--font-body), system-ui, sans-serif">
        Draft docs
      </text>
      <text x="244" y="82" textAnchor="middle" fill="var(--text-muted)" fontSize="7.5" fontFamily="var(--font-body), system-ui, sans-serif">
        resume · letter · notes
      </text>
    </svg>
  );
}

function YamlSnippetBg() {
  const line = (parts: ReactNode[], key: string) => (
    <div key={key} style={{ whiteSpace: "pre", fontFamily: "ui-monospace, monospace", fontSize: 10, lineHeight: 1.65 }}>
      {parts}
    </div>
  );
  return (
    <Box
      pos="absolute"
      top={4}
      right={0}
      left="42%"
      style={{
        overflow: "hidden",
        borderRadius: "var(--mantine-radius-md)",
        pointerEvents: "none",
        opacity: 0.26,
        textAlign: "left",
      }}
    >
      <Box pr={4} pt={0} style={{ transform: "scale(0.92)", transformOrigin: "top right" }}>
        {line([<span key="k" style={{ color: "#c678dd" }}>skills</span>, <span key="c" style={{ color: "var(--text-muted)" }}>:</span>], "1")}
        {line([
          <span key="i" style={{ color: "var(--text-muted)" }}>  - </span>,
          <span key="n" style={{ color: "#98c379" }}>Python</span>,
        ], "2")}
        {line([
          <span key="i" style={{ color: "var(--text-muted)" }}>  - </span>,
          <span key="n" style={{ color: "#98c379" }}>FastAPI</span>,
        ], "3")}
        {line([<span key="k" style={{ color: "#c678dd" }}>experience</span>, <span key="c" style={{ color: "var(--text-muted)" }}>:</span>], "4")}
        {line([
          <span key="i" style={{ color: "var(--text-muted)" }}>  - </span>,
          <span key="r" style={{ color: "#e06c75" }}>role</span>,
          <span key="c" style={{ color: "var(--text-muted)" }}>: </span>,
          <span key="v" style={{ color: "#98c379" }}>Senior Engineer</span>,
        ], "5")}
        {line([
          <span key="i" style={{ color: "var(--text-muted)" }}>    </span>,
          <span key="r" style={{ color: "#e06c75" }}>highlights</span>,
          <span key="c" style={{ color: "var(--text-muted)" }}>: </span>,
          <span key="v" style={{ color: "#d19a66" }}>[ ]</span>,
        ], "6")}
      </Box>
    </Box>
  );
}

type FeatureKind = "default" | "ingestion" | "tailoring" | "pdfBg" | "yamlBg" | "sankeyBg";

type FeatureItem = {
  icon: typeof IconBriefcase;
  title: string;
  description: string;
  kind?: FeatureKind;
};

const features: FeatureItem[] = [
  {
    icon: IconBriefcase,
    title: "Job ingestion",
    description:
      "Paste a posting URL or drop in the full job text—no retyping into forms. JobKit pulls out role, company, and keywords so you can move straight into tailoring.",
    kind: "ingestion",
  },
  {
    icon: IconWand,
    title: "Resume & cover letter drafts",
    description:
      "JobKit scores your projects and skills against the job, then assembles draft resume and cover letter from the facts in your profile—reorder and rephrase, not invent. Add an API key in Profile if you want an LLM to polish wording; you still review everything before you send.",
    kind: "tailoring",
  },
  {
    icon: IconFileDescription,
    title: "PDF export",
    description:
      "WeasyPrint turns your markdown into consistent, print-ready PDFs—same template every time, ready to attach or upload.",
    kind: "pdfBg",
  },
  {
    icon: IconCloudUpload,
    title: "Google Drive & Sheets",
    description:
      "Connect Google once. Upload PDFs to Drive and append or update your application tracker in Sheets in a single action—column mapping fits your existing spreadsheet.",
  },
  {
    icon: IconDatabase,
    title: "Your truth store",
    description:
      "Skills, experience, education, and projects live in one structured place. Every draft is assembled from what you saved—JobKit does not fabricate employers, dates, or tech you haven’t listed. Power users can edit the same data as YAML.",
    kind: "yamlBg",
  },
  {
    icon: IconChartSankey,
    title: "Pipeline Sankey export",
    description:
      "Export your funnel as flow data for SankeyMATIC—handy when you’re juggling many roles. Copy the flows in one click, paste into SankeyMATIC, and visualize how applications move toward interviews and offers.",
    kind: "sankeyBg",
  },
];

const steps = [
  { icon: IconPlus, label: "Add job", text: "URL or pasted description" },
  { icon: IconWand, label: "Tailor", text: "Match profile to role; edit drafts" },
  { icon: IconUpload, label: "Export", text: "PDFs · optional Drive upload" },
  {
    icon: IconTable,
    label: "Track",
    text: "Pipeline in-app; optional Google Sheets sync",
  },
];

function PdfFeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: FeatureItem["icon"];
  title: string;
  description: string;
}) {
  const [photoOk, setPhotoOk] = useState(false);
  useEffect(() => {
    const img = new Image();
    img.onload = () => setPhotoOk(true);
    img.onerror = () => setPhotoOk(false);
    img.src = "/landing/pdf-preview.png";
  }, []);

  return (
    <Card padding="lg" radius="md" withBorder style={{ position: "relative", overflow: "hidden" }}>
      {photoOk ? (
        <Box
          pos="absolute"
          inset={0}
          style={{
            backgroundImage: "url(/landing/pdf-preview.png)",
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right -12px bottom -20px",
            backgroundSize: "min(220px, 58%) auto",
            opacity: 0.22,
            pointerEvents: "none",
          }}
        />
      ) : (
        <Box
          pos="absolute"
          inset={0}
          style={{
            backgroundImage: "url(/landing/pdf-card-bg.svg)",
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right -8px bottom -16px",
            backgroundSize: "min(200px, 55%) auto",
            opacity: 0.2,
            pointerEvents: "none",
          }}
        />
      )}
      <Box style={{ position: "relative", zIndex: 1 }}>
        <ThemeIcon size={40} radius="md" color="amber">
          <Icon size={22} />
        </ThemeIcon>
        <Text fw={600} mt="sm" className="font-display">
          {title}
        </Text>
        <Text size="sm" c="dimmed" mt="xs">
          {description}
        </Text>
      </Box>
    </Card>
  );
}

function SankeyFeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: FeatureItem["icon"];
  title: string;
  description: string;
}) {
  /* Bundled PNG → stable /assets/... URL in prod (public/landing URLs often 404 behind SPA routers). */
  return (
    <Card padding="lg" radius="md" withBorder style={{ position: "relative", overflow: "hidden" }}>
      <Box
        pos="absolute"
        inset={0}
        style={{
          backgroundImage: `url(${sankeyPreviewSrc})`,
          backgroundRepeat: "no-repeat",
          backgroundPosition: "right 4px top 4px",
          backgroundSize: "min(50%, 280px) auto",
          opacity: 0.5,
          pointerEvents: "none",
        }}
      />
      <Box style={{ position: "relative", zIndex: 1 }}>
        <ThemeIcon size={40} radius="md" color="amber">
          <Icon size={22} />
        </ThemeIcon>
        <Text fw={600} mt="sm" className="font-display">
          {title}
        </Text>
        <Text size="sm" c="dimmed" mt="xs">
          {description}
        </Text>
      </Box>
    </Card>
  );
}

function YamlFeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: FeatureItem["icon"];
  title: string;
  description: string;
}) {
  const [yamlImageOk, setYamlImageOk] = useState(false);
  useEffect(() => {
    const img = new Image();
    img.onload = () => setYamlImageOk(true);
    img.onerror = () => setYamlImageOk(false);
    img.src = LANDING_YAML_PREVIEW;
  }, []);

  return (
    <Card padding="lg" radius="md" withBorder style={{ position: "relative", overflow: "hidden" }}>
      {!yamlImageOk && <YamlSnippetBg />}
      {yamlImageOk && (
        <Box
          pos="absolute"
          inset={0}
          style={{
            backgroundImage: `url(${LANDING_YAML_PREVIEW})`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 4px top 4px",
            backgroundSize: "min(44%, 260px) auto",
            opacity: 0.22,
            pointerEvents: "none",
          }}
        />
      )}
      <Box style={{ position: "relative", zIndex: 1 }}>
        <ThemeIcon size={40} radius="md" color="amber">
          <Icon size={22} />
        </ThemeIcon>
        <Text fw={600} mt="sm" className="font-display">
          {title}
        </Text>
        <Text size="sm" c="dimmed" mt="xs">
          {description}
        </Text>
      </Box>
    </Card>
  );
}

function FeatureCard({ item }: { item: FeatureItem }) {
  const { icon: Icon, title, description, kind = "default" } = item;

  if (kind === "ingestion") {
    return (
      <Card padding="lg" radius="md" withBorder style={{ overflow: "visible" }}>
        <ThemeIcon size={40} radius="md" color="amber">
          <Icon size={22} />
        </ThemeIcon>
        <Text fw={600} mt="sm" className="font-display">
          {title}
        </Text>
        <JobIngestionDiagram />
        <Text size="sm" c="dimmed" mt="sm" style={{ position: "relative", zIndex: 1 }}>
          {description}
        </Text>
      </Card>
    );
  }

  if (kind === "tailoring") {
    return (
      <Card padding="lg" radius="md" withBorder style={{ overflow: "visible" }}>
        <ThemeIcon size={40} radius="md" color="amber">
          <Icon size={22} />
        </ThemeIcon>
        <Text fw={600} mt="sm" className="font-display">
          {title}
        </Text>
        <TailoringFlowDiagram />
        <Text size="sm" c="dimmed" mt="sm" style={{ position: "relative", zIndex: 1 }}>
          {description}
        </Text>
      </Card>
    );
  }

  if (kind === "pdfBg") {
    return <PdfFeatureCard icon={Icon} title={title} description={description} />;
  }

  if (kind === "yamlBg") {
    return <YamlFeatureCard icon={Icon} title={title} description={description} />;
  }

  if (kind === "sankeyBg") {
    return <SankeyFeatureCard icon={Icon} title={title} description={description} />;
  }

  return (
    <Card padding="lg" radius="md" withBorder>
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
  );
}

export function LandingPage() {
  const { session, loading, demoLogin } = useAuth();
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState("");
  const navigate = useNavigate();

  const handleDemoLogin = async () => {
    setDemoError("");
    setDemoLoading(true);
    try {
      const { error } = await demoLogin();
      if (error) {
        setDemoError(error);
      } else {
        navigate("/dashboard/profile", { replace: true });
      }
    } finally {
      setDemoLoading(false);
    }
  };

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
          <Text size="xl" c="dimmed" ta="center" maw={580}>
            From saved posting to tailored resume and cover letter—built from{" "}
            <Text component="span" fw={600} c="var(--mantine-color-text)">
              your
            </Text>{" "}
            career facts, then exported as PDFs and tracked in one place. Optional LLM in Profile polishes wording; optional
            Google sync handles Drive and Sheets. You stay in control of what ships.
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
          <Button
            variant="subtle"
            color="amber"
            size="md"
            loading={demoLoading}
            onClick={handleDemoLogin}
          >
            Try the demo
          </Button>
          {demoError && (
            <Text size="sm" c="red" ta="center">
              {demoError}
            </Text>
          )}
        </Stack>

        {/* Features */}
        <Box py={48}>
          <Title order={2} ta="center" mb="xl" className="font-display">
            What JobKit does
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
            {features.map((item) => (
              <FeatureCard key={item.title} item={item} />
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
            Ready to try it?
          </Title>
          <Text size="sm" c="dimmed" ta="center" maw={480}>
            Sign up with an invite code, or use the demo above to explore the profile and workflow.
          </Text>
          <Button component={Link} to="/register" color="amber" size="md">
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
