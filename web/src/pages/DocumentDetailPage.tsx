import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import {
  ArrowLeft,
  MessageSquare,
  CheckCircle2,
  Send,
  User,
  Building,
  Loader2,
  BrainCircuit,
  History,
  FileText,
  ScrollText,
  Shield,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchApi } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

type DocDetail = {
  id: number;
  title: string;
  doc_type: string;
  state: string;
  created_at: string;
  files: Array<{
    id: number;
    file_name: string;
    mime_type: string;
    file_size_bytes: number;
    storage_relative_path: string;
    sha256_hex: string | null;
    created_at: string;
  }>;
  artifacts: Array<{
    id: number;
    extraction_method: string;
    extraction_source_label: string;
    extracted_text: string;
    structured_metadata_json: Record<string, unknown> | null;
    created_at: string;
  }>;
  analysis: {
    suggested_type: string;
    urgency_score: number;
    summary: string;
    suggested_department: string;
    analysis_source_label: string;
  } | null;
  decisions: Array<{
    id: number;
    target_department_id: number;
    note: string | null;
    created_at: string;
  }>;
  consultations: Array<{
    id: number;
    author_role_id: number;
    content: string;
    created_at: string;
  }>;
  audit_logs: Array<{
    id: number;
    actor_role_id: number;
    action: string;
    details: Record<string, unknown> | null;
    timestamp: string;
  }>;
};

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  return <DocumentDetailInner key={id} id={id!} />;
}

function DocumentDetailInner({ id }: { id: string }) {
  const { role } = useRole();
  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [routeDept, setRouteDept] = useState(1);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await fetchApi(`/documents/${id}`);
        if (active) {
          setDoc(data);
          setError(null);
        }
      } catch (err: unknown) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load document');
          setDoc(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [id]);

  const fetchDoc = async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) setLoading(true);
    try {
      const data = await fetchApi(`/documents/${id}`);
      setDoc(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
      setDoc(null);
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  };

  const handleAction = async (action: string, payload: Record<string, string> = {}) => {
    setActionLoading(true);
    try {
      if (action === 'route') {
        const note = encodeURIComponent(payload.note || 'Routed via detail page');
        await fetchApi(`/review/${id}/route?target_dept_id=${routeDept}&note=${note}`, {
          method: 'POST',
        });
      } else if (action === 'approve') {
        await fetchApi(`/review/${id}/approve`, { method: 'POST' });
      } else if (action === 'analyze') {
        await fetchApi(`/documents/${id}/analyze`, { method: 'POST' });
      } else if (action === 'start-review') {
        await fetchApi(`/review/${id}/start-review`, { method: 'POST' });
      } else if (action === 'prepare-response') {
        await fetchApi(`/review/${id}/prepare-response`, { method: 'POST' });
      } else if (action === 'request-consultation') {
        await fetchApi(`/consultation/${id}/notes`, {
          method: 'POST',
          body: JSON.stringify({
            content: payload.note || 'Consultation requested from document detail (baseline).',
          }),
        });
      } else if (action === 'complete-consultation') {
        await fetchApi(`/consultation/${id}/complete`, { method: 'POST' });
      }
      await fetchDoc({ silent: true });
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <Loader2 className="animate-spin text-blue-600" size={48} />
      </div>
    );
  }
  if (error || !doc) {
    return <div className="p-8 text-center text-red-600 font-bold">{error || 'Document not found'}</div>;
  }

  const primaryArtifact = doc.artifacts[0];
  const primaryFile = doc.files[0];

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-20 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <Link to="/review" className="p-2 hover:bg-slate-100 rounded-full transition">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">{doc.title}</h1>
            <Badge variant="outline" className="uppercase text-[10px] font-black">
              {doc.doc_type}
            </Badge>
          </div>
          <p className="text-slate-500 text-sm font-medium">
            Created: {new Date(doc.created_at).toLocaleString('vi-VN')}
          </p>
        </div>
        <div className="ml-auto">
          <Badge className="px-4 py-1 text-sm font-bold capitalize">
            {doc.state.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="border-b border-slate-100 pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <FileText size={18} className="text-slate-700" /> Stored file & extraction (baseline)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4 text-sm">
              {!primaryFile && <p className="text-slate-500">No file rows persisted for this document.</p>}
              {primaryFile && (
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">File metadata</p>
                  <p><span className="font-semibold text-slate-700">Name:</span> {primaryFile.file_name}</p>
                  <p><span className="font-semibold text-slate-700">MIME:</span> {primaryFile.mime_type}</p>
                  <p><span className="font-semibold text-slate-700">Size:</span> {primaryFile.file_size_bytes} bytes</p>
                  <p className="font-mono text-xs break-all">
                    <span className="font-semibold text-slate-700 font-sans">Storage key:</span> {primaryFile.storage_relative_path}
                  </p>
                  {primaryFile.sha256_hex && (
                    <p className="font-mono text-xs break-all">
                      <span className="font-semibold text-slate-700 font-sans">SHA-256:</span> {primaryFile.sha256_hex}
                    </p>
                  )}
                </div>
              )}
              {!primaryArtifact && (
                <p className="text-amber-800 text-sm font-medium">No extracted artifact yet — upload path may be incomplete.</p>
              )}
              {primaryArtifact && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 space-y-3">
                  <p className="text-[10px] font-black uppercase tracking-widest text-blue-500">Extracted artifact (preview)</p>
                  <p>
                    <span className="font-semibold text-slate-800">Method:</span> {primaryArtifact.extraction_method}
                  </p>
                  <p>
                    <span className="font-semibold text-slate-800">Source label:</span> {primaryArtifact.extraction_source_label}
                  </p>
                  <div>
                    <p className="font-semibold text-slate-800 mb-1">Extracted text</p>
                    <p className="text-slate-700 leading-relaxed whitespace-pre-wrap border border-slate-200 rounded-lg p-3 bg-white max-h-48 overflow-y-auto">
                      {primaryArtifact.extracted_text}
                    </p>
                  </div>
                  {primaryArtifact.structured_metadata_json && (
                    <div>
                      <p className="font-semibold text-slate-800 mb-1">Structured metadata (mock)</p>
                      <pre className="text-xs font-mono bg-white border border-slate-200 rounded-lg p-3 overflow-x-auto">
                        {JSON.stringify(primaryArtifact.structured_metadata_json, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-blue-100 bg-blue-50/30 overflow-hidden">
            <CardHeader className="bg-blue-50/50 border-b border-blue-100 pb-3">
              <CardTitle className="text-base flex items-center gap-2 text-blue-800">
                <BrainCircuit size={18} /> AI analysis (mock provider)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {doc.analysis ? (
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <p className="text-[10px] font-black uppercase tracking-widest text-blue-400">
                      Source: {doc.analysis.analysis_source_label}
                    </p>
                    <div className="space-y-1">
                      <label className="text-[10px] font-black uppercase tracking-widest text-blue-400">Suggested Dept</label>
                      <div className="flex items-center gap-2 font-bold text-slate-900">
                        <Building size={16} className="text-blue-600" />
                        {doc.analysis.suggested_department}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-black uppercase tracking-widest text-blue-400">Urgency Score</label>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((v) => (
                          <div
                            key={v}
                            className={`h-1.5 w-8 rounded-full ${
                              v <= doc.analysis!.urgency_score ? 'bg-orange-500' : 'bg-slate-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-blue-400">Summary</label>
                    <p className="text-sm text-slate-700 leading-relaxed font-medium italic">
                      &quot;{doc.analysis.summary}&quot;
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 space-y-4">
                  <p className="text-slate-500 text-sm font-medium">No AI analysis row for this document yet.</p>
                  <button
                    disabled={actionLoading}
                    onClick={() => handleAction('analyze')}
                    className="px-6 py-2 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-700 flex items-center gap-2 mx-auto disabled:opacity-50"
                  >
                    {actionLoading ? <Loader2 className="animate-spin" size={16} /> : <BrainCircuit size={16} />}
                    Run mock AI analysis
                  </button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare size={18} className="text-purple-600" /> Consultation thread
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {doc.consultations.length > 0 ? (
                doc.consultations.map((note) => (
                  <div key={note.id} className="flex gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shrink-0 border border-slate-200 shadow-sm">
                      <User size={18} className="text-slate-400" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">Role ID: {note.author_role_id}</span>
                        <span className="text-[10px] text-slate-400">
                          {new Date(note.created_at).toLocaleTimeString('vi-VN')}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed">{note.content}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-slate-400">
                  <p className="text-sm font-medium italic">No consultation notes yet.</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ScrollText size={18} className="text-slate-600" /> Recent audit log
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-64 overflow-y-auto text-xs font-mono text-slate-600">
              {doc.audit_logs.length === 0 && <p className="text-slate-400">No audit entries.</p>}
              {doc.audit_logs
                .slice()
                .reverse()
                .slice(0, 12)
                .map((a) => (
                  <div key={a.id} className="border-b border-slate-100 pb-2">
                    <div className="flex justify-between gap-2 text-[10px] text-slate-400">
                      <span>{new Date(a.timestamp).toLocaleString('vi-VN')}</span>
                      <span>role {a.actor_role_id}</span>
                    </div>
                    <p className="text-slate-800 font-bold">{a.action}</p>
                    {a.details && <pre className="whitespace-pre-wrap break-all">{JSON.stringify(a.details)}</pre>}
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Shield size={18} className="text-slate-700" /> Workflow actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1 text-xs text-slate-500">
                <label className="font-semibold text-slate-700">Route to department ID</label>
                <select
                  value={routeDept}
                  onChange={(e) => setRouteDept(Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-2 py-1 bg-white"
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      Department {n}
                    </option>
                  ))}
                </select>
              </div>

              <ActionButton
                label="Run mock analysis"
                icon={<BrainCircuit size={16} />}
                onClick={() => handleAction('analyze')}
                disabled={actionLoading || !!doc.analysis}
                active={role === 'Intake Clerk' || role === 'Supervisor'}
                variant="blue"
              />
              <ActionButton
                label="Route to department"
                icon={<Send size={16} />}
                onClick={() => handleAction('route')}
                disabled={actionLoading || doc.state !== 'routed_pending_human_review'}
                active={role === 'Intake Clerk' || role === 'Department Reviewer' || role === 'Supervisor'}
              />
              <ActionButton
                label="Start department review"
                icon={<Building size={16} />}
                onClick={() => handleAction('start-review')}
                disabled={actionLoading || doc.state !== 'assigned_to_department'}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
                variant="purple"
              />
              <ActionButton
                label="Request consultation"
                icon={<MessageSquare size={16} />}
                onClick={() => handleAction('request-consultation')}
                disabled={actionLoading || doc.state !== 'under_review'}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
                variant="purple"
              />
              <ActionButton
                label="Mark consultation complete"
                icon={<CheckCircle2 size={16} />}
                onClick={() => handleAction('complete-consultation')}
                disabled={actionLoading || doc.state !== 'consultation_requested'}
                active={role === 'Consultant' || role === 'Department Reviewer' || role === 'Supervisor'}
                variant="emerald"
              />
              <ActionButton
                label="Prepare response draft"
                icon={<Send size={16} />}
                onClick={() => handleAction('prepare-response')}
                disabled={
                  actionLoading || !['under_review', 'consultation_completed'].includes(doc.state)
                }
                active={role === 'Department Reviewer' || role === 'Supervisor'}
                variant="emerald"
              />
              <ActionButton
                label="Approve & close (supervisor)"
                icon={<CheckCircle2 size={16} />}
                onClick={() => handleAction('approve')}
                disabled={actionLoading || doc.state !== 'response_prepared'}
                variant="emerald"
                active={role === 'Supervisor'}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <History size={18} className="text-slate-600" /> Routing decisions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {doc.decisions.map((dec) => (
                <div key={dec.id} className="text-sm border-l-2 border-slate-200 pl-4 py-1 space-y-1">
                  <p className="font-bold text-slate-900">Dept ID: {dec.target_department_id}</p>
                  <p className="text-xs text-slate-500 italic">&quot;{dec.note || 'No note'}&quot;</p>
                  <p className="text-[10px] text-slate-300 font-mono uppercase tracking-tighter">
                    {new Date(dec.created_at).toLocaleString('vi-VN')}
                  </p>
                </div>
              ))}
              {doc.decisions.length === 0 && <p className="text-xs text-slate-400 italic">No routing decisions yet.</p>}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ActionButton({
  label,
  icon,
  onClick,
  disabled,
  active,
  variant = 'blue',
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  active: boolean;
  variant?: 'blue' | 'emerald' | 'purple';
}) {
  if (!active) return null;

  const colors = {
    blue: 'bg-blue-600 hover:bg-blue-700',
    emerald: 'bg-emerald-600 hover:bg-emerald-700',
    purple: 'bg-purple-600 hover:bg-purple-700',
  };

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-4 py-3 rounded-xl text-white font-bold text-sm transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed ${colors[variant]}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
