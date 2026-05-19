"use client";

import { forwardRef, type SelectHTMLAttributes } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  label?: string;
  options: SelectOption[];
  error?: string;
  placeholder?: string;
  register?: UseFormRegisterReturn;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { label, options, error, placeholder, register, id, className = "", ...props },
    ref
  ) => {
    const selectId = id || register?.name || label?.toLowerCase().replace(/\s+/g, "-");
    const errorId = error ? `${selectId}-error` : undefined;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="mb-1.5 block text-sm font-medium text-neutral-700"
          >
            {label}
          </label>
        )}
        <select
          ref={register ? undefined : ref}
          id={selectId}
          aria-invalid={!!error}
          aria-describedby={errorId}
          className={`w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50 ${
            error
              ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/20"
              : "border-neutral-300 focus:border-primary-500 focus:ring-primary-500/20"
          } ${className}`}
          {...register}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p id={errorId} className="mt-1.5 text-sm text-danger-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";
