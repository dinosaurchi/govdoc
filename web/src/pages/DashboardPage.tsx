import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { BarChart3, PieChart, TrendingUp, Users, FileCheck, Layers } from 'lucide-react';
import { apiGet } from '@/lib/api';
import { useRole } from '@/hooks/use-role';

type DashboardMetrics = {
  total_received: number;
  pending_review: number;
  under_consultation: number;
  closed_today: number;
};

type DocumentListItem = {
  id: string;
  status: string;
  assigned_department_id: string | null;
};

type ChartDatum = {
  label: string;
  value: number;
  color: string;
};

const STATUS_META: Array<{ key: string; label: string; color: string }> = [
  { key: 'received', label: 'Received', color: '#94a3b8' },
  { key: 'analyzed', label: 'Analyzed', color: '#3b82f6' },
  { key: 'under_review', label: 'Under Review', color: '#f59e0b' },
  { key: 'in_consultation', label: 'Consultation', color: '#8b5cf6' },
  { key: 'closed', label: 'Closed', color: '#10b981' },
  { key: 'out_of_scope', label: 'Out of Scope', color: '#64748b' },
];

const DEPARTMENT_LABELS: Record<string, string> = {
  phong_hanh_chinh: 'Hanh chinh',
  phong_ke_hoach: 'Ke hoach',
  phong_tai_chinh: 'Tai chinh',
  phong_phap_che: 'Phap che',
  phong_ke_hoach_dau_tu: 'KH dau tu',
};

const DEPARTMENT_COLORS = ['#2563eb', '#f59e0b', '#8b5cf6', '#10b981', '#ef4444', '#0f172a'];

export default function DashboardPage() {
  const { role } = useRole();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [statusChart, setStatusChart] = useState<ChartDatum[]>([]);
  const [departmentChart, setDepartmentChart] = useState<ChartDatum[]>([]);

  useEffect(() => {
    let active = true;

    (async () => {
      try {
        const nextMetrics = await apiGet<DashboardMetrics>('/dashboard/stats', role);
        const docs = await apiGet<DocumentListItem[]>('/documents/', role);

        if (!active) return;

        setMetrics(nextMetrics);
        setStatusChart(buildStatusChart(docs));
        setDepartmentChart(buildDepartmentChart(docs));
      } catch (err) {
        console.error(err);
      }
    })();

    return () => {
      active = false;
    };
  }, [role]);

  const stats = [
    { label: 'Total Received', value: metrics?.total_received ?? '...', icon: <Layers className="text-blue-600" />, trend: '+12%' },
    { label: 'Pending Review', value: metrics?.pending_review ?? '...', icon: <TrendingUp className="text-orange-600" />, trend: '-5%' },
    { label: 'Consultations', value: metrics?.under_consultation ?? '...', icon: <Users className="text-purple-600" />, trend: '+2%' },
    { label: 'Closed Today', value: metrics?.closed_today ?? '...', icon: <FileCheck className="text-emerald-600" />, trend: '+18%' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Dashboard</h1>
          <p className="text-slate-500">Real-time metrics for GovDoc SecureFlow.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="h-full">
            <CardContent className="p-5 flex flex-col h-full gap-4">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 bg-slate-50 rounded-xl flex items-center justify-center shrink-0">
                  {stat.icon}
                </div>
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                    stat.trend.startsWith('+')
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-red-50 text-red-700'
                  }`}
                >
                  {stat.trend}
                </span>
              </div>
              <div className="mt-auto">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider leading-snug min-h-[1.25rem]">
                  {stat.label}
                </p>
                <p className="text-2xl font-black text-slate-900 leading-none mt-1">
                  {stat.value}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 items-stretch">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 size={18} /> Processing Volume by Workflow Stage
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-6 pb-6">
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 h-full">
              <StatusBars data={statusChart} />
            </div>
          </CardContent>
        </Card>
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PieChart size={18} /> Departmental Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 px-6 pb-6">
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-6 h-full">
              <DepartmentDonut data={departmentChart} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function buildStatusChart(docs: DocumentListItem[]): ChartDatum[] {
  const counts = new Map<string, number>();
  for (const doc of docs) {
    counts.set(doc.status, (counts.get(doc.status) ?? 0) + 1);
  }

  return STATUS_META.map((item) => ({
    label: item.label,
    value: counts.get(item.key) ?? 0,
    color: item.color,
  })).filter((item) => item.value > 0);
}

function buildDepartmentChart(docs: DocumentListItem[]): ChartDatum[] {
  const counts = new Map<string, number>();
  for (const doc of docs) {
    const key = doc.assigned_department_id ?? 'unassigned';
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([key, value], index) => ({
      label: key === 'unassigned' ? 'Unassigned' : (DEPARTMENT_LABELS[key] ?? key),
      value,
      color: DEPARTMENT_COLORS[index % DEPARTMENT_COLORS.length],
    }));
}

function StatusBars({ data }: { data: ChartDatum[] }) {
  if (data.length === 0) {
    return <EmptyChart message="No workflow activity yet." />;
  }

  const maxValue = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className="space-y-4">
      {data.map((item) => (
        <div key={item.label} className="space-y-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-slate-700 truncate">{item.label}</span>
            <span className="font-mono text-slate-500 tabular-nums shrink-0 pl-2">
              {item.value}
            </span>
          </div>
          <div className="h-3 rounded-full bg-white shadow-inner overflow-hidden">
            <div
              className="h-3 rounded-full transition-all"
              style={{
                width: `${(item.value / maxValue) * 100}%`,
                backgroundColor: item.color,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function DepartmentDonut({ data }: { data: ChartDatum[] }) {
  if (data.length === 0) {
    return <EmptyChart message="No departmental assignments yet." />;
  }

  const total = data.reduce((sum, item) => sum + item.value, 0);
  const gradient = buildConicGradient(data, total);

  return (
    <div className="flex min-h-[13rem] h-full items-center gap-6">
      <div
        className="relative flex h-36 w-36 shrink-0 items-center justify-center rounded-full"
        style={{ background: gradient }}
      >
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white text-center shadow-sm">
          <div className="leading-tight">
            <div className="text-2xl font-black text-slate-900">{total}</div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Docs
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-3 min-w-0">
        {data.map((item) => (
          <div
            key={item.label}
            className="flex items-center justify-between gap-3 text-sm min-w-0"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="h-3 w-3 rounded-full shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="font-semibold text-slate-700 truncate">{item.label}</span>
            </div>
            <span className="font-mono text-slate-500 tabular-nums shrink-0 w-10 text-right">
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function buildConicGradient(data: ChartDatum[], total: number): string {
  let offset = 0;
  const segments = data.map((item) => {
    const start = (offset / total) * 360;
    offset += item.value;
    const end = (offset / total) * 360;
    return `${item.color} ${start}deg ${end}deg`;
  });
  return `conic-gradient(${segments.join(', ')})`;
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-52 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white text-sm font-medium text-slate-400">
      {message}
    </div>
  );
}
