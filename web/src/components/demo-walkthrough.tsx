import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui-card';
import { Sparkles } from 'lucide-react';

/** Shown only on the dashboard — home links here via `/dashboard#demo-walkthrough`. */
export function DemoWalkthrough() {
  return (
    <Card
      id="demo-walkthrough"
      className="scroll-mt-24 border-blue-100 bg-gradient-to-br from-blue-50/80 to-white shadow-sm"
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-blue-600" />
          Demo walkthrough
        </CardTitle>
        <p className="text-xs font-medium text-slate-500">
          Downloadable <span className="font-semibold text-slate-600">PDF</span> samples (sourced from the same incoming
          corpus as <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px]">./data/incoming/</code>) are on{' '}
          <Link to="/intake#demo-samples" className="text-blue-700 underline-offset-2 hover:underline">
            Intake → Demo sample files
          </Link>
          . Your full local pack under <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px]">./data</code> may
          contain additional PDFs for stress tests (not committed to git).
        </p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-700">
        <ol className="list-decimal space-y-2 pl-5">
          <li>
            Optional for workshops: on the{' '}
            <Link to="/" className="font-semibold text-blue-700 underline-offset-2 hover:underline">
              home page
            </Link>
            , use <span className="font-semibold">Reset Demo Data</span> to rebuild the seeded scenario set into a known
            starting queue so a guided session stays in sync. Figures below are computed from those records like any other
            deployment.
          </li>
          <li>
            Set <span className="font-semibold">Active Role</span> to <span className="font-semibold">Intake Clerk</span>, open{' '}
            <Link to="/intake" className="font-semibold text-blue-700 underline-offset-2 hover:underline">
              Intake
            </Link>
            , and upload a <span className="font-semibold">PDF</span> from the demo downloads.
          </li>
          <li>
            Switch to <span className="font-semibold">Department Reviewer</span> →{' '}
            <Link to="/review" className="font-semibold text-blue-700 underline-offset-2 hover:underline">
              Review
            </Link>{' '}
            to validate AI routing and workflow actions.
          </li>
          <li>
            Select <span className="font-semibold">Supervisor</span> in the header and return here for aggregate metrics
            (trend badges are illustrative in this MVP).
          </li>
        </ol>
      </CardContent>
    </Card>
  );
}
