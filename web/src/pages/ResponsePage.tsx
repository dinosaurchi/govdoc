import { useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';

const INITIAL_SIDEBAR_LIMIT = 15;
const SIDEBAR_PAGE_SIZE = 15;
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import {
  FileCheck,
  Download,
  UserCheck,
  Loader2,
  CheckCircle2,
  Clock,
  Search,
  AlertTriangle,
  Info,
  Link2,
} from 'lucide-react';
import { apiGet, apiPost } from '@/lib/api';
import { useRole } from '@/hooks/use-role';
import { WorkflowDocConnections } from '@/components/WorkflowDocConnections';

type AIAnalysis = {
  stage: string;
  payload_json: Record<string, unknown>;
};

type ResponseListDoc = {
  id: string;
  title: string;
  status: string;
  urgency?: string | null;
  created_at?: string;
};

function formatRelative(iso?: string | null): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function StatusPill({ status, small }: { status: string; small?: boolean }) {
  const map: Record<string, { cls: string; icon: JSX.Element; label: string }> = {
    closed: {
      cls: 'bg-emerald-100 text-emerald-800',
      icon: <CheckCircle2 size={10} />,
      label: 'Dispatched',
    },
    approved: {
      cls: 'bg-emerald-100 text-emerald-800',
      icon: <CheckCircle2 size={10} />,
      label: 'Approved',
    },
    under_review: {
      cls: 'bg-amber-100 text-amber-800',
      icon: <Clock size={10} />,
      label: 'Pending',
    },
  };
  const entry = map[status] ?? {
    cls: 'bg-slate-100 text-slate-700',
    icon: <Clock size={10} />,
    label: status.replace(/_/g, ' '),
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md font-bold uppercase ${entry.cls} ${
        small ? 'text-[9px] px-1.5 py-0.5' : 'text-[10px] px-2 py-0.5'
      }`}
    >
      {entry.icon}
      {entry.label}
    </span>
  );
}

type ResponseDetailDoc = ResponseListDoc & {
  analyses: AIAnalysis[];
};

export default function ResponsePage() {
  const { role } = useRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkDocId = searchParams.get('doc');
  const [documents, setDocuments] = useState<ResponseListDoc[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<ResponseDetailDoc | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [visibleLimit, setVisibleLimit] = useState(INITIAL_SIDEBAR_LIMIT);
  const responseListRef = useRef<HTMLDivElement>(null);

  const fetchResponses = async (opts?: { preserveSelection?: boolean }) => {
    try {
      const data = await apiGet<ResponseListDoc[]>('/documents/', role);
      const respDocs = data.filter((d) =>
        ['approved', 'closed', 'under_review'].includes(d.status)
      );
      setDocuments(respDocs);
      setSelectedDocId((prev) => {
        if (deepLinkDocId && respDocs.some((doc) => doc.id === deepLinkDocId)) {
          return deepLinkDocId;
        }
        if (opts?.preserveSelection && prev && respDocs.some((doc) => doc.id === prev)) {
          return prev;
        }
        if (prev && respDocs.some((doc) => doc.id === prev)) return prev;
        return respDocs[0]?.id ?? null;
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    (async () => {
      setLoadingList(true);
      await fetchResponses({ preserveSelection: true });
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role]);

  useEffect(() => {
    if (!deepLinkDocId) return;
    if (!documents.some((d) => d.id === deepLinkDocId)) return;
    setSelectedDocId((prev) => (prev === deepLinkDocId ? prev : deepLinkDocId));
  }, [deepLinkDocId, documents]);

  /** Keep ?doc= aligned with selection so every row has a stable, shareable URL. */
  useEffect(() => {
    if (loadingList || !selectedDocId) return;
    if (searchParams.get('doc') === selectedDocId) return;
    const next = new URLSearchParams(searchParams);
    next.set('doc', selectedDocId);
    setSearchParams(next, { replace: true });
  }, [loadingList, selectedDocId, searchParams, setSearchParams]);

  const handleSelectDocId = (id: string) => {
    setSelectedDocId(id);
    const next = new URLSearchParams(searchParams);
    next.set('doc', id);
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    if (!deepLinkDocId || !selectedDocId || selectedDocId !== deepLinkDocId || loadingList) return;
    const root = responseListRef.current;
    if (!root) return;
    const card = root.querySelector<HTMLElement>(`[data-doc-id="${CSS.escape(selectedDocId)}"]`);
    card?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [deepLinkDocId, selectedDocId, loadingList]);

  useEffect(() => {
    let active = true;
    if (!selectedDocId) {
      setSelectedDoc(null);
      return () => { active = false; };
    }

    setLoadingDetail(true);
    (async () => {
      try {
        const data = await apiGet<ResponseDetailDoc>(`/documents/${selectedDocId}`, role);
        if (active) setSelectedDoc(data);
      } catch (err) {
        console.error(err);
        if (active) setSelectedDoc(null);
      } finally {
        if (active) setLoadingDetail(false);
      }
    })();

    return () => { active = false; };
  }, [role, selectedDocId]);

  const handleApprove = async () => {
    if (!selectedDoc) return;
    setActionLoading(true);
    try {
      // Formal approval and archival are separate API steps; this button
      // chains them so supervisors still get a one-click "Approve & Close"
      // from the response queue.
      if (selectedDoc.status !== 'approved' && selectedDoc.status !== 'closed') {
        await apiPost(`/documents/${selectedDoc.id}/approve`, undefined, role);
      }
      if (selectedDoc.status !== 'closed') {
        await apiPost(`/documents/${selectedDoc.id}/close`, undefined, role);
      }
      await fetchResponses({ preserveSelection: true });
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const { pendingDocs, dispatchedDocs } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = (d: ResponseListDoc) =>
      !q || d.title.toLowerCase().includes(q) || d.id.toLowerCase().includes(q);
    const filtered = documents.filter(match);
    const pending = filtered.filter((d) => d.status !== 'closed');
    const dispatched = filtered.filter((d) => d.status === 'closed');
    const byRecency = (a: ResponseListDoc, b: ResponseListDoc) =>
      new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime();
    return { pendingDocs: pending.sort(byRecency), dispatchedDocs: dispatched.sort(byRecency) };
  }, [documents, query]);

  // Reset sidebar window when the filter/role changes.
  useEffect(() => {
    setVisibleLimit(INITIAL_SIDEBAR_LIMIT);
  }, [query, role]);

  const totalSidebar = pendingDocs.length + dispatchedDocs.length;
  const loadMoreRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = loadMoreRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisibleLimit((prev) =>
              Math.min(prev + SIDEBAR_PAGE_SIZE, totalSidebar),
            );
          }
        }
      },
      { rootMargin: '100px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [totalSidebar]);

  const getSummaryFromAnalyses = (doc: ResponseDetailDoc): string => {
    const summary = doc.analyses.find((a) => a.stage === 'summarize');
    if (summary?.payload_json?.summary_points) {
      return (summary.payload_json.summary_points as string[]).join('. ');
    }
    if (summary?.payload_json?.key_subject) {
      return summary.payload_json.key_subject as string;
    }
    return 'Document has been processed and analyzed by the AI pipeline.';
  };

  if (loadingList) return <div className="h-96 flex items-center justify-center"><Loader2 className="animate-spin text-blue-600" size={48} /></div>;

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] min-h-[520px]">
      <div className="flex items-center justify-between flex-shrink-0 pb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Response &amp; Closeout</h1>
          <p className="text-slate-500">Finalize and dispatch official administrative responses.</p>
        </div>
      </div>

      <div
        className="rounded-xl border border-emerald-100 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-950 mb-4 shrink-0 max-w-4xl"
        role="region"
        aria-label="How this queue works"
        data-testid="response-page-explainer"
      >
        <p className="font-bold text-emerald-900 mb-2 flex items-center gap-2">
          <Info size={16} className="shrink-0" /> How you get a result here
        </p>
        <ul className="text-xs text-emerald-900/90 space-y-1.5 list-disc pl-4 leading-relaxed">
          <li>
            <strong>Pending</strong> lists documents that are <strong>under review</strong> or{' '}
            <strong>approved</strong> but not yet archived. As a <strong>Supervisor</strong>, open one
            and click <strong>Approve &amp; Close</strong> (or approve + close from the document page — same
            outcome).
          </li>
          <li>
            <strong>After Close</strong>, the case moves from Pending to <strong>Dispatched</strong> in the
            left sidebar. The success banner on the document page includes a link that opens{' '}
            <strong>this page with that case selected</strong> (same for approve). Or scroll to{' '}
            <strong>Dispatched</strong> and pick the row manually.
          </li>
          <li>
            Nothing here yet? Only documents that have reached <strong>under review</strong> (or later)
            appear. Roles that cannot list documents will see an empty queue.
          </li>
        </ul>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* ----------------------------------------------------- Sidebar */}
        <aside
          className="lg:col-span-1 flex flex-col gap-3 min-h-0"
          data-testid="response-sidebar"
        >
          <div className="relative flex-shrink-0">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search responses…"
              className="w-full bg-white border border-slate-200 rounded-xl pl-8 pr-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
              data-testid="response-search"
            />
          </div>
          <div
            ref={responseListRef}
            className="flex-1 overflow-y-auto min-h-0 pr-1 space-y-4"
            data-testid="response-list"
          >
            {documents.length === 0 ? (
              <div className="p-8 text-center bg-white border border-dashed rounded-2xl text-slate-500 space-y-2">
                <FileCheck className="mx-auto mb-2 text-slate-300" size={28} />
                <p className="text-xs font-bold text-slate-700">No documents in this queue</p>
                <p className="text-[11px] leading-relaxed max-w-xs mx-auto">
                  Items appear when status is <strong>under review</strong>, <strong>approved</strong>, or{' '}
                  <strong>closed</strong>. Earlier pipeline stages stay on Intake / Review only.
                </p>
              </div>
            ) : (
              <>
                <ResponseGroup
                  label="Pending"
                  tone="amber"
                  selectedId={selectedDocId}
                  onSelect={handleSelectDocId}
                  documents={pendingDocs}
                  visibleLimit={visibleLimit}
                  emptyHint={query ? 'No pending responses match.' : 'All caught up — nothing pending.'}
                />
                {dispatchedDocs.length > 0 && (
                  <ResponseGroup
                    label="Dispatched"
                    tone="emerald"
                    selectedId={selectedDocId}
                    onSelect={handleSelectDocId}
                    documents={dispatchedDocs}
                    visibleLimit={Math.max(0, visibleLimit - pendingDocs.length)}
                  />
                )}
                {totalSidebar > visibleLimit && (
                  <div
                    ref={loadMoreRef}
                    className="py-2 text-center"
                    data-testid="response-load-sentinel"
                  >
                    <span className="text-[10px] text-slate-400 inline-flex items-center gap-1">
                      <Loader2 className="animate-spin" size={10} /> Loading more…
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </aside>

        {selectedDoc ? (
          <Card className="lg:col-span-2 flex flex-col min-h-0 overflow-hidden">
            <CardHeader className="border-b border-slate-100 flex flex-row items-start justify-between flex-shrink-0 gap-3">
              <div className="min-w-0 flex-1 space-y-2 pr-2">
                <CardTitle className="text-lg leading-snug">
                  Review Official Response: {selectedDoc.title}
                </CardTitle>
                <WorkflowDocConnections docId={selectedDoc.id} current="response" />
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Badge variant="outline" className="font-mono">{selectedDoc.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-8 space-y-6 flex-1 overflow-y-auto min-h-0">
              {loadingDetail ? (
                <div className="min-h-[400px] flex items-center justify-center">
                  <Loader2 className="animate-spin text-blue-600" size={32} />
                </div>
              ) : (
                <div className="space-y-4 bg-white p-8 rounded-xl border border-slate-200 shadow-inner min-h-[400px] font-serif relative">
                  {selectedDoc.status === 'closed' && (
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[-25deg] opacity-10 pointer-events-none">
                      <div className="border-8 border-emerald-600 rounded-full p-4 flex flex-col items-center justify-center">
                        <CheckCircle2 size={80} className="text-emerald-600" />
                        <span className="text-4xl font-black text-emerald-600 uppercase">CLOSED</span>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-start border-b border-slate-200 pb-4 mb-8">
                    <div className="text-[10px] font-bold space-y-1 text-slate-900">
                      <p>GOVDOC SECUREFLOW</p>
                      <p className="border-t border-slate-900 pt-1">DOCUMENT PROCESSING</p>
                    </div>
                    <div className="text-right text-[10px] text-slate-900">
                      <p className="font-bold">OFFICIAL RESPONSE DRAFT</p>
                      <p className="font-bold border-t border-slate-900 pt-1">Auto-generated</p>
                    </div>
                  </div>

                  <div className="text-center space-y-2 py-4">
                    <h2 className="text-lg font-bold uppercase">Response Document</h2>
                    <p className="text-xs italic">Re: {selectedDoc.title}</p>
                  </div>

                  <div className="text-sm space-y-4 text-slate-800 leading-relaxed">
                    <p>Regarding document {selectedDoc.id.slice(0, 8)}:</p>
                    <p>
                      {getSummaryFromAnalyses(selectedDoc)}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4">
                {selectedDoc.status !== 'closed' && role === 'Supervisor' && (
                  <button
                    disabled={actionLoading}
                    onClick={handleApprove}
                    className="px-8 py-3 bg-emerald-600 text-white rounded-xl font-bold hover:bg-emerald-700 transition flex items-center gap-2 shadow-lg shadow-emerald-100 disabled:opacity-50"
                  >
                    {actionLoading ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}
                    Approve &amp; Close
                  </button>
                )}
                {selectedDoc.status === 'closed' && (
                  <button className="px-8 py-3 bg-slate-100 text-slate-900 rounded-xl font-bold hover:bg-slate-200 transition flex items-center gap-2">
                    <Download size={18} /> Download Archive
                  </button>
                )}
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="lg:col-span-2 min-h-0 bg-slate-50 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-slate-400 space-y-4">
            <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center shadow-sm">
              <FileCheck size={32} />
            </div>
            <p className="font-bold">Select a response draft to review</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar helpers
// ---------------------------------------------------------------------------

function ResponseGroup({
  label,
  tone,
  documents,
  selectedId,
  onSelect,
  emptyHint,
  visibleLimit = Infinity,
}: {
  label: string;
  tone: 'amber' | 'emerald';
  documents: ResponseListDoc[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  emptyHint?: string;
  visibleLimit?: number;
}) {
  const toneClass =
    tone === 'amber' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800';
  const visible = documents.slice(0, Math.max(0, visibleLimit));
  const hidden = documents.length - visible.length;
  return (
    <section className="space-y-2" data-testid={`response-group-${label.toLowerCase()}`}>
      <header className="flex items-center justify-between px-1">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-500">
          {label}
        </h3>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${toneClass}`}>
          {documents.length}
        </span>
      </header>
      {documents.length === 0 ? (
        emptyHint ? <p className="text-[11px] text-slate-400 px-1">{emptyHint}</p> : null
      ) : (
        <div className="space-y-2">
          {visible.map((doc) => (
            <ResponseCard
              key={doc.id}
              doc={doc}
              active={selectedId === doc.id}
              onSelect={onSelect}
            />
          ))}
          {hidden > 0 && (
            <p className="text-[10px] text-slate-400 px-1">
              {hidden} more not shown
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function responseDocHref(docId: string): string {
  return `/response?doc=${encodeURIComponent(docId)}`;
}

function ResponseCard({
  doc,
  active,
  onSelect,
}: {
  doc: ResponseListDoc;
  active: boolean;
  onSelect: (id: string) => void;
}) {
  const hardlink = responseDocHref(doc.id);

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(doc.id);
        }
      }}
      onClick={() => onSelect(doc.id)}
      className={`cursor-pointer rounded-xl border transition-all outline-none focus:ring-2 focus:ring-emerald-400 ${
        active
          ? 'border-emerald-500 bg-emerald-50/40 shadow-sm'
          : 'border-slate-200 bg-white hover:border-emerald-200 hover:bg-slate-50'
      }`}
      data-testid="response-card"
      data-doc-id={doc.id}
      data-active={active ? 'true' : 'false'}
    >
      <div className="p-3 space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <StatusPill status={doc.status} small />
          <div className="flex items-center gap-1.5 shrink-0">
            {doc.created_at && (
              <span className="text-[10px] text-slate-400 whitespace-nowrap">
                {formatRelative(doc.created_at)}
              </span>
            )}
            <RouterLink
              to={hardlink}
              title="Open shareable link for this case (copy from address bar)"
              aria-label="Hard link to this response"
              data-testid="response-card-hardlink"
              onClick={(e) => e.stopPropagation()}
              className="p-1 rounded-md text-slate-400 hover:text-emerald-700 hover:bg-emerald-50 transition-colors"
            >
              <Link2 size={14} />
            </RouterLink>
          </div>
        </div>
        <h4
          className="text-sm font-bold text-slate-900 leading-tight line-clamp-2"
          title={doc.title}
        >
          {doc.title}
        </h4>
        <div className="flex items-center gap-3 text-[10px] text-slate-400 pt-0.5">
          <span className="inline-flex items-center gap-1">
            <UserCheck size={10} />
            {doc.status === 'closed' ? 'Dispatched' : 'Awaiting approval'}
          </span>
          {doc.urgency && doc.urgency !== 'normal' && (
            <span className="inline-flex items-center gap-1 text-orange-700 font-bold uppercase">
              <AlertTriangle size={10} /> {doc.urgency}
            </span>
          )}
        </div>
      </div>
      <div
        className="px-2 pb-2 pt-1 border-t border-slate-100"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <WorkflowDocConnections
          docId={doc.id}
          current="response"
          dense
          onLinkClick={(e) => e.stopPropagation()}
        />
      </div>
    </div>
  );
}
