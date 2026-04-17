import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Card } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { Search, ChevronRight, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiGetPaged } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

type DocListItem = {
  id: string;
  title: string;
  doc_number: string | null;
  status: string;
  security_level: string;
  urgency: string;
  created_at: string;
};

const PAGE_SIZE = 25;

export default function ReviewPage() {
  const { role } = useRole();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocListItem[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loadingFirst, setLoadingFirst] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rawQuery, setRawQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(rawQuery.trim()), 250);
    return () => clearTimeout(t);
  }, [rawQuery]);

  const fetchPage = useCallback(
    async (offset: number, q: string) => {
      const params = new URLSearchParams();
      params.set('offset', String(offset));
      params.set('limit', String(PAGE_SIZE));
      if (q) params.set('q', q);
      return apiGetPaged<DocListItem>(`/documents/?${params.toString()}`, role);
    },
    [role],
  );

  useEffect(() => {
    let active = true;
    setLoadingFirst(true);
    setError(null);
    (async () => {
      try {
        const { items, total } = await fetchPage(0, debouncedQuery);
        if (!active) return;
        setDocuments(items);
        setTotal(total);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load documents');
      } finally {
        if (active) setLoadingFirst(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [fetchPage, debouncedQuery]);

  const hasMore = useMemo(() => {
    if (total == null) return false;
    return documents.length < total;
  }, [documents.length, total]);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const { items, total } = await fetchPage(documents.length, debouncedQuery);
      setDocuments((prev) => [...prev, ...items]);
      setTotal(total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load more');
    } finally {
      setLoadingMore(false);
    }
  }, [debouncedQuery, documents.length, fetchPage, hasMore, loadingMore]);

  // IntersectionObserver sentinel — load next page when it scrolls into view.
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) loadMore();
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Review Queue</h1>
          <p className="text-slate-500">Manage and route incoming administrative documents.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              size={16}
            />
            <input
              type="search"
              value={rawQuery}
              onChange={(e) => setRawQuery(e.target.value)}
              placeholder="Search documents…"
              className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none w-64"
              data-testid="review-search"
            />
          </div>
        </div>
      </div>

      <Card>
        <div className="overflow-x-auto">
          {loadingFirst ? (
            <div className="p-12 flex flex-col items-center justify-center text-slate-400 gap-4">
              <Loader2 className="animate-spin" size={32} />
              <p className="font-medium">Fetching documents from SecureFlow API…</p>
            </div>
          ) : error ? (
            <div className="p-12 text-center text-red-600">
              <p className="font-medium">{error}</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              <p className="font-medium">
                {debouncedQuery
                  ? `No documents match “${debouncedQuery}”.`
                  : 'No documents in queue.'}
              </p>
              {!debouncedQuery && (
                <p className="text-xs">
                  Upload documents via Intake page to populate the review queue.
                </p>
              )}
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold">
                <tr>
                  <th className="px-6 py-4">Title</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Urgency</th>
                  <th className="px-6 py-4">Security</th>
                  <th className="px-6 py-4">Created</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    role="link"
                    tabIndex={0}
                    onClick={() => navigate(`/documents/${doc.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(`/documents/${doc.id}`);
                      }
                    }}
                    className="cursor-pointer hover:bg-blue-50/50 focus:bg-blue-50 focus:outline-none transition-colors group"
                    data-testid="review-row"
                    data-doc-id={doc.id}
                  >
                    <td className="px-6 py-4 font-bold text-slate-900 group-hover:text-blue-800">
                      {doc.title}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="secondary" className="capitalize">
                        {doc.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge
                        className={`capitalize text-[10px] ${
                          doc.urgency === 'critical'
                            ? 'bg-red-600'
                            : doc.urgency === 'urgent'
                              ? 'bg-orange-500'
                              : 'bg-slate-400'
                        }`}
                      >
                        {doc.urgency}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 capitalize">
                      {doc.security_level.replace(/_/g, ' ')}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <ChevronRight
                        size={18}
                        className="inline-block text-slate-300 group-hover:text-blue-600 transition-colors"
                        aria-label="Open document"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {!loadingFirst && documents.length > 0 && (
          <div
            className="border-t border-slate-100 px-6 py-3 flex items-center justify-between text-xs text-slate-500 bg-slate-50/50"
            data-testid="review-pagination-footer"
          >
            <span>
              Showing <span className="font-bold text-slate-700">{documents.length}</span>
              {total != null && (
                <>
                  {' '}of <span className="font-bold text-slate-700">{total}</span>
                </>
              )}{' '}
              documents
            </span>
            {hasMore ? (
              <button
                type="button"
                onClick={loadMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-700 font-medium hover:bg-blue-50 hover:border-blue-200 disabled:opacity-50 transition"
                data-testid="review-load-more"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="animate-spin" size={12} /> Loading…
                  </>
                ) : (
                  <>Load more</>
                )}
              </button>
            ) : (
              <span className="italic">End of queue</span>
            )}
          </div>
        )}

        {/* Sentinel for lazy-load when user scrolls near bottom */}
        <div ref={sentinelRef} aria-hidden="true" />
      </Card>
    </div>
  );
}
