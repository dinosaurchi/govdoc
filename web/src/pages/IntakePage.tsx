import { useRole } from '@/hooks/use-role';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Upload, Info, CheckCircle2, Loader2 } from 'lucide-react';
import { useRef, useState } from 'react';
import { uploadDocument } from '@/lib/api';

export default function IntakePage() {
  const { role } = useRole();
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canIntake = role === 'Intake Clerk' || role === 'Supervisor';

  const handleFile = async (file: File) => {
    if (!canIntake) return;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await uploadDocument(file, role);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = '';
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
          <p className="text-sm font-medium">File uploaded, text extracted, and AI analysis completed. Open Review queue to continue.</p>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardContent className="p-8 space-y-6">
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void handleFile(f);
              }}
            />

            <button
              type="button"
              disabled={!canIntake || loading}
              onClick={() => inputRef.current?.click()}
              className={`w-full border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center space-y-4 transition-colors ${
                canIntake && !loading
                  ? 'border-slate-200 hover:border-blue-400 cursor-pointer bg-slate-50'
                  : 'border-slate-100 bg-slate-50/50 cursor-not-allowed opacity-50'
              }`}
            >
              <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center">
                {loading ? <Loader2 className="animate-spin text-blue-600" size={32} /> : <Upload className="text-blue-600" size={32} />}
              </div>
              <div className="text-center">
                <p className="font-bold text-lg">{loading ? 'Uploading and analyzing…' : 'Choose file to upload'}</p>
                <p className="text-sm text-slate-500">PDF, DOC/DOCX, or plain text — validated on the server (fail-fast).</p>
              </div>
            </button>
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
              <p className="font-bold text-slate-900">2. Upload &amp; Classify</p>
              <p>Text extraction and AI classification (doc type, urgency, department) run automatically on upload.</p>
            </div>
            <div className="space-y-2">
              <p className="font-bold text-slate-900">3. Review AI Output</p>
              <p>Open the Review queue to validate AI routing suggestions and take workflow actions.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
