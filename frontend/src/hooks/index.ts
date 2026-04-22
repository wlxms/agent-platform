import { useState, useEffect, useCallback, useRef } from 'react';
import type { PaginatedResponse } from '@/types';

// ─── useLoading ────────────────────────────────────────────────────

export function useLoading(initial = false) {
  const [loading, setLoading] = useState(initial);
  const start = useCallback(() => setLoading(true), []);
  const stop = useCallback(() => setLoading(false), []);
  return { loading, start, stop };
}

// ─── usePolling ────────────────────────────────────────────────────

export function usePolling(
  fn: () => Promise<void>,
  interval: number,
  enabled = true,
) {
  const savedFn = useRef(fn);
  savedFn.current = fn;

  useEffect(() => {
    if (!enabled || interval <= 0) return;
    const id = setInterval(() => {
      savedFn.current();
    }, interval);
    return () => clearInterval(id);
  }, [interval, enabled]);
}

// ─── usePagination ─────────────────────────────────────────────────

export function usePagination<T>(
  fetchFn: (params: {
    page: number;
    page_size: number;
  }) => Promise<PaginatedResponse<T>>,
) {
  const [data, setData] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const { loading, start, stop } = useLoading(true);

  const reload = useCallback(async () => {
    start();
    try {
      const res = await fetchFn({ page, page_size: pageSize });
      setData(res.items);
      setTotal(res.total);
    } finally {
      stop();
    }
  }, [fetchFn, page, pageSize, start, stop]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, total, page, pageSize, loading, setPage, setPageSize, reload };
}

// ─── useDebounce ───────────────────────────────────────────────────

export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);

  return debounced;
}
