"use client";

import { useState, useCallback } from "react";
import { Table, SearchInput, Button } from "@/shared/ui";
import type { TableColumn } from "@/shared/ui";
import type { User, UserRole } from "@/core/types/models";
import { useUsers, useDeactivateUser } from "../hooks/useUsers";

interface UserListProps {
  onCreateUser: () => void;
  onEditUser: (user: User) => void;
  onResetPassword: (user: User) => void;
}

export function UserList({ onCreateUser, onEditUser, onResetPassword }: UserListProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<UserRole | "">("");
  const [activeFilter, setActiveFilter] = useState<"" | "true" | "false">("");

  const { data, isLoading } = useUsers({
    page,
    page_size: 20,
    search: search || undefined,
    role: roleFilter || undefined,
    is_active: activeFilter === "" ? undefined : activeFilter === "true",
  });

  const deactivateMutation = useDeactivateUser();

  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    setPage(1);
  }, []);

  const handleRoleChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setRoleFilter(e.target.value as UserRole | "");
    setPage(1);
  }, []);

  const handleActiveChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setActiveFilter(e.target.value as "" | "true" | "false");
    setPage(1);
  }, []);

  const handleDeactivate = useCallback(
    (userId: string) => {
      if (window.confirm("Are you sure you want to deactivate this user?")) {
        deactivateMutation.mutate(userId);
      }
    },
    [deactivateMutation]
  );

  const columns: TableColumn<User & Record<string, unknown>>[] = [
    {
      key: "full_name",
      header: "Name",
    },
    {
      key: "email",
      header: "Email",
    },
    {
      key: "role",
      header: "Role",
      render: (row) => (
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            row.role === "admin"
              ? "bg-primary-100 text-primary-800"
              : "bg-neutral-100 text-neutral-800"
          }`}
        >
          {row.role === "admin" ? "Admin" : "Staff"}
        </span>
      ),
    },
    {
      key: "is_active",
      header: "Status",
      render: (row) => (
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            row.is_active
              ? "bg-success-100 text-success-800"
              : "bg-danger-100 text-danger-800"
          }`}
        >
          {row.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onEditUser(row)}
            className="text-sm text-primary-600 hover:text-primary-800 font-medium"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onResetPassword(row)}
            className="text-sm text-neutral-600 hover:text-neutral-800 font-medium"
          >
            Reset Password
          </button>
          {row.is_active && (
            <button
              type="button"
              onClick={() => handleDeactivate(row.id)}
              className="text-sm text-danger-600 hover:text-danger-800 font-medium"
            >
              Deactivate
            </button>
          )}
        </div>
      ),
    },
  ];

  const users = (data?.data ?? []) as (User & Record<string, unknown>)[];
  const totalPages = data?.meta?.total_pages ?? 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-neutral-900">User Management</h1>
        <Button onClick={onCreateUser}>Add User</Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="w-full sm:max-w-xs">
          <SearchInput
            value={search}
            onChange={handleSearch}
            placeholder="Search by name or email..."
          />
        </div>
        <select
          value={roleFilter}
          onChange={handleRoleChange}
          aria-label="Filter by role"
          className="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
        >
          <option value="">All Roles</option>
          <option value="admin">Admin</option>
          <option value="staff">Staff</option>
        </select>
        <select
          value={activeFilter}
          onChange={handleActiveChange}
          aria-label="Filter by status"
          className="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : (
        <Table
          columns={columns}
          data={users}
          pagination={{ page, totalPages }}
          onPageChange={setPage}
          emptyMessage="No users found"
        />
      )}
    </div>
  );
}
