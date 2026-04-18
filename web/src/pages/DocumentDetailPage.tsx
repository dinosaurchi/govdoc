import { useEffect, useRef, useState } from 'react';
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
  XCircle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronRight,
  Circle,
  UserCheck,
  Sparkles,
  Building2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiGet, apiPost } from '@/lib/api';
import { formatBytes } from '@/lib/format';
import { useRole } from '@/hooks/use-role';
import {
  getWorkflowActionStates,
  getWorkflowStatusMessage,
  isTerminalStatus,
  toRoleId,
  toButtonVariant,
  PIPELINE_STAGES,
  getPipelineStepState,
  getResponsibleRoles,
  getNextStepHint,
  getActionsAvailableForOtherRoles,
  toFrontendRoleLabel,
  partitionByForwardness,
  getForwardActionId,
  ROLE_LABEL,
  type ButtonVariant,
  type Role,
} from '@/pages/document-detail/workflow-actions';

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

type Department = {
  id: string;
  name: string;
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
  const { role, setRole } = useRole();
  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConsultInput, setShowConsultInput] = useState(false);
  const [consultBody, setConsultBody] = useState('');
  const [departments, setDepartments] = useState<Department[]>([]);
  const [showRerouteInput, setShowRerouteInput] = useState(false);
  const [rerouteDepartmentId, setRerouteDepartmentId] = useState('');
  const [rerouteRationale, setRerouteRationale] = useState('');
  const [analysisView, setAnalysisView] = useState<'rendered' | 'raw'>('rendered');
  const [flash, setFlash] = useState<{
    tone: 'success' | 'error';
    message: string;
    link?: { to: string; label: string; hint?: string };
  } | null>(null);

  const flashBannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!flash) return;
    // Longer dwell when we show a follow-up link so users can click it.
    const ms = flash.link ? 12_000 : 5000;
    const handle = window.setTimeout(() => setFlash(null), ms);
    return () => window.clearTimeout(handle);
  }, [flash]);

  // After requesting consultation the user is often scrolled to the workflow
  // panel — scroll the success banner into view so the follow-up link is seen.
  useEffect(() => {
    if (!flash?.link) return;
    const id = requestAnimationFrame(() => {
      flashBannerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    return () => cancelAnimationFrame(id);
  }, [flash]);

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
        const [data, deptList] = await Promise.all([
          apiGet<DocDetail>(`/documents/${id}`, role),
          apiGet<Department[]>('/meta/departments', role),
        ]);
        if (active) {
          setDoc(data);
          setDepartments(deptList);
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
      } else if (action === 'approve') {
        await apiPost(`/documents/${id}/approve`, undefined, role);
      } else if (action === 'close') {
        await apiPost(`/documents/${id}/close`, undefined, role);
      } else if (action === 'request-consultation') {
        await apiPost(`/documents/${id}/request-consultation`, payload, role);
      } else if (action === 'resolve-consultation') {
        await apiPost(`/documents/${id}/resolve-consultation/${payload.note_id}`, undefined, role);
      } else if (action === 'analyze') {
        await apiPost(`/documents/${id}/analyze`, undefined, role);
      }
      await fetchDoc({ silent: true });
      let successLink: { to: string; label: string; hint?: string } | undefined;
      if (action === 'request-consultation') {
        successLink = {
          to: `/consultation?doc=${id}`,
          label: 'Open consultation thread',
          hint:
            'Same thread appears here under "Consultation thread" — use the link for the full chat view.',
        };
      } else if (action === 'approve') {
        successLink = {
          to: `/response?doc=${id}`,
          label: 'Continue on Response & Closeout',
          hint:
            'Pending drafts stay in the Response queue until you approve and close — this link opens your case there.',
        };
      } else if (action === 'close') {
        successLink = {
          to: `/response?doc=${id}`,
          label: 'View on Response & Closeout',
          hint:
            'After close, the case appears under Dispatched on the Response page — this link jumps straight to it.',
        };
      }
      setFlash({
        tone: 'success',
        message: actionSuccessMessage(action, payload, departments),
        ...(successLink ? { link: successLink } : {}),
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Action failed';
      setFlash({ tone: 'error', message });
    } finally {
      setActionLoading(false);
    }
  };

  const availableDepartments = departments.filter((department) => department.id !== doc?.assigned_department_id);

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
  const hasConsultationThread = doc.consultation_notes.length > 0 || doc.status === 'in_consultation';
  const departmentNames = Object.fromEntries(departments.map((department) => [department.id, department.name]));
  const analysesByStage: Record<string, AIAnalysis> = {};
  for (const a of doc.analyses) {
    analysesByStage[a.stage] = a;
  }
  const hasAnalysis = doc.analyses.length > 0;

  // Workflow action model
  const roleId = toRoleId(role);
  const terminal = isTerminalStatus(doc.status);
  const actionStates = terminal
    ? { available: [], disabled: [], hidden: [] }
    : getWorkflowActionStates(doc, roleId);

  const getActionIcon = (actionId: string) => {
    switch (actionId) {
      case 'analyze': return <BrainCircuit size={16} />;
      case 'approve-routing': return <CheckCircle2 size={16} />;
      case 'reroute': return <Send size={16} />;
      case 'request-consultation': return <MessageSquare size={16} />;
      case 'resolve-consultation': return <CheckCircle2 size={16} />;
      case 'approve': return <CheckCircle2 size={16} />;
      case 'escalate': return <AlertTriangle size={16} />;
      case 'mark-out-of-scope': return <Send size={16} />;
      case 'close': return <CheckCircle2 size={16} />;
      default: return <CheckCircle2 size={16} />;
    }
  };
  const displayDepartment = (value: string) => departmentNames[value] ?? humanizeEnum(value);

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
          <p
            className="text-slate-600 text-sm font-medium flex items-center gap-1.5 mt-1"
            data-testid="document-assigned-department"
          >
            <Building2 size={14} className="text-slate-400" />
            <span className="text-slate-500">Assigned to:</span>
            {doc.assigned_department_id ? (
              <span className="font-bold text-slate-800">{displayDepartment(doc.assigned_department_id)}</span>
            ) : (
              <span className="italic text-slate-400">Not yet assigned</span>
            )}
          </p>
        </div>
        <div className="ml-auto">
          <Badge className="px-4 py-1 text-sm font-bold capitalize">
            {doc.status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      {flash && (
        <div
          ref={flashBannerRef}
          className={`rounded-xl border px-4 py-3 text-sm font-medium flex items-start gap-3 ${
            flash.tone === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
              : 'border-red-200 bg-red-50 text-red-900'
          }`}
          role="status"
          aria-live="polite"
          data-testid={`document-flash-${flash.tone}`}
        >
          {flash.tone === 'success' ? (
            <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle size={18} className="text-red-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1 min-w-0 space-y-2">
            <p>{flash.message}</p>
            {flash.link && (
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to={flash.link.to}
                  data-testid="document-flash-follow-link"
                  className="inline-flex items-center rounded-lg border border-emerald-400 bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-emerald-900 hover:bg-emerald-100"
                >
                  {flash.link.label}
                </Link>
                {flash.link.hint && (
                  <span className="text-[11px] text-emerald-800/90">{flash.link.hint}</span>
                )}
              </div>
            )}
          </div>
          <button
            type="button"
            className="text-xs font-bold uppercase tracking-wider opacity-60 hover:opacity-100 shrink-0"
            onClick={() => setFlash(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <OrphanedConsultationBanner doc={doc} />
      <NoAssignedDepartmentBanner doc={doc} />

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
                  <p data-testid="file-size">
                    <span className="font-semibold text-slate-700">Size:</span>{' '}
                    {formatBytes(primaryFile.size_bytes)}
                    <span className="text-xs text-slate-400 ml-2">
                      ({primaryFile.size_bytes.toLocaleString()} bytes)
                    </span>
                  </p>
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
              <div className="flex items-center justify-between gap-4">
                <CardTitle className="text-base flex items-center gap-2 text-blue-800">
                  <BrainCircuit size={18} /> AI Analysis
                </CardTitle>
                <div className="inline-flex rounded-lg border border-blue-100 bg-white p-1 text-xs font-bold">
                  <button
                    type="button"
                    onClick={() => setAnalysisView('rendered')}
                    className={`rounded-md px-3 py-1 transition ${
                      analysisView === 'rendered' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-700'
                    }`}
                  >
                    Rendered
                  </button>
                  <button
                    type="button"
                    onClick={() => setAnalysisView('raw')}
                    className={`rounded-md px-3 py-1 transition ${
                      analysisView === 'raw' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-blue-700'
                    }`}
                  >
                    Raw JSON
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {hasAnalysis ? (
                <div className="space-y-4">
                  {doc.analyses.map((analysis) => (
                    <AnalysisCard key={analysis.id} analysis={analysis} view={analysisView} />
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
                {doc.status === 'out_of_scope' && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    This document was later marked out of scope. The routing record below is preserved for audit history.
                  </div>
                )}
                {doc.routing_decisions.map((dec) => (
                  <div key={dec.id} className="text-sm border-l-2 border-slate-200 pl-4 py-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={dec.decision === 'accepted' ? 'default' : 'secondary'} className="text-[9px] uppercase">
                        {humanizeEnum(dec.decision)}
                      </Badge>
                      {dec.suggested_department_id && (
                        <span className="text-xs text-slate-500">Suggested: {displayDepartment(dec.suggested_department_id)}</span>
                      )}
                      {dec.final_department_id && (
                        <span className="text-xs font-bold text-slate-800">Final: {displayDepartment(dec.final_department_id)}</span>
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
          {hasConsultationThread && (
            <Card data-testid="consultation-thread-card">
              <CardHeader className="border-b border-slate-100 pb-4 space-y-3">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <MessageSquare size={18} className="text-purple-600" /> Consultation thread
                  </CardTitle>
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Link
                      to={`/consultation?doc=${doc.id}`}
                      data-testid="consultation-thread-full-view-link"
                      className="inline-flex items-center rounded-lg border border-purple-300 bg-purple-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-purple-900 hover:bg-purple-100"
                    >
                      Open consultation page
                    </Link>
                    <Link
                      to="/review"
                      data-testid="consultation-thread-review-queue-link"
                      className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-700 hover:bg-slate-100"
                    >
                      Review queue
                    </Link>
                  </div>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  The same messages appear here and on the{' '}
                  <Link to="/consultation" className="font-semibold text-purple-700 underline-offset-2 hover:underline">
                    Internal Consultation
                  </Link>{' '}
                  page (chat-style layout). Use <span className="font-semibold">Review queue</span> to find this case
                  alongside other documents.
                </p>
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
                    <p className="text-sm font-medium italic">Consultation is active, but no notes have been recorded yet.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

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
          <WorkflowPipeline
            status={doc.status}
            hadConsultationActivity={
              doc.consultation_notes.length > 0 || doc.status === 'in_consultation'
            }
          />

          <Card data-testid="workflow-actions-panel">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Shield size={18} className="text-slate-700" /> Workflow actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <RoutingDecisionCallout
                decisions={doc.routing_decisions}
                displayDepartment={displayDepartment}
              />
              <WorkflowContext
                status={doc.status}
                role={role}
                roleId={roleId}
                terminal={terminal}
                hasAvailableActions={actionStates.available.length > 0}
              />

              {terminal ? (
                <TerminalStateCard status={doc.status} />
              ) : actionStates.available.length === 0 && actionStates.disabled.length === 0 ? (
                <div
                  className="rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600 leading-relaxed"
                  data-testid="workflow-empty"
                >
                  <p className="font-semibold text-slate-700">No actions for your role on this document.</p>
                  <p className="mt-1 text-xs text-slate-500">{getNextStepHint(doc, roleId)}</p>
                </div>
              ) : (
                <>
                  {/* Primary "next step" actions — the forward action (if any) is
                      promoted above alternatives so the user always knows which
                      button advances the pipeline. */}
                  {actionStates.available.length > 0 && (() => {
                    // Hide supervisor-self-escalate noise, then partition
                    const filtered = actionStates.available.filter((a) => {
                      if (a.id === 'escalate' && roleId === 'supervisor') return false;
                      return true;
                    });
                    const { forward, alternatives } = partitionByForwardness(
                      filtered,
                      doc,
                      roleId,
                    );
                    const renderOne = (action: typeof filtered[number]) =>
                      renderActionControl({
                        action,
                        isAvailable: true,
                        reason: null,
                        getActionIcon,
                        showRerouteInput,
                        setShowRerouteInput,
                        rerouteDepartmentId,
                        setRerouteDepartmentId,
                        rerouteRationale,
                        setRerouteRationale,
                        availableDepartments,
                        showConsultInput,
                        setShowConsultInput,
                        consultBody,
                        setConsultBody,
                        handleAction,
                        actionLoading,
                        doc,
                      });
                    return (
                      <div className="space-y-4" data-testid="workflow-available-actions">
                        {forward && (
                          <div className="space-y-2" data-testid="workflow-forward-action">
                            <div className="flex items-center gap-2">
                              <Sparkles size={12} className="text-emerald-600" />
                              <p className="text-[10px] font-black uppercase tracking-widest text-emerald-700">
                                Recommended next step
                              </p>
                            </div>
                            <p className="text-xs text-slate-600 leading-relaxed">
                              {forwardExplanation(forward.id)}
                            </p>
                            {renderOne(forward)}
                          </div>
                        )}

                        {alternatives.length > 0 && (
                          <div
                            className="space-y-2 pt-1 border-t border-slate-100"
                            data-testid="workflow-alternative-actions"
                          >
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                              {forward ? 'Or, alternatives' : 'Available actions'}
                            </p>
                            <div className="space-y-2">
                              {alternatives.map((a) => renderOne(a))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}

                  {/* Progression actions available to other roles — only shown
                      when the current role itself has no forward action (i.e.
                      the user genuinely needs to hand off to another role). */}
                  {getForwardActionId(doc, roleId) === null && (
                    <OtherRolesActions
                      doc={doc}
                      currentRoleId={roleId}
                      onSwitchRole={(targetId) => {
                        setRole(toFrontendRoleLabel(targetId) as typeof role);
                      }}
                    />
                  )}

                  {/* Disabled actions — role allows them, but status doesn't */}
                  {actionStates.disabled.length > 0 && (
                    <DisabledActionsDisclosure
                      disabled={actionStates.disabled}
                      getActionIcon={getActionIcon}
                    />
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function AnalysisCard({ analysis, view }: { analysis: AIAnalysis; view: 'rendered' | 'raw' }) {
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
        {view === 'rendered' ? (
          <RenderedAnalysis stage={analysis.stage} payload={payload} />
        ) : (
          <pre className="whitespace-pre-wrap break-all bg-slate-50 rounded-lg p-3 border border-slate-100 overflow-x-auto max-h-40">
            {JSON.stringify(payload, null, 2)}
          </pre>
        )}
      </div>
      <p className="text-[10px] text-slate-300">
        {new Date(analysis.created_at).toLocaleString()}
      </p>
    </div>
  );
}

function RenderedAnalysis({ stage, payload }: { stage: string; payload: Record<string, unknown> }) {
  if (stage === 'classify') {
    return <RenderedClassification payload={payload} />;
  }
  if (stage === 'route') {
    return <RenderedRouting payload={payload} />;
  }
  if (stage === 'escalate') {
    return <RenderedEscalation payload={payload} />;
  }

  const rows = getRenderedRows(stage, payload);

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-500">
        No structured summary available for this analysis.
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      {rows.map((row) => (
        <div key={row.label} className="space-y-1">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">{row.label}</p>
          {row.items ? (
            <ul className="list-disc pl-4 text-sm leading-relaxed text-slate-700">
              {row.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-relaxed text-slate-700">{row.value}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function RenderedRouting({ payload }: { payload: Record<string, unknown> }) {
  const suggestedDepartment = humanizeEnum(payload.suggested_department);
  const secondaryDepartment = humanizeEnum(payload.secondary_department);
  const routingRationale = stringifyValue(payload.routing_rationale);
  const needsConsultation = booleanLabel(payload.needs_consultation);
  const needsSupervisorReview = booleanLabel(payload.needs_supervisor_review);

  return (
    <div className="space-y-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="flex flex-wrap gap-2">
        {suggestedDepartment && <ClassifyPill label="Primary Route" value={suggestedDepartment} tone="blue" />}
        {secondaryDepartment && <ClassifyPill label="Secondary" value={secondaryDepartment} tone="purple" />}
        {needsConsultation && <ClassifyPill label="Consultation" value={needsConsultation} tone={needsConsultation === 'Yes' ? 'amber' : 'slate'} />}
        {needsSupervisorReview && <ClassifyPill label="Supervisor Review" value={needsSupervisorReview} tone={needsSupervisorReview === 'Yes' ? 'amber' : 'slate'} />}
      </div>

      {routingRationale && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Routing Rationale</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-700">{routingRationale}</p>
        </div>
      )}
    </div>
  );
}

function RenderedEscalation({ payload }: { payload: Record<string, unknown> }) {
  const primaryRecommendation = humanizeEnum(payload.primary_recommendation);
  const alternatives = Array.isArray(payload.alternatives)
    ? payload.alternatives.map((item) => humanizeEnum(item)).filter(Boolean)
    : [];
  const ambiguityExplanation = stringifyValue(payload.ambiguity_explanation);
  const consultationNeeded = booleanLabel(payload.needs_consultation);
  const consultationReason = stringifyValue(payload.consultation_reason);

  return (
    <div className="space-y-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="flex flex-wrap gap-2">
        {primaryRecommendation && <ClassifyPill label="Primary Recommendation" value={primaryRecommendation} tone="blue" />}
        {consultationNeeded && <ClassifyPill label="Consultation Needed" value={consultationNeeded} tone={consultationNeeded === 'Yes' ? 'amber' : 'slate'} />}
      </div>

      {alternatives.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Alternatives</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {alternatives.map((item) => (
              <span key={item} className="rounded-full border border-purple-200 bg-purple-50 px-3 py-1 text-xs font-bold text-purple-700">
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {ambiguityExplanation && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Ambiguity Explanation</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-700">{ambiguityExplanation}</p>
        </div>
      )}

      {consultationReason && (
        <div className="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wider text-amber-600">Consultation Reason</p>
          <p className="mt-1 text-sm leading-relaxed text-amber-900">{consultationReason}</p>
        </div>
      )}
    </div>
  );
}

function RenderedClassification({ payload }: { payload: Record<string, unknown> }) {
  const docType = humanizeEnum(payload.doc_type);
  const urgency = humanizeEnum(payload.urgency);
  const confidentiality = humanizeEnum(payload.confidentiality);
  const issuingAgency = stringifyValue(payload.issuing_agency);
  const rationale = stringifyValue(payload.rationale);

  return (
    <div className="space-y-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="flex flex-wrap gap-2">
        {docType && <ClassifyPill label="Type" value={docType} tone="blue" />}
        {urgency && <ClassifyPill label="Urgency" value={urgency} tone="amber" />}
        {confidentiality && <ClassifyPill label="Security" value={confidentiality} tone="slate" />}
      </div>

      {issuingAgency && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Issuing Agency</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">{issuingAgency}</p>
        </div>
      )}

      {rationale && (
        <div className="rounded-lg border border-blue-100 bg-white px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">Classification Rationale</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-700">{rationale}</p>
        </div>
      )}
    </div>
  );
}

function ClassifyPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'blue' | 'amber' | 'slate' | 'purple';
}) {
  const tones = {
    blue: 'border-blue-200 bg-blue-50 text-blue-800',
    amber: 'border-amber-200 bg-amber-50 text-amber-800',
    slate: 'border-slate-200 bg-slate-100 text-slate-700',
    purple: 'border-purple-200 bg-purple-50 text-purple-800',
  };

  return (
    <div className={`rounded-full border px-3 py-1.5 ${tones[tone]}`}>
      <p className="text-[9px] font-black uppercase tracking-wider opacity-70">{label}</p>
      <p className="text-sm font-bold">{value}</p>
    </div>
  );
}

function getRenderedRows(stage: string, payload: Record<string, unknown>) {
  switch (stage) {
    case 'classify':
      return compactRows([
        valueRow('Document Type', payload.doc_type),
        valueRow('Issuing Agency', payload.issuing_agency),
        valueRow('Urgency', payload.urgency),
        valueRow('Confidentiality', payload.confidentiality),
        valueRow('Rationale', payload.rationale),
      ]);
    case 'summarize':
      return compactRows([
        listRow('Summary Points', payload.summary_points),
        valueRow('Key Subject', payload.key_subject),
        listRow('Key Entities', payload.key_entities),
      ]);
    case 'route':
      return compactRows([
        valueRow('Suggested Department', payload.suggested_department),
        valueRow('Secondary Department', payload.secondary_department),
        valueRow('Routing Rationale', payload.routing_rationale),
        valueRow('Needs Consultation', booleanLabel(payload.needs_consultation)),
        valueRow('Needs Supervisor Review', booleanLabel(payload.needs_supervisor_review)),
      ]);
    case 'escalate':
      return compactRows([
        valueRow('Primary Recommendation', payload.primary_recommendation),
        listRow('Alternatives', payload.alternatives),
        valueRow('Ambiguity Explanation', payload.ambiguity_explanation),
        valueRow('Consultation Needed', booleanLabel(payload.needs_consultation)),
        valueRow('Consultation Reason', payload.consultation_reason),
      ]);
    default:
      return objectRows(payload);
  }
}

function compactRows<T>(rows: Array<T | null>): T[] {
  return rows.filter((row): row is T => row !== null);
}

function valueRow(label: string, value: unknown) {
  const text = stringifyValue(value);
  if (!text) return null;
  return { label, value: text };
}

function listRow(label: string, value: unknown) {
  if (!Array.isArray(value)) return null;
  const items = value.map((item) => stringifyValue(item)).filter(Boolean);
  if (items.length === 0) return null;
  return { label, items };
}

function objectRows(payload: Record<string, unknown>) {
  return Object.entries(payload)
    .map(([key, value]) => {
      if (Array.isArray(value)) return listRow(formatKey(key), value);
      return valueRow(formatKey(key), value);
    })
    .filter((row): row is { label: string; value?: string; items?: string[] } => row !== null);
}

function formatKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function stringifyValue(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return '';
}

function booleanLabel(value: unknown): string {
  if (typeof value !== 'boolean') return '';
  return value ? 'Yes' : 'No';
}

function humanizeEnum(value: unknown): string {
  const text = stringifyValue(value);
  if (!text) return '';
  return text
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function forwardExplanation(actionId: string): string {
  switch (actionId) {
    case 'approve-routing':
      return 'Accept the AI-suggested routing and move the document into active review.';
    case 'approve':
      return 'Record formal approval — after this, a Supervisor can close the document to archive it.';
    case 'close':
      return 'Archive the approved document and end the workflow.';
    case 'resolve-consultation':
      return 'Mark the consultation note as resolved so the document can continue.';
    case 'reroute':
      return 'Pick a department to own this document before it can progress further.';
    default:
      return 'This is the action that most advances the workflow right now.';
  }
}

function actionSuccessMessage(
  action: string,
  payload: Record<string, string>,
  departments: Array<{ id: string; name: string }>,
): string {
  const deptName = (id: string | undefined) => {
    if (!id) return '';
    return departments.find((d) => d.id === id)?.name ?? humanizeEnum(id);
  };
  switch (action) {
    case 'approve-routing':
      return 'Routing approved. Document is now under review.';
    case 'approve':
      return 'Document approved. A Supervisor can now close it to archive.';
    case 'reroute': {
      const name = deptName(payload.department_id);
      return name ? `Document rerouted to ${name}.` : 'Document rerouted.';
    }
    case 'escalate':
      return 'Document escalated to supervisor.';
    case 'mark-out-of-scope':
      return 'Document marked out of scope.';
    case 'close':
      return 'Document closed.';
    case 'request-consultation':
      return 'Consultation requested — the consultant can reply from the Consultation page or in the thread below.';
    case 'resolve-consultation':
      return 'Consultation resolved.';
    case 'analyze':
      return 'AI analysis complete.';
    default:
      return 'Action completed successfully.';
  }
}

function ActionButton({
  label,
  icon,
  onClick,
  disabled,
  available,
  variant = 'blue',
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  available: boolean;
  variant?: 'blue' | 'emerald' | 'amber' | 'red';
}) {
  const colors = {
    blue: 'bg-blue-600 hover:bg-blue-700',
    emerald: 'bg-emerald-600 hover:bg-emerald-700',
    amber: 'bg-amber-600 hover:bg-amber-700',
    red: 'bg-red-600 hover:bg-red-700',
  };

  if (!available) {
    return (
      <button
        type="button"
        disabled
        className={`w-full flex items-center gap-2 px-4 py-3 rounded-xl text-white font-bold text-sm opacity-40 cursor-not-allowed ${colors[variant]}`}
      >
        {icon}
        <span>{label}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-4 py-3 rounded-xl text-white font-bold text-sm transition-all shadow-sm hover:shadow disabled:opacity-50 disabled:cursor-not-allowed ${colors[variant]}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function DisabledActionWrapper({ reason, children }: { reason: string | null; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      {children}
      {reason && <p className="text-[10px] text-slate-400 px-1">{reason}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workflow guide — visual pipeline + role context + disabled-actions disclosure
// ---------------------------------------------------------------------------

function WorkflowPipeline({
  status,
  hadConsultationActivity,
}: {
  status: string;
  hadConsultationActivity: boolean;
}) {
  const terminal = isTerminalStatus(status);

  return (
    <Card data-testid="workflow-pipeline">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <ScrollText size={18} className="text-slate-700" /> Workflow progress
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2">
          {PIPELINE_STAGES.map((stage, idx) => {
            const stepState = getPipelineStepState(status, idx, {
              hadConsultationActivity,
            });
            const done = stepState === 'done';
            const active = stepState === 'active';
            const icon = done ? (
              <CheckCircle2 size={16} className="text-emerald-600" />
            ) : active ? (
              <Circle size={16} className="text-blue-600 fill-blue-100" />
            ) : (
              <Circle size={16} className="text-slate-300" />
            );
            return (
              <li
                key={stage.id}
                className={`flex items-start gap-3 rounded-lg px-2 py-1.5 ${
                  active ? 'bg-blue-50' : ''
                }`}
                data-testid={`pipeline-stage-${stage.id}`}
                data-status={stepState}
              >
                <div className="mt-0.5 shrink-0">{icon}</div>
                <div className="flex-1">
                  <p
                    className={`text-xs font-bold ${
                      active ? 'text-blue-800' : done ? 'text-slate-700' : 'text-slate-400'
                    }`}
                  >
                    {stage.label}
                  </p>
                  <p className={`text-[11px] ${active ? 'text-blue-700' : 'text-slate-400'}`}>
                    {stage.description}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
        {terminal && (
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs text-slate-600">
            <span className="font-bold">Terminal state:</span> {status.replace(/_/g, ' ')}. No
            further workflow actions are possible.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function WorkflowContext({
  status,
  role,
  roleId,
  terminal,
  hasAvailableActions,
}: {
  status: string;
  role: string;
  roleId: Role;
  terminal: boolean;
  hasAvailableActions: boolean;
}) {
  const responsible = getResponsibleRoles(status);
  const hint = getNextStepHint(status, roleId);
  const statusMessage = getWorkflowStatusMessage(status);
  const needsOtherRole =
    !terminal && !hasAvailableActions && responsible.length > 0 && !responsible.includes(roleId);

  return (
    <div className="space-y-3" data-testid="workflow-context">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-1 font-bold text-blue-800">
          <UserCheck size={12} /> Acting as {role}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 border border-slate-200 px-2.5 py-1 font-bold text-slate-700 capitalize">
          Status: {status.replace(/_/g, ' ')}
        </span>
      </div>

      {statusMessage && (
        <p className="text-sm text-slate-600 leading-relaxed">{statusMessage}</p>
      )}

      {!terminal && hint && (
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
          <span className="font-bold text-slate-700">What happens next: </span>
          {hint}
        </div>
      )}

      {needsOtherRole && (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2 text-xs text-amber-900"
          data-testid="workflow-waiting-on"
        >
          <p className="font-bold">Waiting on another role</p>
          <p>
            Your current role ({role}) cannot act on this status. Switch to{' '}
            {responsible.map((r, i) => (
              <span key={r}>
                <span className="font-semibold">{ROLE_LABEL[r]}</span>
                {i < responsible.length - 1 ? ' or ' : ''}
              </span>
            ))}
            {' '}to continue.
          </p>
        </div>
      )}
    </div>
  );
}

function NoAssignedDepartmentBanner({ doc }: { doc: DocDetail }) {
  // A document that's been opened for review but never got a department
  // assignment is stuck in limbo: the forward-action heuristic recommends
  // rerouting (see workflow-actions.ts), but users need a clear visual
  // cue that the current owner is literally nobody.
  if (doc.assigned_department_id) return null;
  // Only surface once the doc has progressed past intake/AI stages.
  const relevantStatuses = new Set(['routed', 'under_review', 'in_consultation']);
  if (!relevantStatuses.has(doc.status)) return null;
  return (
    <div
      role="alert"
      data-testid="no-assigned-department-warning"
      className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        <p className="font-bold">No department assigned to this document</p>
        <p className="text-xs text-amber-800">
          The document is <span className="font-semibold">{humanizeEnum(doc.status)}</span>
          {' '}but has no owning department. Use{' '}
          <span className="font-semibold">Reroute document</span> below to pick a
          department before approving or closing.
        </p>
      </div>
    </div>
  );
}

function OrphanedConsultationBanner({ doc }: { doc: DocDetail }) {
  // If the document is already on `in_consultation` the normal consultation
  // thread UI covers it — no extra warning needed.
  if (doc.status === 'in_consultation') return null;

  const openNotes = doc.consultation_notes.filter((n) => !n.resolved_at);
  if (openNotes.length === 0) return null;

  // Any non-`in_consultation` status with open notes is a data-drift
  // situation caused by the pre-fix `resolve-consultation` bug (see
  // FEEDBACK-13). Warn the user and deep-link them to the consultation
  // thread so they can finish resolving.
  const count = openNotes.length;
  return (
    <div
      role="alert"
      data-testid="orphaned-consultation-warning"
      className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
      <div className="flex-1 space-y-1">
        <p className="font-bold">
          {count} unresolved consultation note{count === 1 ? '' : 's'} on this document
        </p>
        <p className="text-xs text-amber-800">
          The document is currently <span className="font-semibold">{humanizeEnum(doc.status)}</span>
          {' '}but still has open consultation note{count === 1 ? '' : 's'}. Resolve{' '}
          {count === 1 ? 'it' : 'them all'} before approving or closing this document.
        </p>
      </div>
      <Link
        to={`/consultation?doc=${doc.id}`}
        data-testid="orphaned-consultation-link"
        className="shrink-0 rounded-lg border border-amber-400 bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-amber-800 hover:bg-amber-100"
      >
        Open consultation thread
      </Link>
    </div>
  );
}

function RoutingDecisionCallout({
  decisions,
  displayDepartment,
}: {
  decisions: RoutingDecision[];
  displayDepartment: (value: string) => string;
}) {
  if (!decisions || decisions.length === 0) return null;
  const latest = [...decisions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
  const final = latest.final_department_id;
  const decisionLabel = latest.decision === 'rerouted' ? 'Rerouted' : humanizeEnum(latest.decision);
  const when = new Date(latest.created_at).toLocaleString();
  const who = latest.decided_by_role
    ? humanizeEnum(latest.decided_by_role)
    : 'AI analysis';
  return (
    <div
      className="rounded-xl border border-emerald-200 bg-emerald-50/60 px-3 py-3 space-y-1.5"
      data-testid="latest-routing-decision"
    >
      <div className="flex items-center gap-2 text-xs">
        <Send size={14} className="text-emerald-700" />
        <span className="text-[10px] font-black uppercase tracking-widest text-emerald-700">
          Latest routing
        </span>
        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-800">
          {decisionLabel}
        </span>
      </div>
      <p className="text-sm text-slate-800">
        {final ? (
          <>
            Assigned to{' '}
            <span className="font-bold text-emerald-900">{displayDepartment(final)}</span>
          </>
        ) : (
          <span className="italic text-slate-500">No final department recorded</span>
        )}
      </p>
      {latest.rationale && (
        <p className="text-xs text-slate-600 italic">&quot;{latest.rationale}&quot;</p>
      )}
      <p className="text-[10px] text-slate-500">
        by {who} · {when}
      </p>
    </div>
  );
}

function OtherRolesActions({
  doc,
  currentRoleId,
  onSwitchRole,
}: {
  doc: DocDetail;
  currentRoleId: Role;
  onSwitchRole: (roleId: Role) => void;
}) {
  const groups = getActionsAvailableForOtherRoles(
    {
      status: doc.status,
      analyses: doc.analyses,
      consultation_notes: doc.consultation_notes,
      assigned_department_id: doc.assigned_department_id,
    },
    currentRoleId,
  );
  if (groups.length === 0) return null;

  return (
    <div
      className="space-y-2 rounded-xl border border-blue-100 bg-blue-50/40 p-3"
      data-testid="other-roles-actions"
    >
      <p className="text-[10px] font-black uppercase tracking-widest text-blue-700 flex items-center gap-1">
        <UserCheck size={12} /> Next owner(s) for this document
      </p>
      <p className="text-xs text-slate-600 leading-relaxed">
        To progress further, switch to another role:
      </p>
      <div className="space-y-2">
        {groups.map(({ role: targetRole, forward }) => (
          <div key={targetRole} className="rounded-lg bg-white border border-slate-200 p-2 space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-bold text-slate-800">{ROLE_LABEL[targetRole]}</p>
              <button
                type="button"
                onClick={() => onSwitchRole(targetRole)}
                data-testid={`switch-to-${targetRole}`}
                className="text-[10px] font-bold uppercase tracking-wider text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 rounded-md px-2 py-1 transition"
              >
                Switch role
              </button>
            </div>
            {forward && (
              <p className="text-xs text-slate-600">
                Can <span className="font-semibold text-slate-800">{forward.label}</span>
                {' '}to move the workflow forward.
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

type ActionControlParams = {
  action: { id: string; label: string; variant: 'default' | 'success' | 'caution' | 'destructive' };
  isAvailable: boolean;
  reason: string | null;
  getActionIcon: (id: string) => React.ReactNode;
  showRerouteInput: boolean;
  setShowRerouteInput: (v: boolean) => void;
  rerouteDepartmentId: string;
  setRerouteDepartmentId: (v: string) => void;
  rerouteRationale: string;
  setRerouteRationale: (v: string) => void;
  availableDepartments: Array<{ id: string; name: string }>;
  showConsultInput: boolean;
  setShowConsultInput: (v: boolean) => void;
  consultBody: string;
  setConsultBody: (v: string) => void;
  handleAction: (action: string, payload?: Record<string, string>) => void | Promise<void>;
  actionLoading: boolean;
  doc: { consultation_notes: Array<{ id: string; resolved_at: string | null }> };
};

function renderActionControl(p: ActionControlParams): React.ReactNode {
  const {
    action,
    isAvailable,
    reason,
    getActionIcon,
    showRerouteInput,
    setShowRerouteInput,
    rerouteDepartmentId,
    setRerouteDepartmentId,
    rerouteRationale,
    setRerouteRationale,
    availableDepartments,
    showConsultInput,
    setShowConsultInput,
    consultBody,
    setConsultBody,
    handleAction,
    actionLoading,
    doc,
  } = p;
  const icon = getActionIcon(action.id);
  const btnVariant: ButtonVariant = toButtonVariant(action.variant);

  if (action.id === 'reroute') {
    if (isAvailable) {
      return (
        <div key={action.id} className="space-y-2">
          {!showRerouteInput ? (
            <ActionButton
              label={action.label}
              icon={icon}
              onClick={() => {
                setRerouteDepartmentId('');
                setRerouteRationale('');
                setShowRerouteInput(true);
              }}
              disabled={actionLoading}
              available
              variant={btnVariant}
            />
          ) : (
            <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-3 space-y-3">
              <div className="space-y-1">
                <label htmlFor="reroute-department" className="text-xs font-bold text-slate-600">
                  Reassign department
                </label>
                <select
                  id="reroute-department"
                  value={rerouteDepartmentId}
                  onChange={(e) => setRerouteDepartmentId(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                >
                  <option value="">Select a department...</option>
                  {availableDepartments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label htmlFor="reroute-rationale" className="text-xs font-bold text-slate-600">
                  Rationale
                </label>
                <textarea
                  id="reroute-rationale"
                  value={rerouteRationale}
                  onChange={(e) => setRerouteRationale(e.target.value)}
                  placeholder="Explain why the document should be reassigned..."
                  rows={3}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={actionLoading || !rerouteDepartmentId}
                  onClick={() => {
                    handleAction('reroute', {
                      department_id: rerouteDepartmentId,
                      rationale: rerouteRationale.trim(),
                    });
                    setRerouteDepartmentId('');
                    setRerouteRationale('');
                    setShowRerouteInput(false);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {actionLoading ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Confirm reroute
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowRerouteInput(false);
                    setRerouteDepartmentId('');
                    setRerouteRationale('');
                  }}
                  className="px-3 py-2 text-slate-500 hover:text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      );
    }
    return (
      <DisabledActionWrapper key={action.id} reason={reason}>
        <ActionButton label={action.label} icon={icon} onClick={() => {}} disabled available={false} variant={btnVariant} />
      </DisabledActionWrapper>
    );
  }

  if (action.id === 'request-consultation') {
    if (isAvailable) {
      return (
        <div key={action.id} className="space-y-2">
          {!showConsultInput ? (
            <ActionButton
              label={action.label}
              icon={icon}
              onClick={() => setShowConsultInput(true)}
              disabled={actionLoading}
              available
              variant={btnVariant}
            />
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3 space-y-2">
              <textarea
                value={consultBody}
                onChange={(e) => setConsultBody(e.target.value)}
                placeholder="Describe what you need consulted on..."
                rows={3}
                className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500 outline-none resize-none"
              />
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={actionLoading || !consultBody.trim()}
                  onClick={() => {
                    handleAction('request-consultation', { target_role: 'consultant', body: consultBody });
                    setConsultBody('');
                    setShowConsultInput(false);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-xl font-bold text-sm hover:bg-amber-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {actionLoading ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
                  Send
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowConsultInput(false);
                    setConsultBody('');
                  }}
                  className="px-3 py-2 text-slate-500 hover:text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      );
    }
    return (
      <DisabledActionWrapper key={action.id} reason={reason}>
        <ActionButton label={action.label} icon={icon} onClick={() => {}} disabled available={false} variant={btnVariant} />
      </DisabledActionWrapper>
    );
  }

  if (action.id === 'resolve-consultation') {
    return (
      <DisabledActionWrapper key={action.id} reason={!isAvailable ? reason : null}>
        <ActionButton
          label={action.label}
          icon={icon}
          onClick={() => {
            const unresolved = doc.consultation_notes.filter((n) => n.resolved_at === null);
            const mostRecent = unresolved[unresolved.length - 1];
            if (mostRecent) {
              handleAction('resolve-consultation', { note_id: mostRecent.id });
            }
          }}
          disabled={actionLoading || !isAvailable}
          available={isAvailable}
          variant={btnVariant}
        />
      </DisabledActionWrapper>
    );
  }

  return (
    <DisabledActionWrapper key={action.id} reason={!isAvailable ? reason : null}>
      <ActionButton
        label={action.label}
        icon={icon}
        onClick={() => handleAction(action.id)}
        disabled={actionLoading || !isAvailable}
        available={isAvailable}
        variant={btnVariant}
      />
    </DisabledActionWrapper>
  );
}

function DisabledActionsDisclosure({
  disabled,
  getActionIcon,
}: {
  disabled: Array<{ action: { id: string; label: string; variant: 'default' | 'success' | 'caution' | 'destructive' }; reason: string }>;
  getActionIcon: (id: string) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 text-xs font-bold text-slate-500 hover:text-slate-700 transition"
        data-testid="workflow-disabled-toggle"
      >
        <span className="flex items-center gap-1">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          Actions not available right now ({disabled.length})
        </span>
      </button>
      {open && (
        <ul className="mt-3 space-y-2" data-testid="workflow-disabled-list">
          {disabled.map(({ action, reason }) => (
            <li
              key={action.id}
              className="flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2"
            >
              <div className="mt-0.5 shrink-0 text-slate-400">{getActionIcon(action.id)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-slate-600">{action.label}</p>
                <p className="text-[11px] text-slate-500">{reason}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TerminalStateCard({ status }: { status: string }) {
  const config: Record<string, { icon: React.ReactNode; tone: string; label: string }> = {
    closed: {
      icon: <CheckCircle2 size={20} className="text-slate-500" />,
      tone: 'border-slate-200 bg-slate-50',
      label: 'Closed',
    },
    out_of_scope: {
      icon: <XCircle size={20} className="text-slate-500" />,
      tone: 'border-slate-200 bg-slate-50',
      label: 'Out of Scope',
    },
    ingest_failed: {
      icon: <AlertCircle size={20} className="text-red-500" />,
      tone: 'border-red-200 bg-red-50/60',
      label: 'Ingest Failed',
    },
    analysis_failed: {
      icon: <AlertTriangle size={20} className="text-amber-600" />,
      tone: 'border-amber-200 bg-amber-50/60',
      label: 'Analysis Failed',
    },
  };

  const c = config[status] ?? {
    icon: <Info size={20} className="text-slate-500" />,
    tone: 'border-slate-200 bg-slate-50',
    label: status.replace(/_/g, ' '),
  };

  return (
    <div className={`rounded-xl border p-4 flex items-start gap-3 ${c.tone}`}>
      <div className="shrink-0 mt-0.5">{c.icon}</div>
      <div className="space-y-0.5">
        <p className="text-sm font-bold text-slate-700 capitalize">{c.label}</p>
        <p className="text-xs text-slate-500">No further workflow actions available.</p>
      </div>
    </div>
  );
}
