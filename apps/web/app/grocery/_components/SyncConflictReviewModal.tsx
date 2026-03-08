'use client';

import {
  getConflictDetailFields,
  getConflictOutcomeDescription,
  getConflictOutcomeLabel,
  getConflictResolutionActionCopy,
  getConflictResolutionActionLabel,
} from '../../_lib/grocery-ui';
import type { SyncConflictDetail, SyncResolutionAction } from '../../_lib/types';
import { SyncStatusBadge } from '../../_components/SyncStatusBadge';
import styles from './SyncConflictReviewModal.module.css';

type Props = {
  conflict: SyncConflictDetail;
  loading?: boolean;
  message?: string | null;
  resolvingAction?: SyncResolutionAction | null;
  onClose: () => void;
  onResolve: (action: SyncResolutionAction) => Promise<void> | void;
};

function formatVersion(value: number | null): string {
  return value === null ? 'Unknown' : `v${value}`;
}

function DetailSection({
  title,
  emptyCopy,
  fields,
}: {
  title: string;
  emptyCopy: string;
  fields: ReturnType<typeof getConflictDetailFields>;
}) {
  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      {fields.length > 0 ? (
        <dl className={styles.detailList}>
          {fields.map((field) => (
            <div key={`${title}-${field.key}`} className={styles.detailRow}>
              <dt>{field.label}</dt>
              <dd>{field.value}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className={styles.helperText}>{emptyCopy}</p>
      )}
    </section>
  );
}

export function SyncConflictReviewModal({
  conflict,
  loading = false,
  message = null,
  resolvingAction = null,
  onClose,
  onResolve,
}: Props) {
  const localFields = getConflictDetailFields(conflict.localIntentSummary);
  const baseFields = getConflictDetailFields(conflict.baseStateSummary);
  const serverFields = getConflictDetailFields(conflict.serverStateSummary);

  return (
    <div className={styles.overlay} role="presentation" onClick={onClose}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="sync-conflict-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Saved sync issue</p>
            <h2 id="sync-conflict-title" className={styles.title}>
              {conflict.summary}
            </h2>
            <p className={styles.copy}>{getConflictOutcomeDescription(conflict.outcome)}</p>
          </div>
          <SyncStatusBadge
            status={resolvingAction ? 'resolving' : conflict.resolutionStatus === 'resolved_keep_mine'
              ? 'resolved_keep_mine'
              : conflict.resolutionStatus === 'resolved_use_server'
                ? 'resolved_use_server'
                : 'review_required'}
          />
        </div>

        <div className={styles.metaRow}>
          <span className={styles.metaPill}>{getConflictOutcomeLabel(conflict.outcome)}</span>
          <span className={styles.metaPill}>Saved change {conflict.mutationType.replaceAll('_', ' ')}</span>
          <span className={styles.metaPill}>Base {formatVersion(conflict.baseServerVersion)}</span>
          <span className={styles.metaPill}>Server {formatVersion(conflict.currentServerVersion)}</span>
        </div>

        {message && <p className={styles.notice}>{message}</p>}
        {loading && (
          <p className={styles.helperText}>Refreshing the latest comparison from the server…</p>
        )}

        <div className={styles.sectionGrid}>
          <DetailSection
            title="Your saved change"
            emptyCopy="This phone did not keep extra local detail for the saved change."
            fields={localFields}
          />
          <DetailSection
            title="Server version now"
            emptyCopy="No extra server detail was returned for this conflict."
            fields={serverFields}
          />
          <DetailSection
            title="Before you went offline"
            emptyCopy="No base snapshot detail was returned for this conflict."
            fields={baseFields}
          />
        </div>

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Choose what happens next</h3>
          <div className={styles.actionCards}>
            {conflict.allowedResolutionActions.map((action) => (
              <article key={action} className={styles.actionCard}>
                <h4 className={styles.actionTitle}>{getConflictResolutionActionLabel(action)}</h4>
                <p className={styles.helperText}>{getConflictResolutionActionCopy(action)}</p>
                <button
                  className={action === 'keep_mine' ? styles.primaryAction : styles.secondaryAction}
                  type="button"
                  disabled={Boolean(resolvingAction)}
                  onClick={() => void onResolve(action)}
                >
                  {resolvingAction === action
                    ? `${getConflictResolutionActionLabel(action)}…`
                    : getConflictResolutionActionLabel(action)}
                </button>
              </article>
            ))}
          </div>
        </section>

        <div className={styles.footer}>
          <button
            className={styles.secondaryAction}
            type="button"
            disabled={Boolean(resolvingAction)}
            onClick={onClose}
          >
            Back to trip list
          </button>
        </div>
      </div>
    </div>
  );
}
