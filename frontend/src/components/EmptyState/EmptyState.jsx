import styles from "./EmptyState.module.css";

export default function EmptyState({
  variant = "empty",
  title,
  message,
  onRetry,
}) {
  const isError = variant === "error";
  return (
    <div className={`${styles.wrap} ${isError ? styles.error : ""}`}>
      <div className={styles.icon} aria-hidden="true">
        {isError ? (
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v5" />
            <path d="M12 16h.01" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 17.5V21h3.5L17 10.5 13.5 7 3 17.5z" />
            <path d="m14.5 6 3.5 3.5" />
          </svg>
        )}
      </div>
      <h3 className={styles.title}>
        {title || (isError ? "Something went wrong" : "Draw a shape to begin")}
      </h3>
      <p className={styles.message}>
        {message ||
          (isError
            ? "We couldn't reach the search service. Please try again."
            : "Draw a shape and start searching.")}
      </p>
      {isError && onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}