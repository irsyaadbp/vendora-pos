"use client";

import { useState, useCallback, useMemo } from "react";

interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  totalCount?: number;
}

interface UsePaginationReturn {
  page: number;
  pageSize: number;
  totalPages: number;
  goToPage: (page: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  setPageSize: (size: number) => void;
}

export function usePagination(
  options: UsePaginationOptions = {}
): UsePaginationReturn {
  const { initialPage = 1, initialPageSize = 20, totalCount = 0 } = options;

  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(totalCount / pageSize)),
    [totalCount, pageSize]
  );

  const goToPage = useCallback(
    (targetPage: number) => {
      const clamped = Math.min(Math.max(1, targetPage), totalPages);
      setPage(clamped);
    },
    [totalPages]
  );

  const nextPage = useCallback(() => {
    setPage((current) => Math.min(current + 1, totalPages));
  }, [totalPages]);

  const prevPage = useCallback(() => {
    setPage((current) => Math.max(current - 1, 1));
  }, []);

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    setPage(1);
  }, []);

  return {
    page,
    pageSize,
    totalPages,
    goToPage,
    nextPage,
    prevPage,
    setPageSize,
  };
}
