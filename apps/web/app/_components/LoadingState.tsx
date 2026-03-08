import styles from './LoadingState.module.css';

type Props = {
  label?: string;
};

export function LoadingState({ label = 'Loading…' }: Props) {
  return (
    <div className={styles.container} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
    </div>
  );
}
