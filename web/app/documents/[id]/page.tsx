'use client';

import { useEffect, useState, use } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { 
  ArrowLeft, 
  Clock, 
  MessageSquare, 
  CheckCircle2, 
  Send, 
  User, 
  Building,
  Loader2,
  BrainCircuit,
  History,
  FileText
} from 'lucide-react';
import Link from 'next/link';
import { fetchApi } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { role } = useRole();
  const [doc, setDoc] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDoc = async () => {
    try {
      const data = await fetchApi(`/documents/${id}`);
      setDoc(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoc();
  }, [id]);

  const handleAction = async (action: string, payload: any = {}) => {
    setActionLoading(true);
    try {
      if (action === 'route') {
        await fetchApi(`/review/${id}/route?target_dept_id=1&note=${payload.note || 'Routed via UI'}`, {
          method: 'POST'
        });
      } else if (action === 'approve') {
        await fetchApi(`/review/${id}/approve`, { method: 'POST' });
      } else if (action === 'analyze') {
        // Trigger backend mock analysis
        await fetchApi(`/documents/${id}/analyze`, { method: 'POST' });
      }
      await fetchDoc();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="h-96 flex items-center justify-center"><Loader2 className="animate-spin text-blue-600" size={48} /></div>;
  if (error || !doc) return <div className="p-8 text-center text-red-600 font-bold">{error || 'Document not found'}</div>;

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-20 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <Link href="/review" className="p-2 hover:bg-slate-100 rounded-full transition">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <div className="flex items-center gap-2">
             <h1 className="text-2xl font-black tracking-tight text-slate-900">{doc.title}</h1>
             <Badge variant="outline" className="uppercase text-[10px] font-black">{doc.doc_type}</Badge>
          </div>
          <p className="text-slate-500 text-sm font-medium">Created: {new Date(doc.created_at).toLocaleString('vi-VN')}</p>
        </div>
        <div className="ml-auto">
          <Badge className="px-4 py-1 text-sm font-bold capitalize">
            {doc.state.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-blue-100 bg-blue-50/30 overflow-hidden">
            <CardHeader className="bg-blue-50/50 border-b border-blue-100 pb-3">
              <CardTitle className="text-base flex items-center gap-2 text-blue-800">
                <BrainCircuit size={18} /> AI Analysis Suggestions
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {doc.analysis ? (
                <div className="grid md:grid-cols-2 gap-6">
                   <div className="space-y-4">
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
                           {[1, 2, 3, 4, 5].map(v => (
                             <div key={v} className={`h-1.5 w-8 rounded-full ${v <= doc.analysis.urgency_score ? 'bg-orange-500' : 'bg-slate-200'}`} />
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
                   <p className="text-slate-500 text-sm font-medium">No active AI analysis for this document version.</p>
                   <button 
                     disabled={actionLoading}
                     onClick={() => handleAction('analyze')}
                     className="px-6 py-2 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-700 flex items-center gap-2 mx-auto disabled:opacity-50"
                   >
                     {actionLoading ? <Loader2 className="animate-spin" size={16} /> : <BrainCircuit size={16} />}
                     Run Gemini Analysis
                   </button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare size={18} className="text-purple-600" /> Consultation Thread
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {doc.consultations.length > 0 ? (
                doc.consultations.map((note: any) => (
                  <div key={note.id} className="flex gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center shrink-0 border border-slate-200 shadow-sm">
                      <User size={18} className="text-slate-400" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">Role ID: {note.author_role_id}</span>
                        <span className="text-[10px] text-slate-400">{new Date(note.created_at).toLocaleTimeString('vi-VN')}</span>
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed">{note.content}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-slate-400">
                   <p className="text-sm font-medium italic">No consultation notes registered.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 size={18} className="text-emerald-600" /> Workflow Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <ActionButton 
                label="Assign/Route to Dept" 
                icon={<Send size={16} />} 
                onClick={() => handleAction('route')}
                disabled={actionLoading || doc.state === 'closed'}
                active={role === 'Intake Clerk' || role === 'Supervisor'}
              />
              <ActionButton 
                label="Request Consultation" 
                icon={<MessageSquare size={16} />} 
                onClick={() => {}}
                disabled={actionLoading || doc.state === 'closed'}
                active={role === 'Department Reviewer' || role === 'Supervisor'}
              />
              <ActionButton 
                label="Approve & Dispatch" 
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
                <History size={18} className="text-slate-600" /> Decision History
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {doc.decisions.map((dec: any) => (
                <div key={dec.id} className="text-sm border-l-2 border-slate-200 pl-4 py-1 space-y-1">
                  <p className="font-bold text-slate-900">Routed to Dept ID: {dec.target_department_id}</p>
                  <p className="text-xs text-slate-500 italic">&quot;{dec.note || 'No note provided'}&quot;</p>
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
  variant = 'blue' 
}: { 
  label: string; 
  icon: React.ReactNode; 
  onClick: () => void; 
  disabled: boolean; 
  active: boolean;
  variant?: 'blue' | 'emerald' | 'purple'
}) {
  if (!active) return null;
  
  const colors = {
    blue: 'bg-blue-600 hover:bg-blue-700',
    emerald: 'bg-emerald-600 hover:bg-emerald-700',
    purple: 'bg-purple-600 hover:bg-purple-700'
  };

  return (
    <button 
      disabled={disabled}
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-4 py-3 rounded-xl text-white font-bold text-sm transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed ${colors[variant]}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
