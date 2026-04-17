'use client';

import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Badge } from '@/components/ui-badge';
import { BarChart3, PieChart, TrendingUp, Users, FileCheck, Layers } from 'lucide-react';
import { fetchApi } from '@/lib/api';

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    fetchApi('/dashboard/stats').then(setMetrics).catch(console.error);
  }, []);

  const stats = [
    { label: 'Total Received', value: metrics?.total_received || '...', icon: <Layers className="text-blue-600" />, trend: '+12%' },
    { label: 'Pending Review', value: metrics?.pending_review || '...', icon: <TrendingUp className="text-orange-600" />, trend: '-5%' },
    { label: 'Consultations', value: metrics?.under_consultation || '...', icon: <Users className="text-purple-600" />, trend: '+2%' },
    { label: 'Closed Today', value: metrics?.closed_today || '...', icon: <FileCheck className="text-emerald-600" />, trend: '+18%' },
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
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 bg-slate-50 rounded-xl flex items-center justify-center">
                  {stat.icon}
                </div>
                <span className={`text-xs font-bold ${stat.trend.startsWith('+') ? 'text-emerald-600' : 'text-red-600'}`}>
                  {stat.trend}
                </span>
              </div>
              <div className="mt-4">
                <p className="text-sm font-bold text-slate-400 uppercase tracking-wider">{stat.label}</p>
                <p className="text-2xl font-black text-slate-900">{stat.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 size={18} /> Processing Volume by Type
            </CardTitle>
          </CardHeader>
          <CardContent className="h-64 flex items-center justify-center text-slate-400 bg-slate-50/50 rounded-xl m-6 border border-dashed border-slate-200">
            [D3 Visualization Placeholder]
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PieChart size={18} /> Departmental Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="h-64 flex items-center justify-center text-slate-400 bg-slate-50/50 rounded-xl m-6 border border-dashed border-slate-200">
            [Recharts Visualization Placeholder]
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
