import { create } from 'zustand';
import type {
  SessionRecoveryState,
  SessionSnapshot,
  SessionSummary,
} from '../types';

/**
 * Cache of the session list plus the currently open session.
 *
 * The socket folds revisions through the shared projection. This store accepts
 * its safe snapshots only for the current screen owner and updates list rows.
 */
interface SessionsState {
  summaries: SessionSummary[];
  active: SessionSnapshot | null;
  activeOwner: symbol | null;
  loading: boolean;
  error: string | null;

  setSummaries(summaries: SessionSummary[]): void;
  beginActive(owner: symbol): void;
  setActive(owner: symbol, session: SessionSnapshot | null): void;
  setRecovery(owner: symbol, recovery: SessionRecoveryState): void;
  setLoading(loading: boolean): void;
  setError(error: string | null): void;
  clear(owner: symbol): void;
}

export const useSessionsStore = create<SessionsState>((set) => ({
  summaries: [],
  active: null,
  activeOwner: null,
  loading: false,
  error: null,

  setSummaries: (summaries) => set({ summaries, error: null }),
  beginActive: (activeOwner) => set({ activeOwner, active: null }),
  setActive: (owner, active) =>
    set((state) => (state.activeOwner === owner ? { active } : state)),

  setRecovery: (owner, recovery) =>
    set((state) => {
      if (state.activeOwner !== owner) return state;
      if (recovery.status === 'deleted')
        return {
          active: null,
          summaries: state.summaries.filter(
            (row) => row.id !== recovery.sessionId,
          ),
        };
      if (recovery.status === 'unsupported') return { active: null };
      if (!recovery.snapshot || recovery.snapshot === state.active)
        return state;
      return {
        active: recovery.snapshot,
        summaries: syncSummary(state.summaries, recovery.snapshot),
      };
    }),

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  clear: (owner) =>
    set((state) =>
      state.activeOwner === owner
        ? { activeOwner: null, active: null, error: null }
        : state,
    ),
}));

/** Keep the list projection consistent with the open session. */
function syncSummary(
  summaries: SessionSummary[],
  session: SessionSnapshot,
): SessionSummary[] {
  return summaries.map((summary) =>
    summary.id === session.id
      ? {
          ...summary,
          name: session.name,
          status: session.status,
          itemCount: session.items.length,
          participantCount: session.participants.length,
          updatedAt: session.updatedAt,
        }
      : summary,
  );
}
