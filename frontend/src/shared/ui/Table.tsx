"use client";

import { Pagination } from "./Pagination";

export interface TableColumn<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  pagination?: {
    page: number;
    totalPages: number;
  };
  onPageChange?: (page: number) => void;
  emptyMessage?: string;
}

export function Table<T extends Record<string, unknown>>({
  columns,
  data,
  pagination,
  onPageChange,
  emptyMessage = "No data available",
}: TableProps<T>) {
  return (
    <div className="w-full overflow-hidden rounded-lg border border-neutral-200">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" role="table">
          <thead className="border-b border-neutral-200 bg-neutral-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className="px-4 py-3 font-medium text-neutral-600"
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-neutral-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className="hover:bg-neutral-50 transition-colors"
                >
                  {columns.map((column) => (
                    <td key={column.key} className="px-4 py-3 text-neutral-900">
                      {column.render
                        ? column.render(row)
                        : (row[column.key] as React.ReactNode) ?? "—"}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && onPageChange && pagination.totalPages > 1 && (
        <div className="border-t border-neutral-200 px-4 py-3">
          <Pagination
            page={pagination.page}
            totalPages={pagination.totalPages}
            onPageChange={onPageChange}
          />
        </div>
      )}
    </div>
  );
}
