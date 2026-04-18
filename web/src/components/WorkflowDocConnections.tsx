import { Link } from 'react-router-dom';
import { ClipboardCheck, FileText, ListChecks, MessageSquare } from 'lucide-react';

export type WorkflowHub = 'document' | 'review' | 'consultation' | 'response';

const HUBS: Array<{
  hub: WorkflowHub;
  label: string;
  icon: typeof FileText;
  to: (docId: string) => string;
}> = [
  { hub: 'document', label: 'Document', icon: FileText, to: (id) => `/documents/${id}` },
  { hub: 'review', label: 'Review queue', icon: ListChecks, to: () => '/review' },
  { hub: 'consultation', label: 'Consultation', icon: MessageSquare, to: (id) => `/consultation?doc=${id}` },
  { hub: 'response', label: 'Response', icon: ClipboardCheck, to: (id) => `/response?doc=${id}` },
];

type Props = {
  docId: string;
  /** Page you are on — that destination is omitted so the strip points outward. */
  current: WorkflowHub;
  className?: string;
  /** Use inside clickable rows/cards so links do not trigger the parent action. */
  onLinkClick?: (e: React.MouseEvent) => void;
  /** Smaller controls for sidebar list cards. */
  dense?: boolean;
};

export function WorkflowDocConnections({ docId, current, className, onLinkClick, dense }: Props) {
  const targets = HUBS.filter((h) => h.hub !== current);

  return (
    <div
      className={`flex flex-wrap items-center gap-1.5 ${className ?? ''}`}
      data-testid="workflow-doc-connections"
      aria-label="Open this case elsewhere in SecureFlow"
    >
      {targets.map(({ hub, label, icon: Icon, to }) => (
        <Link
          key={hub}
          to={to(docId)}
          onClick={onLinkClick}
          className={`inline-flex items-center gap-1 rounded-md font-bold uppercase tracking-wide border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors ${
            dense ? 'text-[9px] px-1.5 py-0.5' : 'text-[10px] px-2 py-1'
          }`}
        >
          <Icon size={dense ? 10 : 12} className="shrink-0 text-slate-500" aria-hidden />
          {label}
        </Link>
      ))}
    </div>
  );
}
