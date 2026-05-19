"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, Input, Select, Modal } from "@/shared/ui";
import type { User } from "@/core/types/models";
import { useCreateUser, useUpdateUser, useResetPassword } from "../hooks/useUsers";
import { getErrorMessage } from "@/core/api/error-handler";

// --- Schemas ---

const createUserSchema = z.object({
  full_name: z.string().min(1, "Name is required").max(100, "Name must be 100 characters or less"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  role: z.enum(["admin", "staff"], { message: "Role is required" }),
});

const editUserSchema = z.object({
  full_name: z.string().min(1, "Name is required").max(100, "Name must be 100 characters or less"),
  email: z.string().email("Invalid email address"),
  role: z.enum(["admin", "staff"], { message: "Role is required" }),
});

const resetPasswordSchema = z.object({
  new_password: z.string().min(8, "Password must be at least 8 characters"),
});

type CreateUserFormData = z.infer<typeof createUserSchema>;
type EditUserFormData = z.infer<typeof editUserSchema>;
type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

// --- Create User Form ---

interface CreateUserFormProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateUserForm({ isOpen, onClose }: CreateUserFormProps) {
  const createMutation = useCreateUser();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    setError,
  } = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
  });

  useEffect(() => {
    if (!isOpen) {
      reset();
      createMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, reset]);

  const onSubmit = (data: CreateUserFormData) => {
    createMutation.mutate(data, {
      onSuccess: () => {
        onClose();
      },
      onError: (error) => {
        setError("root", { message: getErrorMessage(error) });
      },
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create User">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {errors.root && (
          <div className="rounded-lg bg-danger-50 px-4 py-3 text-sm text-danger-700" role="alert">
            {errors.root.message}
          </div>
        )}

        <Input
          label="Full Name"
          placeholder="Enter full name"
          error={errors.full_name?.message}
          register={register("full_name")}
        />

        <Input
          label="Email"
          type="email"
          placeholder="Enter email address"
          error={errors.email?.message}
          register={register("email")}
        />

        <Input
          label="Password"
          type="password"
          placeholder="Minimum 8 characters"
          error={errors.password?.message}
          register={register("password")}
        />

        <Select
          label="Role"
          options={[
            { value: "admin", label: "Admin" },
            { value: "staff", label: "Staff" },
          ]}
          placeholder="Select role"
          error={errors.role?.message}
          register={register("role")}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={createMutation.isPending}>
            Create User
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// --- Edit User Form ---

interface EditUserFormProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
}

export function EditUserForm({ isOpen, onClose, user }: EditUserFormProps) {
  const updateMutation = useUpdateUser();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    setError,
  } = useForm<EditUserFormData>({
    resolver: zodResolver(editUserSchema),
  });

  useEffect(() => {
    if (isOpen && user) {
      reset({
        full_name: user.full_name,
        email: user.email,
        role: user.role,
      });
    }
    if (!isOpen) {
      updateMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, user, reset]);

  const onSubmit = (data: EditUserFormData) => {
    if (!user) return;

    updateMutation.mutate(
      { userId: user.id, data },
      {
        onSuccess: () => {
          onClose();
        },
        onError: (error) => {
          setError("root", { message: getErrorMessage(error) });
        },
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit User">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {errors.root && (
          <div className="rounded-lg bg-danger-50 px-4 py-3 text-sm text-danger-700" role="alert">
            {errors.root.message}
          </div>
        )}

        <Input
          label="Full Name"
          placeholder="Enter full name"
          error={errors.full_name?.message}
          register={register("full_name")}
        />

        <Input
          label="Email"
          type="email"
          placeholder="Enter email address"
          error={errors.email?.message}
          register={register("email")}
        />

        <Select
          label="Role"
          options={[
            { value: "admin", label: "Admin" },
            { value: "staff", label: "Staff" },
          ]}
          error={errors.role?.message}
          register={register("role")}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={updateMutation.isPending}>
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// --- Reset Password Form ---

interface ResetPasswordFormProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
}

export function ResetPasswordForm({ isOpen, onClose, user }: ResetPasswordFormProps) {
  const resetMutation = useResetPassword();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    setError,
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  useEffect(() => {
    if (!isOpen) {
      reset();
      resetMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, reset]);

  const onSubmit = (data: ResetPasswordFormData) => {
    if (!user) return;

    resetMutation.mutate(
      { userId: user.id, data },
      {
        onSuccess: () => {
          onClose();
        },
        onError: (error) => {
          setError("root", { message: getErrorMessage(error) });
        },
      }
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Reset Password — ${user?.full_name ?? ""}`}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {errors.root && (
          <div className="rounded-lg bg-danger-50 px-4 py-3 text-sm text-danger-700" role="alert">
            {errors.root.message}
          </div>
        )}

        <Input
          label="New Password"
          type="password"
          placeholder="Minimum 8 characters"
          error={errors.new_password?.message}
          register={register("new_password")}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={resetMutation.isPending}>
            Reset Password
          </Button>
        </div>
      </form>
    </Modal>
  );
}
