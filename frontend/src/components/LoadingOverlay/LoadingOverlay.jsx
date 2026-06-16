import styles from "./LoadingOverlay.module.css";

export default function LoadingOverlay({
  message = "Searching for similar shapes...",
}) {
  return (
    <div className={styles.overlay} role="status" aria-live="polite">
      <div className={styles.card}>
        <div className={styles.spinner} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p className={styles.message}>{message}</p>
      </div>
    </div>
  );
}