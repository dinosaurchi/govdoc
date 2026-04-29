import { useRole } from '@/hooks/use-role';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { ArrowRight, CheckCircle2, Clock, AlertCircle, FileUp, ListChecks, MessageSquare, LayoutDashboard, Database, Loader2, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { apiGet, apiPost } from '@/lib/api';

type DemoScenario = {
  id: string;
  name: string;
  description: string | null;
  document_id: string | null;
  category: string | null;
};

type DemoResetResponse = {
  message: string;
  documents: Array<{ id: string; title: string; status: string }>;
};

export default function HomePage() {
  const { role } = useRole();
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);

  const fetchScenarios = async () => {
    try {
      const next = await apiGet<DemoScenario[]>('/demo/scenarios');
      setScenarios(next);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    void (async () => {
      try {
        const next = await apiGet<DemoScenario[]>('/demo/scenarios');
        setScenarios(next);
      } catch (err) {
        console.error(err);
      }
    })();
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await apiPost<DemoResetResponse>('/demo/reset');
      setSeedResult(res.message || 'Demo data reset successfully.');
      await fetchScenarios();
      setTimeout(() => setSeedResult(null), 5000);
    } catch (err: unknown) {
      setSeedResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <section className="text-center max-w-2xl mx-auto space-y-4">
        <Badge variant="outline" className="px-3 py-1 border-blue-200 text-blue-700 bg-blue-50">Public Sector MVP</Badge>
        <h1 className="text-5xl font-black tracking-tighter text-slate-900">
          GovDoc <span className="text-blue-700">SecureFlow</span>
        </h1>
        <p className="text-xl text-slate-600 font-medium">
          Automated document intake, AI-driven triage, and secure administrative workflow for government departments.
        </p>
        <div className="pt-4 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="px-6 py-2 bg-slate-100 border border-slate-200 rounded-xl text-xs font-bold uppercase tracking-widest text-slate-600 hover:bg-slate-200 transition flex items-center gap-2"
          >
            {seeding ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
            Reset Demo Data
          </button>
          <Link
            to="/dashboard#demo-walkthrough"
            className="px-6 py-2 bg-blue-50 border border-blue-200 rounded-xl text-xs font-bold uppercase tracking-widest text-blue-700 hover:bg-blue-100 transition flex items-center gap-2"
          >
            <Sparkles size={14} />
            Demo walkthrough
          </Link>
          {seedResult && <span className="w-full text-center text-[10px] font-bold text-blue-600 animate-in fade-in sm:w-auto">{seedResult}</span>}
        </div>
      </section>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <RoleActionCard
          roleName="Intake Clerk"
          activeRole={role}
          title="Document Intake"
          description="Receive and classify incoming documents (công văn, tờ trình...)"
          to="/intake"
          icon={<FileUp className="w-8 h-8 text-blue-500" />}
        />
        <RoleActionCard
          roleName="Department Reviewer"
          activeRole={role}
          title="Workflow Review"
          description="Validate AI routing suggestions and assign documents to departments."
          to="/review"
          icon={<ListChecks className="w-8 h-8 text-orange-500" />}
        />
        <RoleActionCard
          roleName="Consultant"
          activeRole={role}
          title="Internal Consultation"
          description="Provide expert opinions on cross-departmental requests."
          to="/consultation"
          icon={<MessageSquare className="w-8 h-8 text-purple-500" />}
        />
        <RoleActionCard
          roleName="Supervisor"
          activeRole={role}
          title="Final Oversight"
          description="Approve prepared responses and monitor overall system metrics."
          to="/dashboard"
          icon={<LayoutDashboard className="w-8 h-8 text-emerald-500" />}
        />
      </div>

      <div className="grid md:grid-cols-3 gap-6 pt-12">
        <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
          <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
            <CheckCircle2 className="text-blue-600" size={20} />
          </div>
          <h3 className="font-bold text-lg">Multi-Role Access</h3>
          <p className="text-sm text-slate-500">Separated concerns for intake, review, and consultation with purpose-built views for each stage.</p>
        </div>
        <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
          <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center">
            <Clock className="text-purple-600" size={20} />
          </div>
          <h3 className="font-bold text-lg">State Machine Flow</h3>
          <p className="text-sm text-slate-500">Robust document lifecycle management from intake_received through to archived_demo_only.</p>
        </div>
        <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
          <div className="w-10 h-10 bg-orange-50 rounded-xl flex items-center justify-center">
            <AlertCircle className="text-orange-600" size={20} />
          </div>
          <h3 className="font-bold text-lg">AI Integration Ready</h3>
          <p className="text-sm text-slate-500">Scaffolded adapter layer for Qwen-powered summaries, entity extraction, and routing suggestions.</p>
        </div>
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">Seeded demo scenarios</h2>
            <p className="text-sm text-slate-500">Prebuilt records for the hero, ambiguity, scan, and out-of-scope flows.</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {scenarios.length === 0 ? (
            <div className="col-span-full rounded-2xl border border-dashed border-slate-200 bg-white p-6 text-sm text-slate-500">
              No demo scenarios are loaded. Use <span className="font-semibold text-slate-700">Reset Demo Data</span> to rebuild them.
            </div>
          ) : (
            scenarios.map((scenario) => (
              <Card key={scenario.id} className="border-slate-200 bg-white">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-base leading-snug">{scenario.name}</CardTitle>
                    {scenario.category && (
                      <Badge variant="outline" className="uppercase text-[10px] tracking-widest">
                        {scenario.category.replace(/_/g, ' ')}
                      </Badge>
                    )}
                  </div>
                  {scenario.description && (
                    <CardDescription className="text-sm leading-relaxed">{scenario.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="pt-0">
                  {scenario.document_id ? (
                    <Link
                      to={`/documents/${scenario.document_id}`}
                      className="inline-flex items-center gap-2 text-sm font-bold text-blue-700 hover:text-blue-800"
                    >
                      Open scenario
                      <ArrowRight size={14} />
                    </Link>
                  ) : (
                    <p className="text-sm text-slate-400 italic">Scenario record is missing its document link.</p>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function RoleActionCard({
  roleName,
  activeRole,
  title,
  description,
  to,
  icon,
}: {
  roleName: string;
  activeRole: string;
  title: string;
  description: string;
  to: string;
  icon: React.ReactNode;
}) {
  const isMatch = roleName === activeRole;

  return (
    <Link to={to}>
      <Card className={`h-full border-2 transition-all hover:scale-[1.02] cursor-pointer ${isMatch ? 'border-blue-500 shadow-md ring-4 ring-blue-50 shadow-blue-100' : 'border-slate-100'}`}>
        <CardHeader className="pb-2">
          <div className="mb-4">{icon}</div>
          <CardTitle className="text-lg">{title}</CardTitle>
          <CardDescription className="text-xs font-medium uppercase tracking-wider">{roleName}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-500 leading-relaxed">{description}</p>
          <div className={`flex items-center gap-2 text-xs font-bold ${isMatch ? 'text-blue-600' : 'text-slate-400'}`}>
            Explore View <ArrowRight size={14} />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
