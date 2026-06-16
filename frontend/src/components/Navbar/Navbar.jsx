import styles from "./Navbar.module.css";

export default function Navbar() {
  return (
    <header className={styles.navbar}>
      <div className={styles.inner}>
        <a href="/" className={styles.brand} aria-label="Shapely home">
          <span className={styles.logoMark} aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 18 L12 4 L20 18 Z" />
              <circle cx="12" cy="14" r="3" />
            </svg>
          </span>
          <span className={styles.brandText}>
            Shapely<span className={styles.brandDot}>.</span>
          </span>
        </a>

        <nav className={styles.nav} aria-label="Primary">
          <a href="#how" className={styles.link}>How it works</a>
          <a href="#about" className={styles.link}>About</a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className={styles.cta}
          >
            Get API access
          </a>
        </nav>
      </div>
    </header>
  );
}