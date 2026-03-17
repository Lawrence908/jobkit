import { useEffect, useState } from "react";
import {
  Title,
  Stack,
  Paper,
  TextInput,
  NumberInput,
  Button,
  Loader,
  Center,
  Alert,
  Table,
  Group,
  ActionIcon,
  Switch,
  Modal,
  Text,
  Badge,
} from "@mantine/core";
import { IconPlus, IconTrash, IconEdit, IconShieldLock } from "@tabler/icons-react";
import { api } from "../api/client";
import type { InviteCode, InviteCodeCreate, InviteCodeUpdate } from "../api/types";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export function AdminPage() {
  const [codes, setCodes] = useState<InviteCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadCodes = () => {
    setLoading(true);
    setForbidden(false);
    setError("");
    api
      .get<InviteCode[]>("/api/admin/invite-codes")
      .then(setCodes)
      .catch((e) => {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.toLowerCase().includes("admin") || msg.includes("403")) {
          setForbidden(true);
        } else {
          setError(msg || "Failed to load invite codes");
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCodes();
  }, []);

  if (loading && codes.length === 0) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (forbidden) {
    return (
      <Stack gap="md">
        <Title order={3}>Admin</Title>
        <Alert icon={<IconShieldLock size={20} />} color="red" title="Access denied">
          You must be an admin to manage invite codes.
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Invite codes</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={() => setCreateOpen(true)}>
          New invite code
        </Button>
      </Group>

      {error && (
        <Alert color="red" onClose={() => setError("")} withCloseButton>
          {error}
        </Alert>
      )}
      {success && (
        <Alert color="green" onClose={() => setSuccess("")} withCloseButton>
          {success}
        </Alert>
      )}

      <Paper withBorder p="md" radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Code</Table.Th>
              <Table.Th>Label</Table.Th>
              <Table.Th>Uses</Table.Th>
              <Table.Th>Expires</Table.Th>
              <Table.Th>Active</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {codes.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>
                  <Text ff="monospace" fw={600}>
                    {row.code}
                  </Text>
                </Table.Td>
                <Table.Td>{row.label || "—"}</Table.Td>
                <Table.Td>
                  <Badge variant={row.used_count >= row.max_uses ? "filled" : "light"} size="sm">
                    {row.used_count} / {row.max_uses}
                  </Badge>
                </Table.Td>
                <Table.Td>{formatDate(row.expires_at)}</Table.Td>
                <Table.Td>
                  <Switch
                    size="sm"
                    checked={row.is_active}
                    onChange={async (e) => {
                      const checked = e.currentTarget.checked;
                      try {
                        const updated = await api.patch<InviteCode>(
                          `/api/admin/invite-codes/${row.id}`,
                          { is_active: checked } as InviteCodeUpdate
                        );
                        setCodes((prev) => prev.map((c) => (c.id === row.id ? updated : c)));
                        setSuccess(checked ? "Code activated." : "Code deactivated.");
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Update failed");
                      }
                    }}
                  />
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {formatDate(row.created_at)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <ActionIcon
                      variant="subtle"
                      size="sm"
                      onClick={() => setEditingId(row.id)}
                      aria-label="Edit"
                    >
                      <IconEdit size={16} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      size="sm"
                      onClick={async () => {
                        if (!confirm(`Delete invite code "${row.code}"?`)) return;
                        try {
                          await api.delete(`/api/admin/invite-codes/${row.id}`);
                          setCodes((prev) => prev.filter((c) => c.id !== row.id));
                          setSuccess("Invite code deleted.");
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Delete failed");
                        }
                      }}
                      aria-label="Delete"
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {codes.length === 0 && (
          <Text c="dimmed" ta="center" py="md">
            No invite codes yet. Create one to get started.
          </Text>
        )}
      </Paper>

      <CreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(created) => {
          setCodes((prev) => [created, ...prev]);
          setCreateOpen(false);
          setSuccess("Invite code created.");
        }}
        onError={setError}
      />

      {editingId !== null && (
        <EditModal
          code={codes.find((c) => c.id === editingId)!}
          open={editingId !== null}
          onClose={() => setEditingId(null)}
          onUpdated={(updated) => {
            setCodes((prev) => prev.map((c) => (c.id === editingId ? updated : c)));
            setEditingId(null);
            setSuccess("Invite code updated.");
          }}
          onError={setError}
        />
      )}
    </Stack>
  );
}

function CreateModal({
  open,
  onClose,
  onCreated,
  onError,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (c: InviteCode) => void;
  onError: (msg: string) => void;
}) {
  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [maxUses, setMaxUses] = useState(1);
  const [expiresAt, setExpiresAt] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    onError("");
    try {
      const body: InviteCodeCreate = {
        label: label.trim() || undefined,
        max_uses: maxUses,
      };
      if (code.trim()) body.code = code.trim();
      if (expiresAt.trim()) body.expires_at = new Date(expiresAt).toISOString();
      const created = await api.post<InviteCode>("/api/admin/invite-codes", body);
      onCreated(created);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to create invite code");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="New invite code" opened={open} onClose={onClose}>
      <Stack gap="md">
        <TextInput
          label="Code (optional)"
          description="Leave blank to auto-generate"
          placeholder="e.g. welcome2025"
          value={code}
          onChange={(e) => setCode(e.currentTarget.value)}
        />
        <TextInput
          label="Label"
          placeholder="e.g. Beta testers"
          value={label}
          onChange={(e) => setLabel(e.currentTarget.value)}
        />
        <NumberInput
          label="Max uses"
          min={1}
          value={maxUses}
          onChange={(v) => setMaxUses(typeof v === "string" ? parseInt(v, 10) || 1 : v)}
        />
        <TextInput
          label="Expires at (optional)"
          type="datetime-local"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.currentTarget.value)}
        />
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={submitting}>
            Create
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function EditModal({
  code,
  open,
  onClose,
  onUpdated,
  onError,
}: {
  code: InviteCode;
  open: boolean;
  onClose: () => void;
  onUpdated: (c: InviteCode) => void;
  onError: (msg: string) => void;
}) {
  const [label, setLabel] = useState(code.label);
  const [maxUses, setMaxUses] = useState(code.max_uses);
  const [expiresAt, setExpiresAt] = useState(
    code.expires_at ? new Date(code.expires_at).toISOString().slice(0, 16) : ""
  );
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open && code) {
      setLabel(code.label);
      setMaxUses(code.max_uses);
      setExpiresAt(code.expires_at ? new Date(code.expires_at).toISOString().slice(0, 16) : "");
    }
  }, [open, code.id, code.label, code.max_uses, code.expires_at]);

  const handleSubmit = async () => {
    setSubmitting(true);
    onError("");
    try {
      const body: InviteCodeUpdate = {
        label: label.trim() || "",
        max_uses: maxUses,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      };
      const updated = await api.patch<InviteCode>(`/api/admin/invite-codes/${code.id}`, body);
      onUpdated(updated);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to update invite code");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title={`Edit: ${code.code}`} opened={open} onClose={onClose}>
      <Stack gap="md">
        <TextInput
          label="Label"
          placeholder="e.g. Beta testers"
          value={label}
          onChange={(e) => setLabel(e.currentTarget.value)}
        />
        <NumberInput
          label="Max uses"
          min={1}
          value={maxUses}
          onChange={(v) => setMaxUses(typeof v === "string" ? parseInt(v, 10) || 1 : v)}
        />
        <TextInput
          label="Expires at (optional)"
          type="datetime-local"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.currentTarget.value)}
        />
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={submitting}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
