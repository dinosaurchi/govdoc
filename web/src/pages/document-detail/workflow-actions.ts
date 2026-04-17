/**
 * Centralized state-aware workflow action model.
 *
 * Determines which workflow actions are available, disabled, or hidden
 * based on document status, user role, and document data (analyses,
 * consultation notes).
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DocumentStatus =
  | 'received'
  | 'extracted'
  | 'analyzed'
  | 'routed'
  | 'under_review'
  | 'in_consultation'
  | 'approved'
  | 'closed'
  | 'out_of_scope'
  | 'ingest_failed'
  | 'analysis_failed';

export type Role = 'intake_clerk' | 'reviewer' | 'consultant' | 'supervisor';

export type DocContext = {
  status: string;
  analyses?: unknown[];
  consultation_notes?: Array<{ resolved_at: string | null }>;
};

export interface WorkflowAction {
  /** Machine-readable action identifier (matches handleAction switch cases). */
  id: string;
  /** Human-readable button label. */
  label: string;
  /** Semantic grouping for sidebar sections. */
  group: 'analysis' | 'review' | 'consultation' | 'closeout';
  /** Visual severity hint for the consuming UI. */
  variant: 'default' | 'caution' | 'destructive';
  /** Roles that are allowed to *see* this action at all. */
  allowedRoles: Role[];
  /** Returns true when the action can be executed right now. */
  isAvailable: (doc: DocContext, role: Role) => boolean;
  /**
   * Returns `null` when the action is available, or a human-readable reason
   * string explaining why it is currently disabled.
   */
  getDisabledReason: (doc: DocContext, role: Role) => string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TERMINAL_STATUSES: ReadonlySet<string> = new Set([
  'closed',
  'out_of_scope',
  'ingest_failed',
  'analysis_failed',
]);

export function isTerminalStatus(status: string): boolean {
  return TERMINAL_STATUSES.has(status);
}

function hasUnresolvedNotes(doc: DocContext): boolean {
  if (!doc.consultation_notes || doc.consultation_notes.length === 0) return false;
  return doc.consultation_notes.some((n) => n.resolved_at === null);
}

function hasAnalysis(doc: DocContext): boolean {
  return Array.isArray(doc.analyses) && doc.analyses.length > 0;
}

// ---------------------------------------------------------------------------
// Predicate helpers (exported for testability)
// ---------------------------------------------------------------------------

/** Supervisor only, any non-terminal status, only if no existing analysis. */
export function canAnalyze(doc: DocContext): boolean {
  return !isTerminalStatus(doc.status) && !hasAnalysis(doc);
}

/** Reviewer/supervisor, status must be `analyzed`. */
export function canApproveRouting(doc: DocContext): boolean {
  return doc.status === 'analyzed';
}

/** Reviewer/supervisor, status must be under_review or in_consultation. */
export function canReroute(doc: DocContext): boolean {
  return doc.status === 'under_review' || doc.status === 'in_consultation';
}

/** Reviewer/supervisor, status must be under_review or routed. */
export function canRequestConsultation(doc: DocContext): boolean {
  return doc.status === 'under_review' || doc.status === 'routed';
}

/** Reviewer/consultant/supervisor, must be in_consultation with unresolved notes. */
export function canResolveConsultation(doc: DocContext): boolean {
  return doc.status === 'in_consultation' && hasUnresolvedNotes(doc);
}

/** Supervisor only, not terminal and not approved. */
export function canEscalate(doc: DocContext): boolean {
  return !isTerminalStatus(doc.status) && doc.status !== 'approved';
}

/** Reviewer/supervisor, status allows transition to out_of_scope. */
export function canMarkOutOfScope(doc: DocContext): boolean {
  return (
    doc.status === 'routed' ||
    doc.status === 'under_review' ||
    doc.status === 'in_consultation'
  );
}

/** Supervisor only, status must be under_review, in_consultation, or approved. */
export function canClose(doc: DocContext): boolean {
  return (
    doc.status === 'under_review' ||
    doc.status === 'in_consultation' ||
    doc.status === 'approved'
  );
}

// ---------------------------------------------------------------------------
// Action definitions
// ---------------------------------------------------------------------------

const WORKFLOW_ACTIONS: readonly WorkflowAction[] = [
  {
    id: 'analyze',
    label: 'Run AI analysis',
    group: 'analysis',
    variant: 'default',
    allowedRoles: ['supervisor'],
    isAvailable: canAnalyze,
    getDisabledReason: (doc) => {
      if (hasAnalysis(doc)) return 'Only available before initial analysis';
      return null;
    },
  },
  {
    id: 'approve-routing',
    label: 'Approve routing',
    group: 'review',
    variant: 'destructive',
    allowedRoles: ['reviewer', 'supervisor'],
    isAvailable: canApproveRouting,
    getDisabledReason: (doc) => {
      if (doc.status !== 'analyzed') return 'Only available when document is analyzed';
      return null;
    },
  },
  {
    id: 'reroute',
    label: 'Reroute document',
    group: 'review',
    variant: 'default',
    allowedRoles: ['reviewer', 'supervisor'],
    isAvailable: canReroute,
    getDisabledReason: (doc) => {
      if (doc.status !== 'under_review' && doc.status !== 'in_consultation') {
        return 'Only available while document is under review or in consultation';
      }
      return null;
    },
  },
  {
    id: 'request-consultation',
    label: 'Request consultation',
    group: 'consultation',
    variant: 'caution',
    allowedRoles: ['reviewer', 'supervisor'],
    isAvailable: canRequestConsultation,
    getDisabledReason: (doc) => {
      if (doc.status !== 'under_review' && doc.status !== 'routed') {
        return 'Only available while document is under review';
      }
      return null;
    },
  },
  {
    id: 'resolve-consultation',
    label: 'Resolve consultation',
    group: 'consultation',
    variant: 'destructive',
    allowedRoles: ['reviewer', 'consultant', 'supervisor'],
    isAvailable: canResolveConsultation,
    getDisabledReason: (doc) => {
      if (doc.status !== 'in_consultation') return 'Only available during active consultation';
      if (!hasUnresolvedNotes(doc)) return 'No unresolved consultation notes to resolve';
      return null;
    },
  },
  {
    id: 'escalate',
    label: 'Escalate to supervisor',
    group: 'review',
    variant: 'default',
    allowedRoles: ['supervisor'],
    isAvailable: canEscalate,
    getDisabledReason: (doc) => {
      if (isTerminalStatus(doc.status)) return 'Only available on active documents';
      if (doc.status === 'approved') return 'Cannot escalate an approved document';
      return null;
    },
  },
  {
    id: 'mark-out-of-scope',
    label: 'Mark out of scope',
    group: 'closeout',
    variant: 'destructive',
    allowedRoles: ['reviewer', 'supervisor'],
    isAvailable: canMarkOutOfScope,
    getDisabledReason: (doc) => {
      if (
        doc.status !== 'routed' &&
        doc.status !== 'under_review' &&
        doc.status !== 'in_consultation'
      ) {
        return 'Only available while document is under review';
      }
      return null;
    },
  },
  {
    id: 'close',
    label: 'Close document',
    group: 'closeout',
    variant: 'destructive',
    allowedRoles: ['supervisor'],
    isAvailable: canClose,
    getDisabledReason: (doc) => {
      if (
        doc.status !== 'under_review' &&
        doc.status !== 'in_consultation' &&
        doc.status !== 'approved'
      ) {
        return 'Only available when document is under review, in consultation, or approved';
      }
      return null;
    },
  },
];

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export interface ActionStates {
  available: WorkflowAction[];
  disabled: Array<{ action: WorkflowAction; reason: string }>;
  hidden: WorkflowAction[];
}

/**
 * Categorises every workflow action for the given document/role pair into
 * three buckets: `available`, `disabled` (with reason), and `hidden`.
 *
 * For terminal-status documents ALL actions are hidden — the caller should
 * render a terminal-state message instead of the action panel.
 */
export function getWorkflowActionStates(
  doc: DocContext,
  role: Role,
): ActionStates {
  const available: WorkflowAction[] = [];
  const disabled: Array<{ action: WorkflowAction; reason: string }> = [];
  const hidden: WorkflowAction[] = [];

  const terminal = isTerminalStatus(doc.status);

  for (const action of WORKFLOW_ACTIONS) {
    // 1. Hide if role is not allowed
    if (!action.allowedRoles.includes(role)) {
      hidden.push(action);
      continue;
    }

    // 2. For terminal statuses, hide every action
    if (terminal) {
      hidden.push(action);
      continue;
    }

    // 3. Determine available vs disabled
    if (action.isAvailable(doc, role)) {
      available.push(action);
    } else {
      const reason = action.getDisabledReason(doc, role);
      disabled.push({ action, reason: reason ?? 'Not available' });
    }
  }

  return { available, disabled, hidden };
}

// ---------------------------------------------------------------------------
// Group labels
// ---------------------------------------------------------------------------

export const ACTION_GROUP_LABELS: Record<WorkflowAction['group'], string> = {
  analysis: 'Analysis',
  review: 'Review',
  consultation: 'Consultation',
  closeout: 'Closeout',
};

// ---------------------------------------------------------------------------
// Role mapping helper (frontend label → role ID)
// ---------------------------------------------------------------------------

const FRONTEND_ROLE_MAP: Record<string, Role> = {
  'Intake Clerk': 'intake_clerk',
  'Department Reviewer': 'reviewer',
  Consultant: 'consultant',
  Supervisor: 'supervisor',
};

export function toRoleId(frontendRole: string): Role {
  return FRONTEND_ROLE_MAP[frontendRole] ?? 'intake_clerk';
}

// ---------------------------------------------------------------------------
// Status-aware helper message
// ---------------------------------------------------------------------------

export function getWorkflowStatusMessage(status: string): string {
  switch (status) {
    case 'closed':
      return 'This document is closed. No further workflow actions are available.';
    case 'out_of_scope':
      return 'This document has been marked out of scope. No further workflow actions are available.';
    case 'ingest_failed':
      return 'Document ingestion failed. No further workflow actions are available.';
    case 'analysis_failed':
      return 'Document analysis failed. No further workflow actions are available.';
    case 'received':
    case 'extracted':
      return 'This document is being processed. Workflow actions will become available after analysis.';
    case 'analyzed':
      return 'Analysis complete. Review and routing actions are now available.';
    case 'routed':
      return 'Document has been routed. A reviewer can now claim and review this document.';
    case 'under_review':
      return 'This document is under review. Use the actions below to progress the workflow.';
    case 'in_consultation':
      return 'This document is in consultation. Resolve the consultation to continue.';
    case 'approved':
      return 'This document has been approved. A supervisor can close it.';
    default:
      return '';
  }
}

// ---------------------------------------------------------------------------
// Variant → button color mapping
// ---------------------------------------------------------------------------

export type ButtonVariant = 'blue' | 'amber' | 'red';

const VARIANT_COLOR_MAP: Record<WorkflowAction['variant'], ButtonVariant> = {
  default: 'blue',
  caution: 'amber',
  destructive: 'red',
};

export function toButtonVariant(variant: WorkflowAction['variant']): ButtonVariant {
  return VARIANT_COLOR_MAP[variant];
}
