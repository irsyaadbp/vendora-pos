"use client";

import { forwardRef, type InputHTMLAttributes } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  error?: string;
  register?: UseFormRegisterReturn;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, register, id, className = "", ...props }, ref) => {
    const inputId = id || register?.name || label?.toLowerCase().replace(/\s+/g, "-");
    const errorId = error ? `${inputId}-error` : undefined;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="mb-1.5 block text-sm font-medium text-neutral-700"
          >
            {label}
          </label>
        )}
        <input
          ref={register ? undefined : ref}
          id={inputId}
          aria-invalid={!!error}
          aria-describedby={errorId}
          className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50 ${
            error
              ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/20"
              : "border-neutral-300 focus:border-primary-500 focus:ring-primary-500/20"
          } ${className}`}
          {...register}
          {...props}
        />
        {error && (
          <p id={errorId} className="mt-1.5 text-sm text-danger-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
