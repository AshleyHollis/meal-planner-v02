'use client';

import styles from './StaleDraftWarning.module.css';

type Props = {
  visible: boolean;
  acknowledged?: boolean;
  onAcknowledgeChange?: (acknowledged: boolean) => void;
};

export function StaleDraftWarning({
  visible,
  acknowledged = false,
  onAcknowledgeChange,
}: Props) {
  if (!visible) return null;

  return (
    <div className={styles.warning} role="alert">
      <span aria-hidden="true">⚠️</span>
      <div className={styles.content}>
        <p>
          <strong>This draft may be out of date.</strong> Your inventory or preferences have
          changed since this draft was created. You can still confirm it, but review or
          regenerate first if anything no longer fits.
        </p>
        {onAcknowledgeChange && (
          <label className={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => onAcknowledgeChange(event.target.checked)}
            />
            <span>I understand this draft may not reflect the latest household context.</span>
          </label>
        )}
      </div>
    </div>
  );
}
