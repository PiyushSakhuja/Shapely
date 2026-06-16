import { useRef, useState } from "react";
import Navbar from "../../components/Navbar/Navbar";
import DrawingCanvas from "../../components/DrawingCanvas/DrawingCanvas";
import SearchControls from "../../components/SearchControls/SearchControls";
import ResultsGrid from "../../components/ResultsGrid/ResultsGrid";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import EmptyState from "../../components/EmptyState/EmptyState";
import { searchSimilarShapes } from "../../services/api";
import styles from "./Home.module.css";

export default function Home() {
  const canvasRef = useRef(null);
  const [brushSize, setBrushSize] = useState(6);
  const [isEmpty, setIsEmpty] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null); // null = no search yet
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!canvasRef.current || canvasRef.current.isEmpty()) return;
    setError(null);
    setIsSearching(true);
    try {
      const blob = await canvasRef.current.exportPng();
      console.log("sending data to backend");
      
      const data = await searchSimilarShapes(blob);
      console.log("data received from backend");
      
      console.log(data);
      setResults(data);
    } catch (err) {
      console.error(err);
      setError(err.message || "Search failed.");
      setResults(null);
    } finally {
      setIsSearching(false);
    }
    // const blob = await canvasRef.current.exportPng();
    // console.log(blob);

  };

  const handleClear = () => {
    canvasRef.current?.clear();
  };

  const handleUndo = () => {
    canvasRef.current?.undo();
  };

  const showInitialEmpty = results === null && !error;

  return (
    <div className={styles.page}>
      <Navbar />

      <main className={styles.main}>
        <section className={styles.hero}>
          <span className={styles.eyebrow}>Shape-based image search</span>
          <h1 className={styles.title}>
            Sketch a shape.
            <br />
            <span className={styles.gradient}>Find images that match.</span>
          </h1>
          <p className={styles.lede}>
            Draw a rough silhouette on the canvas and we'll surface visually
            similar images using contour-based matching.
          </p>
        </section>

        <section className={styles.canvasSection}>
          <div className={styles.canvasWrap}>
            <DrawingCanvas
              ref={canvasRef}
              brushSize={brushSize}
              onChange={(state) => setIsEmpty(state.isEmpty)}
            />
            {isSearching && <LoadingOverlay />}
          </div>

          <SearchControls
            brushSize={brushSize}
            onBrushChange={setBrushSize}
            onSearch={handleSearch}
            onClear={handleClear}
            onUndo={handleUndo}
            canSearch={!isEmpty}
            isSearching={isSearching}
            isEmpty={isEmpty}
          />
        </section>

        {error && (
          <EmptyState
            variant="error"
            message={error}
            onRetry={handleSearch}
          />
        )}

        {!error && showInitialEmpty && <EmptyState />}

        {!error && results && results.length > 0 && (
          <ResultsGrid results={results} />
        )}

        {!error && results && results.length === 0 && (
          <EmptyState
            title="No matches found"
            message="Try a different shape or a thicker brush."
          />
        )}
      </main>

      <footer className={styles.footer}>
        <p>Built with React + Vite · Shape similarity powered by FastAPI</p>
      </footer>
    </div>
  );
}