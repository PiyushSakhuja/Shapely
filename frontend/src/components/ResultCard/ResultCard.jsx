import styles from "./ResultCard.module.css";

export default function ResultCard({ result, index = 0 }) {
  const pct = Math.round(result.score * 100);
  return (
    <article
      className={styles.card}
      style={{ animationDelay: `${Math.min(index, 11) * 40}ms` }}
    >
      <div className={styles.thumb}>
        <img
          src={result.imageUrl}
          alt={result.title}
          loading="lazy"
          draggable="false"
        />
        <span className={styles.badge}>{pct}% match</span>
      </div>
      <div className={styles.meta}>
        <h3 className={styles.title}>{result.title}</h3>
        <div className={styles.scoreBar} aria-hidden="true">
          <span style={{ width: `${pct}%` }} />
        </div>
      </div>
    </article>
  );
}