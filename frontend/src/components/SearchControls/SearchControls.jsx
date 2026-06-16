import styles from "./SearchControls.module.css";

function IconSearch() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

function IconUndo() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 14 4 9l5-5" />
      <path d="M4 9h11a5 5 0 0 1 0 10h-3" />
    </svg>
  );
}

function IconClear() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6 18 20a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  );
}

export default function SearchControls({
  onSearch,
  onClear,
  onUndo,
  brushSize,
  onBrushChange,
  canSearch,
  isSearching,
  isEmpty,
}) {
  return (
    <div className={styles.controls}>
      <div className={styles.brushGroup}>
        <label htmlFor="brush" className={styles.brushLabel}>
          Brush
        </label>
        <input
          id="brush"
          type="range"
          min="2"
          max="20"
          step="1"
          value={brushSize}
          onChange={(e) => onBrushChange(Number(e.target.value))}
          className={styles.brushSlider}
          aria-label="Brush size"
        />
        <span className={styles.brushValue}>{brushSize}px</span>
      </div>

      <div className={styles.buttonGroup}>
        <button
          type="button"
          className={styles.ghost}
          onClick={onUndo}
          disabled={isEmpty || isSearching}
        >
          <IconUndo />
          Undo
        </button>
        <button
          type="button"
          className={styles.ghost}
          onClick={onClear}
          disabled={isEmpty || isSearching}
        >
          <IconClear />
          Clear
        </button>
        <button
          type="button"
          className={styles.primary}
          onClick={onSearch}
          disabled={!canSearch || isSearching}
        >
          <IconSearch />
          {isSearching ? "Searching…" : "Search shapes"}
        </button>
      </div>
    </div>
  );
}