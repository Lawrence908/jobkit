import { useCallback, useEffect, useState } from "react";
import {
  Title,
  Stack,
  Paper,
  Table,
  ScrollArea,
  Button,
  Loader,
  Alert,
  Text,
  Group,
  Anchor,
} from "@mantine/core";
import { IconExternalLink, IconRefresh } from "@tabler/icons-react";
import { api } from "../api/client";

export interface SheetData {
  spreadsheet_url: string;
  sheet_name: string;
  headers: string[];
  rows: string[][];
}

export function SpreadsheetPage() {
  const [data, setData] = useState<SheetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .get<SheetData>("/api/google/sheet")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load sheet"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return (
      <div className="page-container" style={{ display: "flex", justifyContent: "center", paddingTop: "3rem" }}>
        <Loader color="amber" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <Stack gap="md" style={{ width: "100%" }}>
        <Title order={3} className="font-display" style={{ fontWeight: 700, margin: 0 }}>
          Tracker (Google Sheet)
        </Title>
        <Alert color="red" title="Could not load sheet">
          {error}
        </Alert>
        <Text size="sm" c="dimmed">
          Connect Google in Profile and ensure GOOGLE_SHEETS_SPREADSHEET_ID and tab name are set.
        </Text>
        <Button variant="light" onClick={load} leftSection={<IconRefresh size={16} />}>
          Retry
        </Button>
      </Stack>
    );
  }

  const headers = data?.headers ?? [];
  const rows = data?.rows ?? [];

  return (
    <Stack gap="md" style={{ width: "100%" }}>
      <Group justify="space-between" wrap="wrap" align="center" gap="md">
        <Title order={3} className="font-display" style={{ fontWeight: 700, margin: 0 }}>
          Tracker (Google Sheet)
        </Title>
        <Group gap="xs">
          <Button
            variant="subtle"
            size="sm"
            leftSection={<IconRefresh size={16} />}
            onClick={load}
            loading={loading}
          >
            Refresh
          </Button>
          {data?.spreadsheet_url && (
            <Button
              component="a"
              href={data.spreadsheet_url}
              target="_blank"
              rel="noopener noreferrer"
              variant="light"
              size="sm"
              leftSection={<IconExternalLink size={16} />}
            >
              Open in Google Sheets
            </Button>
          )}
        </Group>
      </Group>

      {data?.sheet_name && (
        <Text size="sm" c="dimmed">
          Tab: {data.sheet_name}
        </Text>
      )}

      <Paper className="app-card" withBorder radius="lg" p={0} style={{ overflow: "hidden" }}>
        <ScrollArea type="auto" scrollbarSize="sm" offsetScrollbars>
          <Table striped highlightOnHover withTableBorder withColumnBorders style={{ minWidth: 600 }}>
            <Table.Thead>
              <Table.Tr>
                {headers.map((h, i) => (
                  <Table.Th key={i} style={{ whiteSpace: "nowrap", fontWeight: 600 }}>
                    {h || `Col ${i + 1}`}
                  </Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={headers.length || 1} c="dimmed" ta="center" py="xl">
                    No rows yet. Upload & log from a job to add rows.
                  </Table.Td>
                </Table.Tr>
              ) : (
                rows.map((row, ri) => (
                  <Table.Tr key={ri}>
                    {row.map((cell, ci) => (
                      <Table.Td key={ci} style={{ maxWidth: 280 }} title={cell}>
                        {cell.startsWith("http") ? (
                          <Anchor href={cell} target="_blank" rel="noopener noreferrer" size="sm">
                            {cell.length > 50 ? cell.slice(0, 47) + "…" : cell}
                          </Anchor>
                        ) : (
                          cell.length > 60 ? cell.slice(0, 57) + "…" : cell
                        )}
                      </Table.Td>
                    ))}
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </Paper>
    </Stack>
  );
}
