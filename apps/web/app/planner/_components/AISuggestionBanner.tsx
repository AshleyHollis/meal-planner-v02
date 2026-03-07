'use client';

import { getSuggestionBannerDetail } from '../../_lib/planner-ui';
import type { AISuggestionStatus, FallbackMode } from '../../_lib/types';
import styles from './AISuggestionBanner.module.css';

const STATUS_CONFIG: Record<
  AISuggestionStatus,
  { icon: string; label: string; cls: string }
> = {
  idle: { icon: '💡', label: 'No suggestion yet', cls: styles.idle },
  generating: { icon: '⏳', label: 'Generating suggestions…', cls: styles.generating },
  ready: { icon: '✅', label: 'AI suggestion ready', cls: styles.ready },
  fallback_used: {
    icon: '⚠️',
    label: 'Suggestion used fallback guidance',
    cls: styles.fallback,
  },
  insufficient_context: {
    icon: '📭',
    label: 'Not enough context for a full suggestion',
    cls: styles.warn,
  },
  failed: { icon: '❌', label: 'Suggestion failed', cls: styles.failed },
};

type Props = {
  status: AISuggestionStatus;
  fallbackMode?: FallbackMode;
  hasConfirmedPlan?: boolean;
  isStale?: boolean;
  onOpenDraft?: () => void;
  onRequestNew?: () => void;
};

export function AISuggestionBanner({
  status,
  fallbackMode = 'none',
  hasConfirmedPlan = false,
  isStale,
  onOpenDraft,
  onRequestNew,
}: Props) {
  const config = STATUS_CONFIG[status];
  const detail = getSuggestionBannerDetail(status, fallbackMode, { hasConfirmedPlan });
  const canReview = (status === 'ready' || status === 'fallback_used') && onOpenDraft;
  const canRequest =
    (status === 'idle' || status === 'failed' || status === 'insufficient_context') &&
    onRequestNew;

  return (
    <div className={`${styles.banner} ${config.cls}`} role="status">
      <span className={styles.icon} aria-hidden="true">
        {config.icon}
      </span>
      <div className={styles.copy}>
        <span className={styles.label}>
          {config.label}
          {isStale && status !== 'generating' && <span className={styles.stale}> · Stale</span>}
        </span>
        {detail && <p className={styles.detail}>{detail}</p>}
      </div>
      <div className={styles.actions}>
        {canReview && (
          <button className={styles.primaryAction} onClick={onOpenDraft} type="button">
            Review suggestion
          </button>
        )}
        {canRequest && (
          <button className={styles.primaryAction} onClick={onRequestNew} type="button">
            Request AI suggestion
          </button>
        )}
      </div>
    </div>
  );
}
