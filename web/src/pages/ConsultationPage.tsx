import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const INITIAL_SIDEBAR_LIMIT = 15;
const SIDEBAR_PAGE_SIZE = 15;
import { Card } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import {
  Send,
  MessageCircle,
  Loader2,
  Info,
  Lock,
  CheckCircle2,
  Clock,
  Search,
  AlertTriangle,
} from 'lucide-react';
import { apiGet, apiPost } from '@/lib/api';
import { useRole, type Role } from '@/hooks/use-role';

type ConsultationNote = {
  id: string;
  author_role: string;
  body: string;
  created_at: string;
  target_role?: string | null;
  resolved_at?: string | null;
};

type ConsultDoc = {
  id: string;
  title: string;
  status: string;
  urgency?: string | null;
  doc_number?: string | null;
  created_at?: string;
  consultation_notes: ConsultationNote[];
};

// ---------------------------------------------------------------------------
// Role helpers
// ---------------------------------------------------------------------------

const ROLE_ID_BY_LABEL: Record<Role, string> = {
  'Intake Clerk': 'intake_clerk',
  'Department Reviewer': 'reviewer',
  Consultant: 'consultant',
  Supervisor: 'supervisor',
};

const ROLE_LABEL_BY_ID: Record<string, string> = {
  intake_clerk: 'Intake Clerk',
  reviewer: 'Reviewer',
  consultant: 'Consultant',
  supervisor: 'Supervisor',
  system: 'System',
};

const ROLE_TONE: Record<string, string> = {
  reviewer: 'bg-blue-100 text-blue-800',
  supervisor: 'bg-purple-100 text-purple-800',
  consultant: 'bg-amber-100 text-amber-800',
  intake_clerk: 'bg-slate-100 text-slate-700',
  system: 'bg-slate-100 text-slate-500',
};

function canReply(role: Role): boolean {
  return role === 'Department Reviewer' || role === 'Consultant' || role === 'Supervisor';
}

/** A reviewer/supervisor message on a `routed` / `under_review` doc must go
 *  through `request-consultation` so the status transitions correctly.
 *  Consultants (and anyone replying on an already-active thread) can use
 *  the simpler `/consultation/{id}/notes` endpoint. */
function chooseReplyEndpoint(doc: ConsultDoc, role: Role): 'request' | 'note' {
  if (doc.status === 'in_consultation') return 'note';
  if (role === 'Consultant') return 'note';
  return 'request';
}

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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ConsultationPage() {
  const { role } = useRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkDocId = searchParams.get('doc');
  const [documents, setDocuments] = useState<ConsultDoc[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(deepLinkDocId);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [visibleLimit, setVisibleLimit] = useState(INITIAL_SIDEBAR_LIMIT);
  const [resolvingNoteId, setResolvingNoteId] = useState<string | null>(null);

  const currentRoleId = ROLE_ID_BY_LABEL[role];
  const canSend = canReply(role);

  const handleSelectId = (id: string) => {
    setSelectedId(id);
    // Drop any ?doc=<id> deep-link once the user picks a different thread.
    if (searchParams.get('doc') && searchParams.get('doc') !== id) {
      const next = new URLSearchParams(searchParams);
      next.delete('doc');
      setSearchParams(next, { replace: true });
    }
  };

  const fetchConsultations = async (opts?: { preserveSelection?: boolean }) => {
    try {
      const data = await apiGet<ConsultDoc[]>('/documents/', role);
      const consultDocs = data.filter(
        (d) => d.status.includes('consultation') || d.consultation_notes.length > 0,
      );
      setDocuments(consultDocs);
      setSelectedId((prev) => {
        if (opts?.preserveSelection && prev && consultDocs.some((d) => d.id === prev)) {
          return prev;
        }
        // Honor a ?doc=<id> deep link on first successful load (e.g. from
        // the document-detail orphaned-notes warning banner).
        if (deepLinkDocId && consultDocs.some((d) => d.id === deepLinkDocId)) {
          return deepLinkDocId;
        }
        return prev ?? consultDocs[0]?.id ?? null;
      });
      return consultDocs;
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Failed to load consultations');
      return [];
    }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      await fetchConsultations({ preserveSelection: true });
      if (active) setLoading(false);
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role]);

  const selectedDoc = useMemo(
    () => documents.find((d) => d.id === selectedId) ?? null,
    [documents, selectedId],
  );

  const sortedNotes = useMemo(() => {
    if (!selectedDoc) return [] as ConsultationNote[];
    return [...selectedDoc.consultation_notes].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [selectedDoc]);

  // Split sidebar threads into active (needs attention) and resolved/closed.
  const { activeThreads, resolvedThreads } = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const match = (d: ConsultDoc) => {
      if (!normalizedQuery) return true;
      return (
        d.title.toLowerCase().includes(normalizedQuery) ||
        d.id.toLowerCase().includes(normalizedQuery) ||
        (d.doc_number ?? '').toLowerCase().includes(normalizedQuery)
      );
    };
    const filtered = documents.filter(match);
    const active = filtered.filter((d) => d.status === 'in_consultation');
    const resolved = filtered.filter((d) => d.status !== 'in_consultation');
    // Most recently-updated first (last note timestamp or created_at)
    const byRecency = (a: ConsultDoc, b: ConsultDoc) => {
      const ta =
        a.consultation_notes.at(-1)?.created_at ??
        a.created_at ??
        '';
      const tb =
        b.consultation_notes.at(-1)?.created_at ??
        b.created_at ??
        '';
      return new Date(tb).getTime() - new Date(ta).getTime();
    };
    return {
      activeThreads: active.sort(byRecency),
      resolvedThreads: resolved.sort(byRecency),
    };
  }, [documents, query]);

  const handleResolveNote = async (note: ConsultationNote) => {
    if (!selectedDoc || note.resolved_at) return;
    setResolvingNoteId(note.id);
    setError(null);
    try {
      await apiPost(
        `/documents/${selectedDoc.id}/resolve-consultation/${note.id}`,
        undefined,
        role,
      );
      await fetchConsultations({ preserveSelection: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to resolve note');
    } finally {
      setResolvingNoteId(null);
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim() || !selectedDoc || !canSend) return;
    setSending(true);
    setError(null);
    try {
      const endpoint = chooseReplyEndpoint(selectedDoc, role);
      if (endpoint === 'request') {
        await apiPost(
          `/documents/${selectedDoc.id}/request-consultation`,
          { target_role: 'consultant', body: message },
          role,
        );
      } else {
        await apiPost(
          `/consultation/${selectedDoc.id}/notes`,
          { content: message },
          role,
        );
      }
      setMessage('');
      await fetchConsultations({ preserveSelection: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  // Auto-scroll the chat to the bottom when the notes change or the thread
  // switches — this is standard chat UX and avoids the "new message is hidden
  // behind the composer" problem.
  const scrollRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [sortedNotes, selectedId]);

  // Reset visible window when the filter/role changes so we always start at the
  // top of the freshly-filtered list.
  useEffect(() => {
    setVisibleLimit(INITIAL_SIDEBAR_LIMIT);
  }, [query, role]);

  // IntersectionObserver for lazy-loading more sidebar cards.
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const totalThreads = activeThreads.length + resolvedThreads.length;
  useEffect(() => {
    const el = loadMoreRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisibleLimit((prev) =>
              Math.min(prev + SIDEBAR_PAGE_SIZE, totalThreads),
            );
          }
        }
      },
      { rootMargin: '100px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [totalThreads]);

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Loader2 className="animate-spin text-blue-600" size={48} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] min-h-[520px]">
      <div className="flex items-center justify-between flex-shrink-0 pb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Internal Consultation</h1>
          <p className="text-slate-500">Cross-departmental collaboration on complex cases.</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* ----------------------------------------------------- Sidebar */}
        <aside
          className="lg:col-span-1 flex flex-col gap-3 min-h-0"
          data-testid="consultation-sidebar"
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
              placeholder="Search threads…"
              className="w-full bg-white border border-slate-200 rounded-xl pl-8 pr-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              data-testid="consultation-search"
            />
          </div>

          <div
            className="flex-1 overflow-y-auto min-h-0 pr-1 space-y-4"
            data-testid="consultation-list"
          >
            {documents.length === 0 ? (
              <div className="p-8 text-center bg-white border border-dashed rounded-2xl text-slate-400">
                <MessageCircle className="mx-auto mb-2 text-slate-300" size={28} />
                <p className="text-xs font-medium">No documents currently in consultation.</p>
              </div>
            ) : (
              <>
                <ThreadGroup
                  label="Active"
                  count={activeThreads.length}
                  tone="blue"
                  documents={activeThreads}
                  selectedId={selectedId}
                  onSelect={handleSelectId}
                  visibleLimit={visibleLimit}
                  emptyHint={query ? 'No active threads match.' : 'No active consultations.'}
                />
                {resolvedThreads.length > 0 && (
                  <ThreadGroup
                    label="Resolved"
                    count={resolvedThreads.length}
                    tone="slate"
                    documents={resolvedThreads}
                    selectedId={selectedId}
                    onSelect={handleSelectId}
                    visibleLimit={
                      Math.max(0, visibleLimit - activeThreads.length)
                    }
                  />
                )}
                {(activeThreads.length + resolvedThreads.length) > visibleLimit && (
                  <div ref={loadMoreRef} className="py-2 text-center" data-testid="consultation-load-sentinel">
                    <span className="text-[10px] text-slate-400 inline-flex items-center gap-1">
                      <Loader2 className="animate-spin" size={10} /> Loading more…
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </aside>

        {/* ----------------------------------------------------- Thread */}
        {selectedDoc ? (
          <Card
            className="lg:col-span-2 flex flex-col min-h-0 overflow-hidden"
            data-testid="consultation-thread"
          >
            <div className="px-5 py-4 border-b border-slate-100 bg-white">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-bold text-slate-900 truncate">
                    {selectedDoc.title}
                  </h2>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
                    <StatusPill status={selectedDoc.status} />
                    {selectedDoc.urgency && selectedDoc.urgency !== 'normal' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-orange-100 text-orange-800 font-bold uppercase">
                        <AlertTriangle size={10} />
                        {selectedDoc.urgency}
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-bold">
                      <MessageCircle size={10} /> {selectedDoc.consultation_notes.length} notes
                    </span>
                  </div>
                </div>
                <span className="text-[10px] text-slate-400 font-mono shrink-0 mt-1">
                  #{selectedDoc.id.slice(0, 8)}
                </span>
              </div>
            </div>

            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/50"
              data-testid="consultation-scroll"
            >
              {sortedNotes.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
                  <Info size={24} />
                  <p className="text-sm font-medium">No notes yet. Be the first to comment.</p>
                </div>
              )}
              {sortedNotes.map((note) => {
                // A note can be resolved by the role that was asked
                // (`target_role`) — but not by the author themselves, and
                // only while the doc is still on `in_consultation`.
                const canResolveThisNote =
                  !note.resolved_at &&
                  !!note.target_role &&
                  note.target_role === currentRoleId &&
                  note.author_role !== currentRoleId &&
                  selectedDoc?.status === 'in_consultation';
                return (
                  <ChatMessage
                    key={note.id}
                    note={note}
                    isOwn={note.author_role === currentRoleId}
                    canResolve={canResolveThisNote}
                    isResolving={resolvingNoteId === note.id}
                    onResolve={() => handleResolveNote(note)}
                  />
                );
              })}
            </div>

            <div className="p-3 border-t border-slate-100 bg-white space-y-2">
              {selectedDoc && (
                <ThreadStatusHint
                  doc={selectedDoc}
                  currentRoleId={currentRoleId}
                />
              )}
              {error && (
                <div
                  className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2"
                  data-testid="consultation-error"
                >
                  {error}
                </div>
              )}
              {canSend ? (
                <div data-testid="consultation-composer">
                  <label className="flex items-end gap-2">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-1 rounded-md shrink-0 ${
                        ROLE_TONE[currentRoleId] ?? 'bg-slate-100 text-slate-600'
                      }`}
                      data-testid="consultation-active-role"
                    >
                      You · {ROLE_LABEL_BY_ID[currentRoleId] ?? role}
                    </span>
                    <textarea
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          if (!sending) handleSendMessage();
                        }
                      }}
                      rows={1}
                      placeholder="Type your consultation note…  (Enter to send · Shift+Enter for newline)"
                      className="flex-1 bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none max-h-32 min-h-[2.5rem]"
                      data-testid="consultation-input"
                    />
                    <button
                      type="button"
                      disabled={sending || !message.trim()}
                      onClick={handleSendMessage}
                      className="p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-50 shrink-0"
                      data-testid="consultation-send"
                      aria-label="Send message"
                    >
                      {sending ? (
                        <Loader2 className="animate-spin" size={18} />
                      ) : (
                        <Send size={18} />
                      )}
                    </button>
                  </label>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">
                  <Lock size={14} />
                  <span>
                    Your current role ({role}) can view this thread but cannot reply. Switch to
                    Reviewer, Consultant, or Supervisor to participate.
                  </span>
                </div>
              )}
            </div>
          </Card>
        ) : (
          <div className="lg:col-span-2 min-h-0 bg-slate-50 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-slate-400 space-y-4">
            <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center shadow-sm">
              <MessageCircle size={32} />
            </div>
            <p className="font-bold">Select a thread to start collaborating</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function ThreadGroup({
  label,
  count,
  tone,
  documents,
  selectedId,
  onSelect,
  emptyHint,
  visibleLimit = Infinity,
}: {
  label: string;
  count: number;
  tone: 'blue' | 'slate';
  documents: ConsultDoc[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  emptyHint?: string;
  visibleLimit?: number;
}) {
  const toneClass =
    tone === 'blue'
      ? 'bg-blue-100 text-blue-800'
      : 'bg-slate-200 text-slate-700';
  const visible = documents.slice(0, Math.max(0, visibleLimit));
  const hidden = documents.length - visible.length;
  return (
    <section className="space-y-2" data-testid={`consultation-group-${label.toLowerCase()}`}>
      <header className="flex items-center justify-between px-1">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-500">
          {label}
        </h3>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${toneClass}`}>
          {count}
        </span>
      </header>
      {documents.length === 0 ? (
        emptyHint ? (
          <p className="text-[11px] text-slate-400 px-1">{emptyHint}</p>
        ) : null
      ) : (
        <div className="space-y-2">
          {visible.map((doc) => (
            <ThreadCard
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

function ThreadCard({
  doc,
  active,
  onSelect,
}: {
  doc: ConsultDoc;
  active: boolean;
  onSelect: (id: string) => void;
}) {
  const lastNote =
    [...doc.consultation_notes].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )[0] ?? null;
  const snippet = (lastNote?.body ?? '').trim().replace(/\s+/g, ' ').slice(0, 90);
  const lastAuthor = lastNote
    ? ROLE_LABEL_BY_ID[lastNote.author_role] ?? lastNote.author_role
    : null;
  const updatedAt = lastNote?.created_at ?? doc.created_at;

  return (
    <div
      key={doc.id}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(doc.id);
        }
      }}
      onClick={() => onSelect(doc.id)}
      className={`cursor-pointer rounded-xl border transition-all outline-none focus:ring-2 focus:ring-blue-400 ${
        active
          ? 'border-blue-500 bg-blue-50/40 shadow-sm'
          : 'border-slate-200 bg-white hover:border-blue-200 hover:bg-slate-50'
      }`}
      data-testid="consultation-thread-card"
      data-doc-id={doc.id}
      data-active={active ? 'true' : 'false'}
    >
      <div className="p-3 space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <StatusPill status={doc.status} small />
          <span className="text-[10px] text-slate-400 whitespace-nowrap">
            {formatRelative(updatedAt)}
          </span>
        </div>
        <h4
          className="text-sm font-bold text-slate-900 leading-tight line-clamp-1"
          title={doc.title}
        >
          {doc.title}
        </h4>
        {snippet ? (
          <p className="text-xs text-slate-500 leading-snug line-clamp-2">
            {lastAuthor && <span className="font-semibold text-slate-700">{lastAuthor}: </span>}
            {snippet}
            {lastNote && (lastNote.body.length ?? 0) > snippet.length ? '…' : ''}
          </p>
        ) : (
          <p className="text-xs text-slate-400 italic">No messages yet.</p>
        )}
        <div className="flex items-center gap-3 text-[10px] text-slate-400 pt-0.5">
          <span className="inline-flex items-center gap-1">
            <MessageCircle size={10} /> {doc.consultation_notes.length}
          </span>
          {doc.urgency && doc.urgency !== 'normal' && (
            <span className="inline-flex items-center gap-1 text-orange-700 font-bold uppercase">
              <AlertTriangle size={10} /> {doc.urgency}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status, small }: { status: string; small?: boolean }) {
  const map: Record<string, { cls: string; icon: JSX.Element; label: string }> = {
    in_consultation: {
      cls: 'bg-amber-100 text-amber-800',
      icon: <Clock size={10} />,
      label: 'In consultation',
    },
    closed: {
      cls: 'bg-emerald-100 text-emerald-800',
      icon: <CheckCircle2 size={10} />,
      label: 'Closed',
    },
    approved: {
      cls: 'bg-emerald-100 text-emerald-800',
      icon: <CheckCircle2 size={10} />,
      label: 'Approved',
    },
    under_review: {
      cls: 'bg-blue-100 text-blue-800',
      icon: <Clock size={10} />,
      label: 'Under review',
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

// ---------------------------------------------------------------------------
// Chat bubble
// ---------------------------------------------------------------------------

function ThreadStatusHint({
  doc,
  currentRoleId,
}: {
  doc: ConsultDoc;
  currentRoleId: string;
}) {
  const openNotes = doc.consultation_notes.filter((n) => !n.resolved_at);
  const openForMe = openNotes.filter(
    (n) => n.target_role && n.target_role === currentRoleId && n.author_role !== currentRoleId,
  );
  const docHref = `/documents/${doc.id}`;

  if (doc.status === 'in_consultation') {
    if (openForMe.length > 0) {
      return (
        <div
          data-testid="consultation-thread-hint"
          data-tone="action"
          className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
        >
          {openForMe.length} note{openForMe.length === 1 ? '' : 's'} waiting for your reply.{' '}
          Mark resolved once you&rsquo;re done — the reviewer will pick up from there.
        </div>
      );
    }
    if (openNotes.length > 0) {
      return (
        <div
          data-testid="consultation-thread-hint"
          data-tone="waiting"
          className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
        >
          Waiting on {openNotes.length} open note{openNotes.length === 1 ? '' : 's'} from{' '}
          other role(s). Status will flip to Under Review once everyone resolves.
        </div>
      );
    }
    // `in_consultation` with zero open notes shouldn't normally happen
    // after the backend fix; surface defensively so it's debuggable.
    return (
      <div
        data-testid="consultation-thread-hint"
        data-tone="defensive"
        className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
      >
        All notes resolved. Waiting for reviewer to pick up the document.
      </div>
    );
  }

  // Thread is no longer `in_consultation` (under_review, approved, closed,
  // etc). If orphaned open notes remain, let the target role still resolve
  // them in-place (handled by the Resolve button on the bubble) and nudge
  // other roles to the document page for next-step decisions.
  if (openNotes.length > 0 && openForMe.length > 0) {
    return (
      <div
        data-testid="consultation-thread-hint"
        data-tone="orphaned"
        className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
      >
        Document is <strong>{doc.status.replace(/_/g, ' ')}</strong>. You still have{' '}
        {openForMe.length} open note{openForMe.length === 1 ? '' : 's'} — resolve{' '}
        {openForMe.length === 1 ? 'it' : 'them'} to keep the record clean.
      </div>
    );
  }

  return (
    <div
      data-testid="consultation-thread-hint"
      data-tone="closed"
      className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2"
    >
      This thread is <strong>{doc.status.replace(/_/g, ' ')}</strong>.{' '}
      <a href={docHref} className="font-semibold text-blue-600 hover:underline">
        Open the document page
      </a>{' '}
      for approve / reroute / close actions.
    </div>
  );
}

function ChatMessage({
  note,
  isOwn,
  canResolve,
  isResolving,
  onResolve,
}: {
  note: ConsultationNote;
  isOwn: boolean;
  canResolve: boolean;
  isResolving: boolean;
  onResolve: () => void;
}) {
  const label = ROLE_LABEL_BY_ID[note.author_role] ?? note.author_role;
  const time = new Date(note.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
  const tone = ROLE_TONE[note.author_role] ?? 'bg-slate-100 text-slate-700';

  return (
    <div
      className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
      data-testid="consultation-message"
      data-author-role={note.author_role}
      data-own={isOwn ? 'true' : 'false'}
    >
      <div
        className={`flex flex-col ${
          isOwn ? 'items-end' : 'items-start'
        } max-w-[75%] min-w-0 space-y-1`}
      >
        <div className="flex items-center gap-2 px-2">
          {!isOwn && (
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md ${tone}`}>
              {label}
            </span>
          )}
          <span className="text-[10px] text-slate-400">{time}</span>
          {note.resolved_at && (
            <Badge variant="secondary" className="text-[9px]">
              Resolved
            </Badge>
          )}
          {isOwn && (
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md ${tone}`}>
              You
            </span>
          )}
        </div>
        <div
          className={`px-4 py-2 rounded-2xl text-sm shadow-sm whitespace-pre-wrap break-words leading-relaxed ${
            isOwn
              ? 'bg-blue-600 text-white rounded-tr-none'
              : 'bg-white border border-slate-200 text-slate-900 rounded-tl-none'
          }`}
        >
          {note.body}
        </div>
        {canResolve && (
          <button
            type="button"
            onClick={onResolve}
            disabled={isResolving}
            data-testid="consultation-resolve-note"
            data-note-id={note.id}
            className="inline-flex items-center gap-1 rounded-md border border-emerald-300 bg-emerald-50 px-2 py-1 text-[11px] font-bold uppercase tracking-wide text-emerald-800 hover:bg-emerald-100 disabled:opacity-60 disabled:cursor-wait"
          >
            {isResolving ? (
              <Loader2 className="animate-spin" size={12} />
            ) : (
              <CheckCircle2 size={12} />
            )}
            {isResolving ? 'Resolving…' : 'Mark as resolved'}
          </button>
        )}
      </div>
    </div>
  );
}
