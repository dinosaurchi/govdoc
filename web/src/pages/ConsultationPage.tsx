import { useEffect, useMemo, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { Send, MessageCircle, Loader2, Info, Lock } from 'lucide-react';
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
  consultation_notes: ConsultationNote[];
};

// ---------------------------------------------------------------------------
// Role helpers
// ---------------------------------------------------------------------------

const ROLE_ID_BY_LABEL: Record<Role, string> = {
  'Intake Clerk': 'intake_clerk',
  'Department Reviewer': 'reviewer',
  'Consultant': 'consultant',
  'Supervisor': 'supervisor',
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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ConsultationPage() {
  const { role } = useRole();
  const [documents, setDocuments] = useState<ConsultDoc[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentRoleId = ROLE_ID_BY_LABEL[role];
  const canSend = canReply(role);

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

  // Sort by created_at ascending so newest messages always appear at the bottom.
  const sortedNotes = useMemo(() => {
    if (!selectedDoc) return [] as ConsultationNote[];
    return [...selectedDoc.consultation_notes].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [selectedDoc]);

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

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Loader2 className="animate-spin text-blue-600" size={48} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Internal Consultation</h1>
          <p className="text-slate-500">Cross-departmental collaboration on complex cases.</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <h3 className="font-bold text-sm text-slate-400 uppercase tracking-widest pl-2">Active Requests</h3>
          {documents.length === 0 ? (
            <div className="p-8 text-center bg-white border border-dashed rounded-2xl text-slate-400">
              <p className="text-xs font-medium">No documents currently in consultation.</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div
                key={doc.id}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') setSelectedId(doc.id);
                }}
                onClick={() => setSelectedId(doc.id)}
                className="rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <Card
                  className={`cursor-pointer transition-all ${selectedId === doc.id ? 'border-blue-500 shadow-md ring-2 ring-blue-50' : 'hover:border-blue-200'}`}
                >
                  <CardContent className="p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary" className="scale-75 origin-left">
                        {doc.status.replace(/_/g, ' ')}
                      </Badge>
                    </div>
                    <h4 className="font-bold text-slate-900 leading-tight truncate">{doc.title}</h4>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <MessageCircle size={12} /> {doc.consultation_notes.length} notes
                    </div>
                  </CardContent>
                </Card>
              </div>
            ))
          )}
        </div>

        {selectedDoc ? (
          <Card className="lg:col-span-2 flex flex-col h-[600px]" data-testid="consultation-thread">
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="text-lg flex items-center justify-between gap-4">
                <span className="truncate">Thread: {selectedDoc.title}</span>
                <span className="text-xs text-slate-400 font-mono shrink-0">{selectedDoc.id.slice(0, 8)}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/50">
              {sortedNotes.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
                  <Info size={24} />
                  <p className="text-sm font-medium">No notes yet. Be the first to comment.</p>
                </div>
              )}
              {sortedNotes.map((note) => (
                <ChatMessage
                  key={note.id}
                  note={note}
                  isOwn={note.author_role === currentRoleId}
                />
              ))}
            </CardContent>
            <div className="p-4 border-t border-slate-100 bg-white space-y-2">
              {error && (
                <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}
              {canSend ? (
                <div className="flex items-center gap-2" data-testid="consultation-composer">
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-1 rounded-md ${ROLE_TONE[currentRoleId] ?? 'bg-slate-100 text-slate-600'}`}
                    data-testid="consultation-active-role"
                  >
                    You · {ROLE_LABEL_BY_ID[currentRoleId] ?? role}
                  </span>
                  <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !sending && handleSendMessage()}
                    placeholder="Type your consultation note…"
                    className="flex-1 bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    data-testid="consultation-input"
                  />
                  <button
                    type="button"
                    disabled={sending || !message.trim()}
                    onClick={handleSendMessage}
                    className="p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-50"
                    data-testid="consultation-send"
                    aria-label="Send message"
                  >
                    {sending ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
                  </button>
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
          <div className="lg:col-span-2 h-[600px] bg-slate-50 border-2 border-dashed border-slate-200 rounded-2xl flex flex-col items-center justify-center text-slate-400 space-y-4">
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
// Chat bubble
// ---------------------------------------------------------------------------

function ChatMessage({ note, isOwn }: { note: ConsultationNote; isOwn: boolean }) {
  const label = ROLE_LABEL_BY_ID[note.author_role] ?? note.author_role;
  const time = new Date(note.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const tone = ROLE_TONE[note.author_role] ?? 'bg-slate-100 text-slate-700';

  return (
    <div
      className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
      data-testid="consultation-message"
      data-author-role={note.author_role}
      data-own={isOwn ? 'true' : 'false'}
    >
      <div className={`flex flex-col ${isOwn ? 'items-end' : 'items-start'} max-w-[80%] space-y-1`}>
        <div className="flex items-center gap-2 px-2">
          {!isOwn && (
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md ${tone}`}>{label}</span>
          )}
          <span className="text-[10px] text-slate-400">{time}</span>
          {note.resolved_at && (
            <Badge variant="secondary" className="text-[9px]">Resolved</Badge>
          )}
          {isOwn && (
            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md ${tone}`}>You</span>
          )}
        </div>
        <div
          className={`px-4 py-2 rounded-2xl text-sm shadow-sm ${
            isOwn
              ? 'bg-blue-600 text-white rounded-tr-none'
              : 'bg-white border border-slate-200 text-slate-900 rounded-tl-none'
          }`}
        >
          {note.body}
        </div>
      </div>
    </div>
  );
}
