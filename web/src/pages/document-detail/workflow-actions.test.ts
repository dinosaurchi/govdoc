/**
 * Unit tests for workflow action helpers and state resolution.
 *
 * Exercises every exported predicate, getWorkflowActionStates, and
 * getWorkflowStatusMessage from workflow-actions.ts.
 */

import { describe, it, expect } from 'vitest';
import {
  isTerminalStatus,
  canAnalyze,
  canApproveRouting,
  canReroute,
  canRequestConsultation,
  canResolveConsultation,
  canEscalate,
  canMarkOutOfScope,
  canClose,
  getWorkflowActionStates,
  getWorkflowStatusMessage,
  type DocContext,
} from './workflow-actions';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Shorthand to build a DocContext with sensible defaults. */
function doc(overrides: Partial<DocContext> = {}): DocContext {
  return {
    status: 'received',
    analyses: [],
    consultation_notes: [],
    ...overrides,
  };
}

const unresolvedNotes: Array<{ resolved_at: string | null }> = [
  { resolved_at: null },
];
const resolvedNotes: Array<{ resolved_at: string | null }> = [
  { resolved_at: '2025-01-01T00:00:00Z' },
];

// ---------------------------------------------------------------------------
// isTerminalStatus
// ---------------------------------------------------------------------------

describe('isTerminalStatus', () => {
  it('returns true for terminal statuses', () => {
    expect(isTerminalStatus('closed')).toBe(true);
    expect(isTerminalStatus('out_of_scope')).toBe(true);
    expect(isTerminalStatus('ingest_failed')).toBe(true);
    expect(isTerminalStatus('analysis_failed')).toBe(true);
  });

  it('returns false for active statuses', () => {
    expect(isTerminalStatus('received')).toBe(false);
    expect(isTerminalStatus('extracted')).toBe(false);
    expect(isTerminalStatus('analyzed')).toBe(false);
    expect(isTerminalStatus('routed')).toBe(false);
    expect(isTerminalStatus('under_review')).toBe(false);
    expect(isTerminalStatus('in_consultation')).toBe(false);
    expect(isTerminalStatus('approved')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canAnalyze  (supervisor-only predicate — role gating tested via ActionStates)
// ---------------------------------------------------------------------------

describe('canAnalyze', () => {
  it('returns true for non-terminal doc with no analyses', () => {
    expect(canAnalyze(doc({ status: 'received' }))).toBe(true);
    expect(canAnalyze(doc({ status: 'extracted' }))).toBe(true);
    expect(canAnalyze(doc({ status: 'analyzed', analyses: [] }))).toBe(true);
  });

  it('returns false for terminal doc', () => {
    expect(canAnalyze(doc({ status: 'closed' }))).toBe(false);
    expect(canAnalyze(doc({ status: 'out_of_scope' }))).toBe(false);
    expect(canAnalyze(doc({ status: 'ingest_failed' }))).toBe(false);
    expect(canAnalyze(doc({ status: 'analysis_failed' }))).toBe(false);
  });

  it('returns false when doc already has analyses', () => {
    expect(canAnalyze(doc({ status: 'analyzed', analyses: [{}] }))).toBe(false);
    expect(canAnalyze(doc({ status: 'received', analyses: [{ id: '1' }] }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canApproveRouting
// ---------------------------------------------------------------------------

describe('canApproveRouting', () => {
  it('returns true when status is analyzed', () => {
    expect(canApproveRouting(doc({ status: 'analyzed' }))).toBe(true);
  });

  it('returns false for non-analyzed statuses', () => {
    expect(canApproveRouting(doc({ status: 'under_review' }))).toBe(false);
    expect(canApproveRouting(doc({ status: 'routed' }))).toBe(false);
    expect(canApproveRouting(doc({ status: 'closed' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canReroute
// ---------------------------------------------------------------------------

describe('canReroute', () => {
  it('returns true for under_review', () => {
    expect(canReroute(doc({ status: 'under_review' }))).toBe(true);
  });

  it('returns false for in_consultation', () => {
    expect(canReroute(doc({ status: 'in_consultation' }))).toBe(false);
  });

  it('returns false for closed', () => {
    expect(canReroute(doc({ status: 'closed' }))).toBe(false);
  });

  it('returns false for other statuses', () => {
    expect(canReroute(doc({ status: 'routed' }))).toBe(false);
    expect(canReroute(doc({ status: 'approved' }))).toBe(false);
    expect(canReroute(doc({ status: 'analyzed' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canRequestConsultation
// ---------------------------------------------------------------------------

describe('canRequestConsultation', () => {
  it('returns true for under_review status', () => {
    expect(canRequestConsultation(doc({ status: 'under_review' }))).toBe(true);
  });

  it('returns true for routed status', () => {
    expect(canRequestConsultation(doc({ status: 'routed' }))).toBe(true);
  });

  it('returns false for other statuses', () => {
    expect(canRequestConsultation(doc({ status: 'analyzed' }))).toBe(false);
    expect(canRequestConsultation(doc({ status: 'closed' }))).toBe(false);
    expect(canRequestConsultation(doc({ status: 'in_consultation' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canResolveConsultation
// ---------------------------------------------------------------------------

describe('canResolveConsultation', () => {
  it('returns true when in_consultation with unresolved notes', () => {
    expect(
      canResolveConsultation(doc({ status: 'in_consultation', consultation_notes: unresolvedNotes })),
    ).toBe(true);
  });

  it('returns false when in_consultation but no unresolved notes', () => {
    expect(
      canResolveConsultation(doc({ status: 'in_consultation', consultation_notes: resolvedNotes })),
    ).toBe(false);
  });

  it('returns false when in_consultation but no notes at all', () => {
    expect(
      canResolveConsultation(doc({ status: 'in_consultation', consultation_notes: [] })),
    ).toBe(false);
  });

  it('returns false for other statuses', () => {
    expect(canResolveConsultation(doc({ status: 'under_review' }))).toBe(false);
    expect(canResolveConsultation(doc({ status: 'routed' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canEscalate
// ---------------------------------------------------------------------------

describe('canEscalate', () => {
  it('returns true for non-terminal, non-approved statuses', () => {
    expect(canEscalate(doc({ status: 'under_review' }))).toBe(true);
    expect(canEscalate(doc({ status: 'routed' }))).toBe(true);
    expect(canEscalate(doc({ status: 'in_consultation' }))).toBe(true);
  });

  it('returns false for terminal statuses', () => {
    expect(canEscalate(doc({ status: 'closed' }))).toBe(false);
    expect(canEscalate(doc({ status: 'out_of_scope' }))).toBe(false);
  });

  it('returns false for approved status', () => {
    expect(canEscalate(doc({ status: 'approved' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canMarkOutOfScope
// ---------------------------------------------------------------------------

describe('canMarkOutOfScope', () => {
  it('returns true for under_review', () => {
    expect(canMarkOutOfScope(doc({ status: 'under_review' }))).toBe(true);
  });

  it('returns true for routed', () => {
    expect(canMarkOutOfScope(doc({ status: 'routed' }))).toBe(true);
  });

  it('returns true for in_consultation', () => {
    expect(canMarkOutOfScope(doc({ status: 'in_consultation' }))).toBe(true);
  });

  it('returns false for closed', () => {
    expect(canMarkOutOfScope(doc({ status: 'closed' }))).toBe(false);
  });

  it('returns false for analyzed', () => {
    expect(canMarkOutOfScope(doc({ status: 'analyzed' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// canClose
// ---------------------------------------------------------------------------

describe('canClose', () => {
  it('returns true for under_review', () => {
    expect(canClose(doc({ status: 'under_review' }))).toBe(true);
  });

  it('returns true for in_consultation', () => {
    expect(canClose(doc({ status: 'in_consultation' }))).toBe(true);
  });

  it('returns true for approved', () => {
    expect(canClose(doc({ status: 'approved' }))).toBe(true);
  });

  it('returns false for analyzed', () => {
    expect(canClose(doc({ status: 'analyzed' }))).toBe(false);
  });

  it('returns false for closed', () => {
    expect(canClose(doc({ status: 'closed' }))).toBe(false);
  });

  it('returns false for non-terminal statuses outside the allowed set', () => {
    expect(canClose(doc({ status: 'routed' }))).toBe(false);
    expect(canClose(doc({ status: 'received' }))).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// getWorkflowActionStates  (integration tests)
// ---------------------------------------------------------------------------

describe('getWorkflowActionStates', () => {
  it('hides all actions for a closed document (supervisor)', () => {
    const states = getWorkflowActionStates(doc({ status: 'closed' }), 'supervisor');
    expect(states.available).toHaveLength(0);
    expect(states.disabled).toHaveLength(0);
    // All actions should be hidden since it's terminal
    expect(states.hidden.length).toBeGreaterThan(0);
  });

  it('shows approve-routing as available for reviewer on analyzed doc', () => {
    const states = getWorkflowActionStates(doc({ status: 'analyzed' }), 'reviewer');
    const ids = states.available.map((a) => a.id);
    expect(ids).toContain('approve-routing');
    // Other review actions should be disabled or hidden
    expect(ids).not.toContain('analyze'); // supervisor-only
    expect(ids).not.toContain('close'); // supervisor-only
  });

  it('shows request-consultation as available for reviewer on under_review doc', () => {
    const states = getWorkflowActionStates(doc({ status: 'under_review' }), 'reviewer');
    const availableIds = states.available.map((a) => a.id);
    expect(availableIds).toContain('request-consultation');
    // approve-routing should be disabled (not analyzed)
    const disabledIds = states.disabled.map((d) => d.action.id);
    expect(disabledIds).toContain('approve-routing');
  });

  it('shows reroute as available for reviewer on under_review doc', () => {
    const states = getWorkflowActionStates(doc({ status: 'under_review' }), 'reviewer');
    const availableIds = states.available.map((a) => a.id);
    expect(availableIds).toContain('reroute');
  });

  it('shows reroute as disabled for reviewer on in_consultation doc', () => {
    const states = getWorkflowActionStates(doc({ status: 'in_consultation' }), 'reviewer');
    const availableIds = states.available.map((a) => a.id);
    expect(availableIds).not.toContain('reroute');
    const disabledIds = states.disabled.map((d) => d.action.id);
    expect(disabledIds).toContain('reroute');
  });

  it('shows resolve-consultation for reviewer on in_consultation doc with unresolved notes', () => {
    const states = getWorkflowActionStates(
      doc({ status: 'in_consultation', consultation_notes: unresolvedNotes }),
      'reviewer',
    );
    const availableIds = states.available.map((a) => a.id);
    expect(availableIds).toContain('resolve-consultation');
  });

  it('disables resolve-consultation for reviewer on in_consultation doc with no unresolved notes', () => {
    const states = getWorkflowActionStates(
      doc({ status: 'in_consultation', consultation_notes: resolvedNotes }),
      'reviewer',
    );
    const availableIds = states.available.map((a) => a.id);
    expect(availableIds).not.toContain('resolve-consultation');
    const disabledIds = states.disabled.map((d) => d.action.id);
    expect(disabledIds).toContain('resolve-consultation');
  });

  it('hides supervisor-only actions for intake_clerk', () => {
    const states = getWorkflowActionStates(doc({ status: 'under_review' }), 'intake_clerk');
    const allVisible = [
      ...states.available.map((a) => a.id),
      ...states.disabled.map((d) => d.action.id),
    ];
    expect(allVisible).not.toContain('analyze');
    expect(allVisible).not.toContain('escalate');
    expect(allVisible).not.toContain('close');
  });

  it('hides non-consultant actions correctly for consultant role', () => {
    const states = getWorkflowActionStates(
      doc({ status: 'in_consultation', consultation_notes: unresolvedNotes }),
      'consultant',
    );
    const allVisible = [
      ...states.available.map((a) => a.id),
      ...states.disabled.map((d) => d.action.id),
    ];
    // Consultant can see resolve-consultation
    expect(allVisible).toContain('resolve-consultation');
    // Consultant should NOT see approve-routing, reroute, request-consultation, close, etc.
    expect(allVisible).not.toContain('approve-routing');
    expect(allVisible).not.toContain('close');
    expect(allVisible).not.toContain('escalate');
  });
});

// ---------------------------------------------------------------------------
// getWorkflowStatusMessage
// ---------------------------------------------------------------------------

describe('getWorkflowStatusMessage', () => {
  const allStatuses: string[] = [
    'closed',
    'out_of_scope',
    'ingest_failed',
    'analysis_failed',
    'received',
    'extracted',
    'analyzed',
    'routed',
    'under_review',
    'in_consultation',
    'approved',
  ];

  it('returns a non-empty string for every known status', () => {
    for (const status of allStatuses) {
      const msg = getWorkflowStatusMessage(status);
      expect(msg.length, `status "${status}" should have a non-empty message`).toBeGreaterThan(0);
    }
  });

  it('terminal statuses mention no further actions', () => {
    const terminalStatuses = ['closed', 'out_of_scope', 'ingest_failed', 'analysis_failed'];
    for (const status of terminalStatuses) {
      const msg = getWorkflowStatusMessage(status);
      expect(
        msg.toLowerCase(),
        `terminal status "${status}" should mention no further actions`,
      ).toContain('no further');
    }
  });

  it('active statuses describe available actions or state', () => {
    const activeStatuses = [
      'received',
      'extracted',
      'analyzed',
      'routed',
      'under_review',
      'in_consultation',
      'approved',
    ];
    for (const status of activeStatuses) {
      const msg = getWorkflowStatusMessage(status);
      // Active messages should NOT say "no further"
      expect(
        msg.toLowerCase(),
        `active status "${status}" should not say "no further"`,
      ).not.toContain('no further');
    }
  });

  it('returns empty string for unknown status', () => {
    expect(getWorkflowStatusMessage('some_unknown_status')).toBe('');
  });
});
