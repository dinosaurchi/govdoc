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
  Loader2,
  BrainCircuit,
  History,
  FileText,
  ScrollText,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiGet, apiPost } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

type AIAnalysis = {
  id: string;
  stage: string;
  model_name: string;
  prompt_version: string;
  source: string;
  payload_json: Record<string, unknown>;
  confidence: number | null;
  created_at: string;
};

type AuditEvent = {
  id: string;
  document_id: string | null;
  actor_role: string | null;
  event_type: string;
  from_state: string | null;
  to_state: string | null;
  metadata_json: Record<string, unknown>;
  occurred_at: string;
};

type RoutingDecision = {
  id: string;
  document_id: string;
  suggested_department_id: string | null;
  final_department_id: string | null;
  decided_by_role: string | null;
  decision: string;
  rationale: string | null;
  created_at: string;
};

type ConsultationNote = {
  id: string;
  document_id: string;
  author_role: string;
  target_role: string | null;
  body: string;
  resolved_at: string | null;
  created_at: string;
};

type DocDetail = {
  id: string;
  title: string;
  doc_number: string | null;
  issuing_agency: string | null;
  status: string;
  security_level: string;
  urgency: string;
  assigned_department_id: string | null;
  created_at: string;
  updated_at: string;
  files: Array<{
    id: string;
    original_filename: string;
    mime_type: string;
    size_bytes: number;
    storage_key: string;
    sha256: string;
    created_at: string;
  }>;
  artifacts: Array<{
    id: string;
    extraction_method: string;
    text: string;
    page_count: number;
    warnings: string[];
    extracted_at: string;
  }>;
  analyses: AIAnalysis[];
  routing_decisions: RoutingDecision[];
  consultation_notes: ConsultationNote[];
  audit_events: AuditEvent[];
};

const STAGE_LABELS: Record<string, string> = {
  classify: 'Classification',
  summarize: 'Summary',
  route: 'Routing Suggestion',
  escalate: 'Escalation Analysis',
};

const STAGE_COLORS: Record<string, string> = {
  classify: 'bg-blue-100 text-blue-800',
  summarize: 'bg-emerald-100 text-emerald-800',
  route: 'bg-orange-100 text-orange-800',
  escalate: 'bg-red-100 text-red-800',
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

  const fetchDoc = async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) setLoading(true);
    try {
      const data = await apiGet<DocDetail>(`/documents/${id}`, role);
      setDoc(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
      setDoc(null);
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await apiGet<DocDetail>(`/documents/${id}`, role);
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
    return () => { active = false; };
  }, [id, role]);

  const handleAction = async (action: string, payload: Record<string, string> = {}) => {
    setActionLoading(true);
    try {
      if (action === 'approve-routing') {
        await apiPost(`/documents/${id}/approve-routing`, undefined, role);
      } else if (action === 'reroute') {
        await apiPost(`/documents/${id}/reroute`, payload, role);
      } else if (action === 'escalate') {
        await apiPost(`/documents/${id}/escalate`, undefined, role);
      } else if (action === 'mark-out-of-scope') {
        await apiPost(`/documents/${id}/mark-out-of-scope`, undefined, role);
      } else if (action === 'close') {
        await apiPost(`/documents/${id}/close`, undefined, role);
      } else if (action === 'request-consultation') {
        await apiPost(`/documents/${id}/request-consultation`, payload, role);
      } else if (action === 'analyze') {
        await apiPost(`/documents/${id}/analyze`, undefined, role);
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

  const primaryFile = doc.files[0];
  const primaryArtifact = doc.artifacts[0];
  const analysesByStage: Record<string, AIAnalysis> = {};
  for (const a of doc.analyses) {
    analysesByStage[a.stage] = a;
  }
  const hasAnalysis = doc.analyses.length > 0;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-20 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <Link to="/review" className="p-2 hover:bg-slate-100 rounded-full transition">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">{doc.title}</h1>
            {doc.urgency !== 'normal' && (
              <Badge className={`uppercase text-[10px] font-black ${doc.urgency === 'critical' ? 'bg-red-600' : 'bg-orange-500'}`}>
                {doc.urgency}
              </Badge>
            )}
          </div>
          <p className="text-slate-500 text-sm font-medium">
            Created: {new Date(doc.created_at).toLocaleString()}
            {doc.issuing_agency && <> · From: {doc.issuing_agency}</>}
          </p>
        </div>
        <div className="ml-auto">
          <Badge className="px-4 py-1 text-sm font-bold capitalize">
            {doc.status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* File & Extraction Card */}
          <Card>
            <CardHeader className="border-b border-slate-100 pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <FileText size={18} className="text-slate-700" /> Stored file &amp; extraction
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4 text-sm">
              {!primaryFile && <p className="text-slate-500">No file attached to this document.</p>}
              {primaryFile && (
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 space-y-2">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">File metadata</p>
                  <p><span className="font-semibold text-slate-700">Name:</span> {primaryFile.original_filename}</p>
                  <p><span className="font-semibold text-slate-700">MIME:</span> {primaryFile.mime_type}</p>
                  <p><span className="font-semibold text-slate-700">Size:</span> {primaryFile.size_bytes} bytes</p>
                  {primaryFile.sha256 && (
                    <p className="font-mono text-xs break-all">
                      <span className="font-semibold text-slate-700 font-sans">SHA-256:</span> {primaryFile.sha256}
                    </p>
                  )}
                </div>
              )}
              {primaryArtifact && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <p className="text-[10px] font-black uppercase tracking-widest text-blue-500">Extracted artifact</p>
                    <Badge variant="outline" className="text-[9px] font-mono">{primaryArtifact.extraction_method}</Badge>
                  </div>
                  <p><span className="font-semibold text-slate-800">Pages:</span> {primaryArtifact.page_count}</p>
                  <div>
                    <p className="font-semibold text-slate-800 mb-1">Extracted text</p>
                    <p className="text-slate-700 leading-relaxed whitespace-pre-wrap border border-slate-200 rounded-lg p-3 bg-white max-h-48 overflow-y-auto">
                      {primaryArtifact.text}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Analyses Card */}
          <Card className="border-blue-100 bg-blue-50/30 overflow-hidden">
            <CardHeader className="bg-blue-50/50 border-b border-blue-100 pb-3">
              <CardTitle className="text-base flex items-center gap-2 text-blue-800">
                <BrainCircuit size={18} /> AI Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {hasAnalysis ? (
                <div className="space-y-4">
                  {doc.analyses.map((analysis) => (
                    <AnalysisCard key={analysis.id} analysis={analysis} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 space-y-4">
                  <p className="text-slate-500 text-sm font-medium">No AI analysis yet for this document.</p>
                  <button
                    disabled={actionLoading}
                    onClick={() => handleAction('analyze')}
                    className="px-6 py-2 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-700 flex items-center gap-2 mx-auto disabled:opacity-50"
                  >
                    {actionLoading ? <Loader2 className="animate-spin" size={16} /> : <BrainCircuit size={16} />}
                    Run AI analysis
                  </button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Routing Decisions */}
          {(doc.routing_decisions.length > 0) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <ScrollText size={18} className="text-slate-600" /> Routing decisions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {doc.routing_decisions.map((dec) => (
                  <div key={dec.id} className="text-sm border-l-2 border-slate-200 pl-4 py-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={dec.decision === 'accepted' ? 'default' : 'secondary'} className="text-[9px]">
                        {dec.decision}
                      </Badge>
                      {dec.suggested_department_id && (
                        <span className="text-xs text-slate-500">Suggested: {dec.suggested_department_id}</span>
                      )}
                      {dec.final_department_id && (
                        <span className="text-xs font-bold text-slate-800">Final: {dec.final_department_id}</span>
                      )}
                    </div>
                    {dec.rationale && <p className="text-xs text-slate-500 italic">&quot;{dec.rationale}&quot;</p>}
                    <p className="text-[10px] text-slate-300 font-mono">
                      {new Date(dec.created_at).toLocaleString()} · by {dec.decided_by_role || 'AI'}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Consultation Notes */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare size={18} className="text-purple-600" /> Consultation thread
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {doc.consultation_notes.length > 0 ? (
                doc.consultation_notes.map((note) => (
                  <div key={note.id} className="flex gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shrink-0 border border-slate-200 shadow-sm">
                      <User size={18} className="text-slate-400" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">{note.author_role}</span>
                        {note.target_role && <span className="text-[10px] text-slate-400">→ {note.target_role}</span>}
                        <span className="text-[10px] text-slate-400">
                          {new Date(note.created_at).toLocaleTimeString()}
                        </span>
                        {note.resolved_at && <Badge variant="secondary" className="text-[9px]">Resolved</Badge>}
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed">{note.body}</p>
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

          {/* Audit Events */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <History size={18} className="text-slate-600" /> Audit timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-h-64 overflow-y-auto text-xs font-mono text-slate-600">
              {doc.audit_events.length === 0 && <p className="text-slate-400">No audit entries.</p>}
              {doc.audit_events
                .slice()
                .reverse()
                .slice(0, 20)
                .map((a) => (
                  <div key={a.id} className="border-b border-slate-100 pb-2">
                    <div className="flex justify-between gap-2 text-[10px] text-slate-400">
                      <span>{new Date(a.occurred_at).toLocaleString()}</span>
                      <span>{a.actor_role || 'system'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <p className="text-slate-800 font-bold">{a.event_type}</p>
                      {a.from_state && a.to_state && (
                        <span className="text-slate-400">
                          {a.from_state} → {a.to_state}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar — Workflow Actions */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Shield size={18} className="text-slate-700" /> Workflow actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <ActionButton
                label="Run AI analysis"
                icon={<BrainCircuit size={16} />}
                onClick={() => handleAction('analyze')}
                disabled={actionLoading || hasAnalysis}
                active={role === 'Intake Clerk' || role === 'Supervisor'}
                variant="blue"
              />
              <ActionButton
                label="Approve routing"
                icon={<CheckCircle2 size={16} />}
                onClick={() => handleAction('approve-routing')}
                disabled={actionLoading || doc.status !== 'analyzed'}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
                variant="emerald"
              />
              <ActionButton
                label="Request consultation"
                icon={<MessageSquare size={16} />}
                onClick={() => handleAction('request-consultation', { target_role: 'consultant', body: 'Consultation requested from document detail.' })}
                disabled={actionLoading || !['under_review', 'routed'].includes(doc.status)}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
                variant="purple"
              />
              <ActionButton
                label="Escalate to supervisor"
                icon={<AlertTriangle size={16} />}
                onClick={() => handleAction('escalate')}
                disabled={actionLoading}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
                variant="blue"
              />
              <ActionButton
                label="Mark out of scope"
                icon={<Send size={16} />}
                onClick={() => handleAction('mark-out-of-scope')}
                disabled={actionLoading}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
              />
              <ActionButton
                label="Close document"
                icon={<CheckCircle2 size={16} />}
                onClick={() => handleAction('close')}
                disabled={actionLoading}
                active={role === 'Supervisor'}
                variant="emerald"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function AnalysisCard({ analysis }: { analysis: AIAnalysis }) {
  const stageLabel = STAGE_LABELS[analysis.stage] || analysis.stage;
  const stageColor = STAGE_COLORS[analysis.stage] || 'bg-slate-100 text-slate-800';
  const payload = analysis.payload_json;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge className={`text-[9px] font-black uppercase ${stageColor}`}>
            {stageLabel}
          </Badge>
          <span className="text-[10px] text-slate-400 font-mono">
            {analysis.model_name}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[9px] font-mono">
            {analysis.source}
          </Badge>
          {analysis.confidence != null && (
            <span className="text-xs font-bold text-slate-600">
              {(analysis.confidence * 100).toFixed(1)}%
            </span>
          )}
        </div>
      </div>
      <div className="text-xs text-slate-600 space-y-1">
        <pre className="whitespace-pre-wrap break-all bg-slate-50 rounded-lg p-3 border border-slate-100 overflow-x-auto max-h-40">
          {JSON.stringify(payload, null, 2)}
        </pre>
      </div>
      <p className="text-[10px] text-slate-300">
        {new Date(analysis.created_at).toLocaleString()} · prompt v{analysis.prompt_version}
      </p>
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
