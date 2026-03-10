import { useState, useEffect, useCallback } from "react";
import { type ColumnDef, type RowSelectionState } from "@tanstack/react-table";
import { Shield, ShieldCheck, Ban, X } from "lucide-react";
import { toast } from "sonner";
import { adminApi } from "../../lib/admin-api";
import DataTable from "../../components/admin/DataTable";
import ConfirmDialog from "../../components/admin/ConfirmDialog";
import BulkActionBar from "../../components/admin/BulkActionBar";
import ExportButton from "../../components/admin/ExportButton";
import type { AdminUser, AdminRole } from "../../lib/admin-types";

const ROLE_BADGE: Record<string, string> = {
  user: "bg-slate-500/20 text-slate-300",
  admin: "bg-primary/20 text-primary-light",
  superadmin: "bg-accent/20 text-accent",
};

const TIER_BADGE: Record<string, string> = {
  free: "bg-slate-500/20 text-slate-400",
  starter: "bg-blue-500/20 text-blue-400",
  professional: "bg-primary/20 text-primary-light",
  business: "bg-accent/20 text-accent",
  enterprise: "bg-success/20 text-success",
};

export default function UserManagementPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search] = useState("");
  const [, setLoading] = useState(true);
  const [selection, setSelection] = useState<RowSelectionState>({});
  const [confirm, setConfirm] = useState<{ userId: string; action: string } | null>(null);
  const [detailUser, setDetailUser] = useState<AdminUser | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getUsers(page, search);
      setUsers(res.users);
      setTotal(res.total);
    } catch {
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { load(); }, [load]);

  async function changeRole(userId: string, role: AdminRole) {
    try {
      await adminApi.updateUserRole(userId, role);
      toast.success(`Role updated to ${role}`);
      load();
    } catch {
      toast.error("Failed to update role");
    }
  }

  async function toggleSuspend(userId: string, isSuspended: boolean) {
    try {
      await adminApi.suspendUser(userId, !isSuspended);
      toast.success(isSuspended ? "User activated" : "User suspended");
      load();
    } catch {
      toast.error("Failed to update user status");
    }
  }

  const columns: ColumnDef<AdminUser, unknown>[] = [
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary-light">
            {(row.original.email || "?").charAt(0).toUpperCase()}
          </div>
          <span className="text-white">{row.original.email}</span>
        </div>
      ),
    },
    { accessorKey: "company_name", header: "Company", cell: ({ getValue }) => getValue() || "-" },
    {
      accessorKey: "role",
      header: "Role",
      cell: ({ getValue }) => {
        const r = String(getValue() || "user");
        return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_BADGE[r] || ""}`}>{r}</span>;
      },
    },
    {
      accessorKey: "tier",
      header: "Tier",
      cell: ({ getValue }) => {
        const t = String(getValue() || "free");
        return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TIER_BADGE[t] || ""}`}>{t}</span>;
      },
    },
    { accessorKey: "credits_balance", header: "Credits", cell: ({ getValue }) => getValue() ?? "-" },
    {
      accessorKey: "created_at",
      header: "Joined",
      cell: ({ getValue }) => getValue() ? new Date(String(getValue())).toLocaleDateString() : "-",
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); changeRole(row.original.id, row.original.role === "admin" ? "user" : "admin"); }}
            title={row.original.role === "admin" ? "Remove admin" : "Make admin"}
            className="rounded p-1 text-slate-500 hover:bg-white/5 hover:text-primary-light"
          >
            {row.original.role === "admin" ? <ShieldCheck className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); toggleSuspend(row.original.id, row.original.status === "suspended"); }}
            title={row.original.status === "suspended" ? "Activate" : "Suspend"}
            className="rounded p-1 text-slate-500 hover:bg-white/5 hover:text-warning"
          >
            <Ban className="h-4 w-4" />
          </button>
        </div>
      ),
      enableSorting: false,
    },
  ];

  const selectedIds = Object.keys(selection).map((i) => users[Number(i)]?.id).filter(Boolean);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-white">User Management</h1>
        <div className="flex items-center gap-2">
          <ExportButton data={users} filename="users" />
        </div>
      </div>

      <DataTable
        data={users}
        columns={columns}
        selectable
        selectedRows={selection}
        onSelectionChange={setSelection}
        onRowClick={(user) => setDetailUser(user)}
        serverPagination={{
          pageIndex: page - 1,
          pageCount: Math.ceil(total / 25),
          onPageChange: (p) => setPage(p + 1),
        }}
      />

      <BulkActionBar
        count={selectedIds.length}
        actions={[
          { label: "Make Admin", onClick: () => selectedIds.forEach((id) => changeRole(id, "admin")) },
          { label: "Suspend", variant: "danger", onClick: () => selectedIds.forEach((id) => toggleSuspend(id, false)) },
        ]}
        onClear={() => setSelection({})}
      />

      {/* Detail drawer */}
      {detailUser && (
        <div className="fixed inset-y-0 end-0 z-50 w-full max-w-md border-s border-dark-border bg-[#06060a] p-6 shadow-2xl overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-white">User Details</h2>
            <button onClick={() => setDetailUser(null)} className="text-slate-500 hover:text-white">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500">Email</label>
              <p className="text-white">{detailUser.email}</p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Role</label>
              <p><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_BADGE[detailUser.role]}`}>{detailUser.role}</span></p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Tier</label>
              <p><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TIER_BADGE[detailUser.tier || "free"]}`}>{detailUser.tier || "free"}</span></p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Company</label>
              <p className="text-slate-300">{detailUser.company_name || "Not set"}</p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Credits</label>
              <p className="text-white">{detailUser.credits_balance ?? 0}</p>
            </div>
            <div>
              <label className="text-xs text-slate-500">Joined</label>
              <p className="text-slate-300">{detailUser.created_at ? new Date(detailUser.created_at).toLocaleDateString() : "-"}</p>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.action === "suspend" ? "Suspend User?" : "Confirm Action"}
        message="This action can be reversed later."
        variant={confirm?.action === "suspend" ? "warning" : "default"}
        onConfirm={() => { setConfirm(null); }}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
