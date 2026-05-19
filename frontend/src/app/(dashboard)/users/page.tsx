"use client";

import { useState } from "react";
import type { User } from "@/core/types/models";
import { UserList } from "@/features/users/components/UserList";
import {
  CreateUserForm,
  EditUserForm,
  ResetPasswordForm,
} from "@/features/users/components/UserForm";

export default function UsersPage() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<User | null>(null);

  return (
    <div className="p-6">
      <UserList
        onCreateUser={() => setShowCreateForm(true)}
        onEditUser={(user) => setEditingUser(user)}
        onResetPassword={(user) => setResetPasswordUser(user)}
      />

      <CreateUserForm
        isOpen={showCreateForm}
        onClose={() => setShowCreateForm(false)}
      />

      <EditUserForm
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
        user={editingUser}
      />

      <ResetPasswordForm
        isOpen={!!resetPasswordUser}
        onClose={() => setResetPasswordUser(null)}
        user={resetPasswordUser}
      />
    </div>
  );
}
