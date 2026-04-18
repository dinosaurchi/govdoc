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
  assigned_department_id?: string | null;
};

export interface WorkflowAction {
  /** Machine-readable action identifier (matches handleAction switch cases). */
  id: string;
  /** Human-readable button label. */
  label: string;
  /** Semantic grouping for sidebar sections. */
  group: 'analysis' | 'review' | 'consultation' | 'closeout';
  /** Visual severity hint for the consuming UI. */
  variant: 'default' | 'success' | 'caution' | 'destructive';
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

/** Reviewer/supervisor, status must be under_review. */
export function canReroute(doc: DocContext): boolean {
  return doc.status === 'under_review';
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

/** Supervisor only — archives an already-approved document. */
export function canClose(doc: DocContext): boolean {
  return doc.status === 'approved';
}

/** Reviewer/supervisor — formal approval before close (no open consultation notes). */
export function canApprove(doc: DocContext): boolean {
  if (doc.status !== 'under_review' && doc.status !== 'in_consultation') return false;
  if (hasUnresolvedNotes(doc)) return false;
  return true;
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
    variant: 'success',
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
      if (doc.status !== 'under_review') {
        return 'Only available while the document is under review';
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
    variant: 'success',
    allowedRoles: ['reviewer', 'consultant', 'supervisor'],
    isAvailable: canResolveConsultation,
    getDisabledReason: (doc) => {
      if (doc.status !== 'in_consultation') return 'Only available during active consultation';
      if (!hasUnresolvedNotes(doc)) return 'No unresolved consultation notes to resolve';
      return null;
    },
  },
  {
    id: 'approve',
    label: 'Approve document',
    group: 'closeout',
    variant: 'success',
    allowedRoles: ['reviewer', 'supervisor'],
    isAvailable: canApprove,
    getDisabledReason: (doc) => {
      if (doc.status !== 'under_review' && doc.status !== 'in_consultation') {
        return 'Only available while under review or in consultation';
      }
      if (hasUnresolvedNotes(doc)) {
        return 'Resolve open consultation notes before approving';
      }
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
    variant: 'success',
    allowedRoles: ['supervisor'],
    isAvailable: canClose,
    getDisabledReason: (doc) => {
      if (doc.status !== 'approved') {
        return 'Only available after the document has been approved';
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
/**
 * Per (status, role), the id of the single action that most advances the
 * workflow toward completion. `null` means there is no "forward" action
 * for this role on this status — the user must hand off to another role
 * (surfaced via `getActionsAvailableForOtherRoles`).
 */
const FORWARD_ACTION_BY_STATUS_ROLE: Record<string, Partial<Record<Role, string>>> = {
  analyzed: { reviewer: 'approve-routing', supervisor: 'approve-routing' },
  under_review: { reviewer: 'approve', supervisor: 'approve' },
  in_consultation: { reviewer: 'resolve-consultation', consultant: 'resolve-consultation', supervisor: 'resolve-consultation' },
  approved: { supervisor: 'close' },
};

/**
 * Pick the single forward action for (status, role).
 *
 * Accepts either a raw status string or a full DocContext. When a
 * DocContext is provided we apply a few context-sensitive overrides:
 *   - `under_review` + supervisor + NO assigned_department_id → recommend
 *     `reroute` instead of `close`. Closing an un-routed document would
 *     just hide an un-owned case; the supervisor needs to pick a
 *     department first.
 */
export function getForwardActionId(
  statusOrDoc: string | DocContext,
  role: Role,
): string | null {
  const doc: DocContext | null =
    typeof statusOrDoc === 'string' ? null : statusOrDoc;
  const status = typeof statusOrDoc === 'string' ? statusOrDoc : statusOrDoc.status;

  if (
    doc &&
    status === 'under_review' &&
    role === 'supervisor' &&
    !doc.assigned_department_id
  ) {
    // No owner picked yet — recommend rerouting instead of approving/closing.
    return 'reroute';
  }

  // In consultation: resolving open notes takes priority; once notes are
  // cleared but status is still `in_consultation`, recommend approval.
  if (doc && status === 'in_consultation') {
    if (hasUnresolvedNotes(doc)) {
      return FORWARD_ACTION_BY_STATUS_ROLE.in_consultation?.[role] ?? null;
    }
    if (role === 'reviewer' || role === 'supervisor') {
      return 'approve';
    }
    return null;
  }

  return FORWARD_ACTION_BY_STATUS_ROLE[status]?.[role] ?? null;
}

/** IDs that, when listed alongside others, look like "try again" branches
 *  (they don't advance the pipeline to a terminal or approved state). */
const ALTERNATIVE_ACTION_IDS: ReadonlySet<string> = new Set([
  'reroute',
  'request-consultation',
  'mark-out-of-scope',
  'escalate',
]);

export function isAlternativeAction(actionId: string): boolean {
  return ALTERNATIVE_ACTION_IDS.has(actionId);
}

/**
 * Split a list of available actions into the "forward" action (single,
 * role+status-aware) and the remaining "alternative" actions in their
 * original order. The forward slot is `null` when the role has no
 * progression action for the current status.
 */
export function partitionByForwardness(
  actions: WorkflowAction[],
  statusOrDoc: string | DocContext,
  role: Role,
): { forward: WorkflowAction | null; alternatives: WorkflowAction[] } {
  const forwardId = getForwardActionId(statusOrDoc, role);
  let forward: WorkflowAction | null = null;
  const alternatives: WorkflowAction[] = [];
  for (const a of actions) {
    if (forwardId && a.id === forwardId && !forward) {
      forward = a;
    } else {
      alternatives.push(a);
    }
  }
  return { forward, alternatives };
}

/**
 * Returns, per *other* role, the progression actions that would be
 * available right now on this document if the user switched to that role.
 *
 * Used to drive the "needs another role" CTA: when a reviewer has
 * rerouted a document there are no further actions *for them* that move
 * the case to a terminal state (e.g. `close`), but a Supervisor could
 * close it — we want to surface that clearly instead of leaving the user
 * wondering why nothing else happens.
 */
export function getActionsAvailableForOtherRoles(
  doc: DocContext,
  currentRole: Role,
): Array<{ role: Role; actions: WorkflowAction[]; forward: WorkflowAction | null }> {
  if (isTerminalStatus(doc.status)) return [];
  const otherRoles: Role[] = (['supervisor', 'reviewer', 'consultant', 'intake_clerk'] as Role[]).filter(
    (r) => r !== currentRole,
  );
  const result: Array<{ role: Role; actions: WorkflowAction[]; forward: WorkflowAction | null }> = [];
  for (const role of otherRoles) {
    const all = WORKFLOW_ACTIONS.filter(
      (a) => a.allowedRoles.includes(role) && a.isAvailable(doc, role),
    );
    const forwardId = getForwardActionId(doc, role);
    const forward = forwardId ? all.find((a) => a.id === forwardId) ?? null : null;
    // Only show the other role if they have a *forward* (progressive) action.
    // Listing "reroute / reroute / reroute" for every other role adds noise
    // instead of helping the user understand the next owner.
    if (forward) {
      result.push({ role, actions: all, forward });
    }
  }
  return result;
}

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

/** Inverse of `toRoleId` — return the frontend label stored in `RoleProvider`. */
export function toFrontendRoleLabel(roleId: Role): string {
  const entry = Object.entries(FRONTEND_ROLE_MAP).find(([, id]) => id === roleId);
  return entry ? entry[0] : 'Intake Clerk';
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
      return 'This document has been approved. A supervisor can close it to archive.';
    default:
      return '';
  }
}

// ---------------------------------------------------------------------------
// Variant → button color mapping
// ---------------------------------------------------------------------------

export type ButtonVariant = 'blue' | 'emerald' | 'amber' | 'red';

const VARIANT_COLOR_MAP: Record<WorkflowAction['variant'], ButtonVariant> = {
  default: 'blue',
  success: 'emerald',
  caution: 'amber',
  destructive: 'red',
};

export function toButtonVariant(variant: WorkflowAction['variant']): ButtonVariant {
  return VARIANT_COLOR_MAP[variant];
}

// ---------------------------------------------------------------------------
// Pipeline stepper
// ---------------------------------------------------------------------------

/** Canonical linear progression of an active document through the workflow.
 *  Terminal states (closed/out_of_scope/ingest_failed/analysis_failed) are
 *  not part of this linear progression. */
export const PIPELINE_STAGES: readonly { id: string; label: string; description: string }[] = [
  { id: 'received', label: 'Received', description: 'File accepted by the intake API.' },
  { id: 'extracted', label: 'Extracted', description: 'Text extracted from the file.' },
  { id: 'analyzed', label: 'Analyzed', description: 'AI classification & routing suggestions generated.' },
  { id: 'routed', label: 'Routed', description: 'Awaiting reviewer claim.' },
  { id: 'under_review', label: 'Under Review', description: 'Reviewer handling the document.' },
  { id: 'in_consultation', label: 'In Consultation', description: 'Cross-department consultation in progress.' },
  { id: 'approved', label: 'Approved', description: 'Formal approval recorded; ready to archive.' },
  { id: 'closed', label: 'Closed', description: 'File closed. No further actions.' },
] as const;

/** Index of the in-consultation step (for skip-detection). */
export const PIPELINE_IN_CONSULTATION_INDEX = PIPELINE_STAGES.findIndex(
  (s) => s.id === 'in_consultation',
);

/** Visual state for one row of the workflow progress stepper. */
export type PipelineStepVisualState = 'done' | 'active' | 'pending';

/**
 * Computes stepper visuals for `PIPELINE_STAGES[stageIndex]` given API status.
 *
 * - `closed` is terminal for actions but is still the last pipeline stage — all
 *   rows show as completed (fixes the bug where `isTerminalStatus(closed)`
 *   greyed out every row).
 * - `approved` without any consultation notes keeps the In Consultation row
 *   **pending** so we do not imply a consultation that never happened.
 */
export function getPipelineStepState(
  status: string,
  stageIndex: number,
  options?: { hadConsultationActivity?: boolean },
): PipelineStepVisualState {
  const hadConsultation = options?.hadConsultationActivity ?? false;
  const currentIdx = getPipelineIndex(status);

  if (status === 'closed') {
    return 'done';
  }

  // Hard terminal outcomes that are not represented as a pipeline row
  if (isTerminalStatus(status) && currentIdx < 0) {
    return 'pending';
  }

  if (currentIdx < 0) {
    return 'pending';
  }

  const ciIdx = PIPELINE_IN_CONSULTATION_INDEX;
  if (
    ciIdx >= 0 &&
    stageIndex === ciIdx &&
    status === 'approved' &&
    !hadConsultation
  ) {
    return 'pending';
  }

  if (currentIdx > stageIndex) return 'done';
  if (currentIdx === stageIndex) return 'active';
  return 'pending';
}

/** Returns the index of the status inside PIPELINE_STAGES, or -1 for terminal
 *  error states / unknown statuses. */
export function getPipelineIndex(status: string): number {
  return PIPELINE_STAGES.findIndex((s) => s.id === status);
}

// ---------------------------------------------------------------------------
// "Responsible role" hint for the current status
// ---------------------------------------------------------------------------

export const ROLE_LABEL: Record<Role, string> = {
  intake_clerk: 'Intake Clerk',
  reviewer: 'Reviewer',
  consultant: 'Consultant',
  supervisor: 'Supervisor',
};

/** Describes which role is expected to act next for a given status. Used to
 *  educate users who don't yet understand the workflow. */
export function getResponsibleRoles(status: string): Role[] {
  switch (status) {
    case 'received':
    case 'extracted':
      return []; // system/background
    case 'analyzed':
      return ['reviewer', 'supervisor'];
    case 'routed':
      return ['reviewer', 'supervisor'];
    case 'under_review':
      return ['reviewer', 'supervisor'];
    case 'in_consultation':
      return ['reviewer', 'consultant', 'supervisor'];
    case 'approved':
      return ['supervisor'];
    default:
      return [];
  }
}

/** Short next-step hint for the given status — rendered next to the status
 *  pill on the document detail page. When `role` is provided the copy is
 *  tailored to that role so the user isn't told "a Reviewer must act"
 *  while they are already Supervisor. */
export function getNextStepHint(
  statusOrDoc: string | DocContext,
  role?: Role,
): string {
  const doc: DocContext | null =
    typeof statusOrDoc === 'string' ? null : statusOrDoc;
  const status = typeof statusOrDoc === 'string' ? statusOrDoc : statusOrDoc.status;

  const roleHint = role ? getNextStepHintForRole(status, role, doc) : null;
  if (roleHint) return roleHint;
  switch (status) {
    case 'received':
      return 'Waiting for the system to finish extracting text from the file.';
    case 'extracted':
      return 'Waiting for AI analysis to run.';
    case 'analyzed':
      return 'A Reviewer or Supervisor must approve or reroute the AI-suggested department.';
    case 'routed':
      return 'A Reviewer must open this document to begin review (assignment happens on open).';
    case 'under_review':
      return 'A Reviewer or Supervisor must approve the document (or reroute / consult) before it can be closed.';
    case 'in_consultation':
      return 'The Consultant (or the Reviewer) must resolve the open consultation note to continue.';
    case 'approved':
      return 'A Supervisor can close this document.';
    case 'closed':
      return 'No further actions — the document is archived.';
    case 'out_of_scope':
      return 'No further actions — the document was marked out of scope.';
    case 'ingest_failed':
      return 'No further actions — file ingestion failed.';
    case 'analysis_failed':
      return 'No further actions — AI analysis failed.';
    default:
      return '';
  }
}

function getNextStepHintForRole(
  status: string,
  role: Role,
  doc?: DocContext | null,
): string | null {
  if (status === 'under_review') {
    if (doc && !doc.assigned_department_id) {
      // No owning department — rerouting is the first real next step.
      if (role === 'supervisor') {
        return 'No department has been assigned yet — reroute to a department before approving.';
      }
      if (role === 'reviewer') {
        return 'No department has been assigned yet — reroute to a department, or hand off to a Supervisor.';
      }
    }
    if (role === 'supervisor') {
      return 'Approve the document when satisfied, then close it to archive (or use alternatives below).';
    }
    if (role === 'reviewer') {
      return 'Approve when review is complete, request consultation if needed, or hand off to a Supervisor.';
    }
  }
  if (status === 'analyzed') {
    if (role === 'reviewer' || role === 'supervisor') {
      return 'Approve the AI-suggested routing, or reroute to a different department.';
    }
  }
  if (status === 'in_consultation') {
    if (role === 'reviewer' || role === 'consultant' || role === 'supervisor') {
      return 'Resolve the consultation note to continue the workflow.';
    }
  }
  if (status === 'approved' && role === 'supervisor') {
    return 'Close the document to finalize it.';
  }
  return null;
}
