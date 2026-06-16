import ResultCard from "../ResultCard/ResultCard";
import styles from "./ResultsGrid.module.css";

export default function ResultsGrid({ results }) {
  return (
    <section className={styles.section} aria-label="Search results">
      <header className={styles.header}>
        <h2 className={styles.heading}>
          {results.length} similar {results.length === 1 ? "shape" : "shapes"}
        </h2>
        <p className={styles.sub}>
          Sorted by visual similarity to your drawing.
        </p>
      </header>
      <div className={styles.grid}>
        {results.map((r, i) => (
          <ResultCard key={r.id} result={r} index={i} />
        ))}
      </div>
    </section>
  );
}