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
import { IconDownload, IconExternalLink, IconRefresh } from "@tabler/icons-react";
import { api } from "../api/client";

export interface SheetData {
  spreadsheet_url?: string;
  sheet_name?: string;
  headers: string[];
  rows: string[][];
}

/** Tracker data from DB when Google is not connected. */
interface TrackerData {
  headers: string[];
  rows: string[][];
}

/** Escape a cell for CSV (quotes and newlines). */
function csvEscape(cell: string): string {
  const s = String(cell ?? "");
  if (s.includes('"') || s.includes("\n") || s.includes("\r") || s.includes(",")) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

/** Build CSV string from headers and rows. */
function toCSV(headers: string[], rows: string[][]): string {
  const headerLine = headers.map(csvEscape).join(",");
  const dataLines = rows.map((row) => headers.map((_, i) => csvEscape(row[i] ?? "")).join(","));
  return [headerLine, ...dataLines].join("\r\n");
}

/** Trigger download of tracker data as CSV. */
function downloadTrackerCSV(headers: string[], rows: string[][]) {
  const csv = toCSV(headers, rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `jobkit-tracker-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function SpreadsheetPage() {
  const [data, setData] = useState<SheetData | null>(null);
  const [fromDb, setFromDb] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setFromDb(false);
    api
      .get<SheetData>("/api/google/sheet")
      .then((sheetData) => {
        setData(sheetData);
        setFromDb(false);
        setLoading(false);
      })
      .catch(() => {
        api
          .get<TrackerData>("/api/jobs/tracker")
          .then((trackerData) => {
            setData({
              headers: trackerData.headers,
              rows: trackerData.rows,
            });
            setFromDb(true);
          })
          .catch((e) =>
            setError(e instanceof Error ? e.message : "Failed to load tracker"),
          )
          .finally(() => setLoading(false));
      });
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
          Tracker
        </Title>
        <Alert color="red" title="Could not load tracker">
          {error}
        </Alert>
        <Text size="sm" c="dimmed">
          Connect Google in Profile and set a spreadsheet if you want to sync to a sheet.
        </Text>
        <Button variant="light" onClick={load} leftSection={<IconRefresh size={16} />}>
          Retry
        </Button>
      </Stack>
    );
  }

  const headers = data?.headers ?? [];
  const rows = data?.rows ?? [];
  const pageTitle = fromDb ? "Tracker" : "Tracker (Google Sheet)";

  /** Min widths for key columns so content is readable; others get 120. */
  const getHeaderMinWidth = (h: string) => {
    const lower = (h || "").toLowerCase();
    if (lower.includes("company")) return 180;
    if (lower.includes("url") || lower.includes("link")) return 220;
    if (lower.includes("role")) return 160;
    if (lower.includes("status") || lower.includes("application")) return 200;
    if (lower.includes("date")) return 120;
    if (lower.includes("rejection")) return 160;
    return 120;
  };

  return (
    <Stack gap="md" style={{ width: "100%", minWidth: 0 }}>
      <Group justify="space-between" wrap="wrap" align="center" gap="md">
        <Title order={3} className="font-display" style={{ fontWeight: 700, margin: 0 }}>
          {pageTitle}
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
          <Button
            variant="subtle"
            size="sm"
            leftSection={<IconDownload size={16} />}
            onClick={() => downloadTrackerCSV(headers, rows)}
          >
            Download CSV
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

      {fromDb && (
        <Text size="sm" c="dimmed">
          Showing your jobs from JobKit. Connect Google in Profile to sync to a spreadsheet.
        </Text>
      )}

      <Paper className="app-card" withBorder radius="lg" p={0} style={{ overflow: "hidden", minWidth: 0 }}>
        <ScrollArea type="scroll" scrollbarSize="sm" offsetScrollbars style={{ maxWidth: "100%" }}>
          <Table
            striped
            highlightOnHover
            withTableBorder
            withColumnBorders
            style={{ minWidth: 1280, tableLayout: "auto" }}
          >
            <Table.Thead>
              <Table.Tr>
                {headers.map((h, i) => (
                  <Table.Th
                    key={i}
                    style={{
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      minWidth: getHeaderMinWidth(h),
                      maxWidth: 320,
                    }}
                    title={h || undefined}
                  >
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
                      <Table.Td
                        key={ci}
                        style={{
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          minWidth: getHeaderMinWidth(headers[ci]),
                          maxWidth: 320,
                        }}
                        title={cell || undefined}
                      >
                        {cell.startsWith("http") ? (
                          <Anchor
                            href={cell}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="sm"
                            style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis" }}
                          >
                            {cell}
                          </Anchor>
                        ) : (
                          cell
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
