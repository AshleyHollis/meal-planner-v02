import styles from './ErrorState.module.css';

type Props = {
  message?: string;
  onRetry?: () => void;
};

export function ErrorState({
  message = 'Something went wrong.',
  onRetry,
}: Props) {
  return (
    <div className={styles.container} role="alert">
      <span className={styles.icon} aria-hidden="true">⚠️</span>
      <p className={styles.message}>{message}</p>
      {onRetry && (
        <button className={styles.retryButton} onClick={onRetry} type="button">
          Try again
        </button>
      )}
    </div>
  );
}
