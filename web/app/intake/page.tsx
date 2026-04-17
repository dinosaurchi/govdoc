'use client';

import { useRole } from '@/hooks/use-role';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { FileUp, Upload, Info, CheckCircle2, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { fetchApi } from '@/lib/api';

export default function IntakePage() {
  const { role } = useRole();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canIntake = role === 'Intake Clerk' || role === 'Supervisor';

  const handleSimulateUpload = async () => {
    if (!canIntake) return;
    
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await fetchApi('/documents', {
        method: 'POST',
        body: JSON.stringify({
          title: `Document ${new Date().toLocaleString('vi-VN')}`,
          doc_type: 'công văn'
        })
      });
      setSuccess(true);
      // Reset after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to register document');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Document Intake</h1>
          <p className="text-slate-500">Upload and register new administrative documents.</p>
        </div>
      </div>

      {!canIntake && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-800">
          <Info className="shrink-0 mt-0.5" size={18} />
          <div className="text-sm">
            <p className="font-bold">Restricted Access</p>
            <p>Your current role ({role}) does not have permission to register new documents. Please switch to &quot;Intake Clerk&quot; to perform this action.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3 text-red-800">
           <Info className="shrink-0 mt-0.5" size={18} />
           <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3 text-emerald-800">
           <CheckCircle2 className="shrink-0 mt-0.5" size={18} />
           <p className="text-sm font-medium">Document registered successfully and entering triage.</p>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardContent className="p-12">
            <div 
              onClick={handleSimulateUpload}
              className={`border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center space-y-4 transition-colors ${canIntake && !loading ? 'border-slate-200 hover:border-blue-400 cursor-pointer bg-slate-50' : 'border-slate-100 bg-slate-50/50 cursor-not-allowed opacity-50'}`}
            >
              <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center">
                {loading ? <Loader2 className="animate-spin text-blue-600" size={32} /> : <Upload className="text-blue-600" size={32} />}
              </div>
              <div className="text-center">
                <p className="font-bold text-lg">{loading ? 'Processing...' : 'Click to simulate intake upload'}</p>
                <p className="text-sm text-slate-500">Document registry will be created immediately.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Intake Guidelines</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-slate-600">
            <div className="space-y-2">
              <p className="font-bold text-slate-900">1. Verify Origin</p>
              <p>Ensure the document is from an authorized sender or department.</p>
            </div>
            <div className="space-y-2">
              <p className="font-bold text-slate-900">2. Classify Type</p>
              <p>Identify if it is a Công văn, Quyết định, or Thông báo.</p>
            </div>
            <div className="space-y-2">
              <p className="font-bold text-slate-900">3. Initial Triage</p>
              <p>AI will suggest a triage priority, but Intake Clerks must verify.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
