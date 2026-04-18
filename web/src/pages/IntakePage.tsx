import { useRole } from '@/hooks/use-role';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import {
  Upload,
  Info,
  CheckCircle2,
  Loader2,
  Circle,
  FileCheck2,
  ScanText,
  BrainCircuit,
  ArrowRight,
  ListChecks,
  Download,
  FileText,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { uploadDocument } from '@/lib/api';
import { DEMO_SAMPLE_FILES, demoSampleFileUrl } from '@/lib/demo-samples';

// ---------------------------------------------------------------------------
// Stepper model
// ---------------------------------------------------------------------------

type StepId = 'upload' | 'validate' | 'extract' | 'analyze' | 'done';
type StepStatus = 'pending' | 'active' | 'done' | 'error';

type StepDefinition = {
  id: StepId;
  label: string;
  detail: string;
  icon: React.ReactNode;
};

const STEPS: StepDefinition[] = [
  {
    id: 'upload',
    label: 'Uploading file',
    detail: 'Sending bytes to the SecureFlow API over HTTPS.',
    icon: <Upload size={16} />,
  },
  {
    id: 'validate',
    label: 'Validating & storing',
    detail: 'Checking MIME type, size and deduping by SHA-256 checksum.',
    icon: <FileCheck2 size={16} />,
  },
  {
    id: 'extract',
    label: 'Extracting text',
    detail: 'Parsing the document body (PDF/DOCX/TXT).',
    icon: <ScanText size={16} />,
  },
  {
    id: 'analyze',
    label: 'AI classification & routing',
    detail: 'Determining type, urgency, department and routing suggestions.',
    icon: <BrainCircuit size={16} />,
  },
];

type UploadResponse = {
  document: { id: string; title: string; status: string };
  extracted_artifact?: { id: string } | null;
  ai_analyses?: Array<{ id: string }>;
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function IntakePage() {
  const { role } = useRole();
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<StepId | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());
  const [failedStep, setFailedStep] = useState<StepId | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canIntake = role === 'Intake Clerk' || role === 'Supervisor';

  // Advance through the "live" steps on a timer while the request is in flight.
  // We cannot observe the real server-side progress from a single POST, so we
  // pace through the first three steps at a realistic cadence and let the
  // final step ("analyze") settle when the response arrives. This is better
  // UX than a featureless spinner.
  useEffect(() => {
    if (!loading) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    // Stage transitions; kept conservative so even fast uploads feel like steps.
    timers.push(setTimeout(() => advanceTo('validate'), 600));
    timers.push(setTimeout(() => advanceTo('extract'), 1800));
    timers.push(setTimeout(() => advanceTo('analyze'), 3600));

    return () => {
      for (const t of timers) clearTimeout(t);
    };
  }, [loading]);

  const advanceTo = (next: StepId) => {
    setCurrentStep((prev) => {
      if (!prev) return next;
      // Mark prior as done when we advance.
      setCompletedSteps((set) => {
        const nextSet = new Set(set);
        nextSet.add(prev);
        return nextSet;
      });
      return next;
    });
  };

  const resetStepper = () => {
    setCurrentStep(null);
    setCompletedSteps(new Set());
    setFailedStep(null);
  };

  const handleFile = async (file: File) => {
    if (!canIntake) return;

    setLoading(true);
    setError(null);
    setResult(null);
    resetStepper();
    setCurrentStep('upload');

    try {
      const response = await uploadDocument<UploadResponse>(file, role);

      // Mark everything through "analyze" as done based on what came back.
      setCompletedSteps(() => {
        const done = new Set<StepId>(['upload', 'validate']);
        if (response.extracted_artifact) done.add('extract');
        if (response.ai_analyses && response.ai_analyses.length > 0) {
          done.add('analyze');
        }
        return done;
      });
      setCurrentStep('done');
      setResult(response);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      setFailedStep(currentStep);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleDismiss = () => {
    setResult(null);
    resetStepper();
  };

  const success = result !== null && !loading && !error;

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
          <div className="text-sm flex-1">
            <p className="font-bold">Upload failed</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {success && result && (
        <div
          className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-start gap-4 text-emerald-900"
          data-testid="intake-success"
        >
          <CheckCircle2 className="shrink-0 mt-0.5 text-emerald-600" size={22} />
          <div className="flex-1 space-y-3">
            <div>
              <p className="font-bold">Document registered</p>
              <p className="text-sm text-emerald-800/90">
                File uploaded, text extracted, and AI analysis completed for
                {' '}
                <span className="font-semibold">{result.document.title}</span>.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                to={`/documents/${result.document.id}`}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-xl font-bold text-sm hover:bg-emerald-700 transition shadow-sm"
                data-testid="intake-open-case"
              >
                Open review case
                <ArrowRight size={16} />
              </Link>
              <Link
                to="/review"
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-emerald-200 text-emerald-800 rounded-xl font-bold text-sm hover:bg-emerald-50 transition"
              >
                <ListChecks size={16} />
                View review queue
              </Link>
              <button
                type="button"
                onClick={handleDismiss}
                className="px-3 py-2 text-emerald-800/70 hover:text-emerald-900 text-sm font-medium"
              >
                Upload another
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid items-stretch gap-6 lg:grid-cols-3">
        <Card className="flex min-h-0 flex-col lg:col-span-2">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Upload document</CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-6">
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
              className={`flex min-h-[260px] w-full flex-1 flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-10 transition-colors ${
                canIntake && !loading
                  ? 'cursor-pointer border-slate-200 bg-slate-50 hover:border-blue-400'
                  : 'cursor-not-allowed border-slate-100 bg-slate-50/50 opacity-50'
              }`}
            >
              <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center">
                {loading ? (
                  <Loader2 className="animate-spin text-blue-600" size={32} />
                ) : (
                  <Upload className="text-blue-600" size={32} />
                )}
              </div>
              <div className="text-center">
                <p className="font-bold text-lg">
                  {loading ? 'Processing upload…' : 'Choose file to upload'}
                </p>
                <p className="text-sm text-slate-500">
                  PDF, DOC/DOCX, or plain text — validated on the server (fail-fast).
                </p>
              </div>
            </button>

            {(loading || success) && (
              <ProcessingStepper
                currentStep={currentStep}
                completedSteps={completedSteps}
                failedStep={failedStep}
              />
            )}
          </CardContent>
        </Card>

        <div className="flex min-h-0 flex-col gap-6">
          <Card id="demo-samples" className="flex min-h-0 flex-col scroll-mt-24">
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Demo sample files</CardTitle>
              <p className="text-xs font-medium text-slate-500">
                PDFs below match files under <code className="rounded bg-slate-100 px-1 py-0.5">./data/incoming/</code> in the
                full data pack; they are bundled here for one-click demos.
              </p>
            </CardHeader>
            <CardContent className="flex-1 space-y-3 text-sm">
              <ul className="space-y-3">
                {DEMO_SAMPLE_FILES.map((f) => (
                  <li key={f.filename} className="rounded-xl border border-slate-200 bg-slate-50/80 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2 font-semibold text-slate-900">
                          <FileText className="h-4 w-4 shrink-0 text-red-600" aria-hidden />
                          <span className="truncate">{f.title}</span>
                        </div>
                        <p className="text-xs text-slate-600">{f.description}</p>
                        <p className="text-[11px] text-slate-400">
                          <span className="font-medium text-slate-500">Source in data pack:</span> {f.dataPackSource}
                        </p>
                      </div>
                      <a
                        href={demoSampleFileUrl(f.filename)}
                        download={f.filename}
                        className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-bold text-white hover:bg-blue-700"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Get
                      </a>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="flex min-h-0 flex-col">
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Intake Guidelines</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 space-y-4 text-sm text-slate-600">
              <div className="space-y-1">
                <p className="font-bold text-slate-900">1. Verify Origin</p>
                <p>Ensure the document is from an authorized sender or department.</p>
              </div>
              <div className="space-y-1">
                <p className="font-bold text-slate-900">2. Upload &amp; Classify</p>
                <p>
                  Text extraction and AI classification (doc type, urgency, department) run
                  automatically on upload.
                </p>
              </div>
              <div className="space-y-1">
                <p className="font-bold text-slate-900">3. Review AI Output</p>
                <p>
                  Open the Review queue to validate AI routing suggestions and take workflow
                  actions.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stepper component
// ---------------------------------------------------------------------------

function ProcessingStepper({
  currentStep,
  completedSteps,
  failedStep,
}: {
  currentStep: StepId | null;
  completedSteps: Set<StepId>;
  failedStep: StepId | null;
}) {
  return (
    <ol
      className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-5"
      data-testid="intake-stepper"
    >
      {STEPS.map((step) => {
        const status = resolveStatus(step.id, currentStep, completedSteps, failedStep);
        return <StepperRow key={step.id} step={step} status={status} />;
      })}
    </ol>
  );
}

function StepperRow({ step, status }: { step: StepDefinition; status: StepStatus }) {
  const palette = {
    pending: {
      icon: <Circle size={18} className="text-slate-300" />,
      label: 'text-slate-500',
      detail: 'text-slate-400',
    },
    active: {
      icon: <Loader2 size={18} className="animate-spin text-blue-600" />,
      label: 'text-blue-800 font-bold',
      detail: 'text-blue-700',
    },
    done: {
      icon: <CheckCircle2 size={18} className="text-emerald-600" />,
      label: 'text-slate-800 font-bold',
      detail: 'text-slate-500',
    },
    error: {
      icon: <Info size={18} className="text-red-600" />,
      label: 'text-red-800 font-bold',
      detail: 'text-red-700',
    },
  }[status];

  return (
    <li
      className="flex items-start gap-3"
      data-testid={`intake-step-${step.id}`}
      data-status={status}
    >
      <div className="mt-0.5 shrink-0">{palette.icon}</div>
      <div className="flex-1 space-y-0.5">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">{step.icon}</span>
          <p className={`text-sm ${palette.label}`}>{step.label}</p>
        </div>
        <p className={`text-xs ${palette.detail}`}>{step.detail}</p>
      </div>
    </li>
  );
}

function resolveStatus(
  id: StepId,
  currentStep: StepId | null,
  completedSteps: Set<StepId>,
  failedStep: StepId | null,
): StepStatus {
  if (failedStep === id) return 'error';
  if (completedSteps.has(id)) return 'done';
  if (currentStep === id) return 'active';
  return 'pending';
}
