import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import styles from "./DrawingCanvas.module.css";

/**
 * DrawingCanvas
 * Exposes via ref:
 *   - clear()
 *   - undo()
 *   - isEmpty()
 *   - exportPng()  -> Promise<Blob>  (PNG blob for backend submission)
 */
const DrawingCanvas = forwardRef(function DrawingCanvas(
  { brushSize = 6, onChange },
  ref,
) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const ctxRef = useRef(null);
  const drawingRef = useRef(false);
  const lastPointRef = useRef(null);
  const currentStrokeRef = useRef(null);

  // Strokes are stored as arrays of points (in CSS pixels) so we can redraw
  // crisply at any DPR and support undo without rasterized history.
  const [strokes, setStrokes] = useState([]);
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;

  const setupCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const rect = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#0f172a";
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, rect.width, rect.height);
    ctxRef.current = ctx;

    // Redraw existing strokes
    for (const stroke of strokesRef.current) {
      drawStroke(ctx, stroke);
    }
  }, []);

  useEffect(() => {
    setupCanvas();
    const handleResize = () => setupCanvas();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [setupCanvas]);

  const drawStroke = (ctx, stroke) => {
    if (!stroke || stroke.points.length === 0) return;
    ctx.lineWidth = stroke.size;
    ctx.beginPath();
    const [first, ...rest] = stroke.points;
    ctx.moveTo(first.x, first.y);
    if (rest.length === 0) {
      // single point -> dot
      ctx.lineTo(first.x + 0.01, first.y + 0.01);
    } else {
      for (const p of rest) ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  };

  const getPos = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const point = e.touches ? e.touches[0] : e;
    return {
      x: point.clientX - rect.left,
      y: point.clientY - rect.top,
    };
  };

  const startDraw = (e) => {
    e.preventDefault();
    drawingRef.current = true;
    const pos = getPos(e);
    lastPointRef.current = pos;
    currentStrokeRef.current = { size: brushSize, points: [pos] };

    const ctx = ctxRef.current;
    ctx.lineWidth = brushSize;
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    ctx.lineTo(pos.x + 0.01, pos.y + 0.01);
    ctx.stroke();
  };

  const moveDraw = (e) => {
    if (!drawingRef.current) return;
    e.preventDefault();
    const pos = getPos(e);
    const ctx = ctxRef.current;
    const last = lastPointRef.current;
    ctx.lineWidth = brushSize;
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    currentStrokeRef.current.points.push(pos);
    lastPointRef.current = pos;
  };

  const endDraw = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    if (currentStrokeRef.current) {
      const finished = currentStrokeRef.current;
      currentStrokeRef.current = null;
      setStrokes((prev) => {
        const next = [...prev, finished];
        onChange && onChange({ isEmpty: next.length === 0 });
        return next;
      });
    }
  };

  const redrawAll = (nextStrokes) => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (!canvas || !ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, rect.width, rect.height);
    for (const s of nextStrokes) drawStroke(ctx, s);
  };

  useImperativeHandle(ref, () => ({
    clear() {
      setStrokes([]);
      redrawAll([]);
      onChange && onChange({ isEmpty: true });
    },
    undo() {
      setStrokes((prev) => {
        const next = prev.slice(0, -1);
        redrawAll(next);
        onChange && onChange({ isEmpty: next.length === 0 });
        return next;
      });
    },
    isEmpty() {
      return strokesRef.current.length === 0;
    },
    /**
     * Export the current drawing as a PNG Blob.
     * Use this to send to the FastAPI backend for contour extraction.
     */
    exportPng() {
      return new Promise((resolve, reject) => {
        const canvas = canvasRef.current;
        if (!canvas) return reject(new Error("Canvas not ready"));
        canvas.toBlob(
          (blob) => {
            if (blob) resolve(blob);
            else reject(new Error("Failed to export canvas"));
          },
          "image/png",
        );
      });
    },
  }));

  return (
    <div
      ref={wrapRef}
      className={styles.wrap}
      role="application"
      aria-label="Drawing canvas"
    >
      <canvas
        ref={canvasRef}
        className={styles.canvas}
        onMouseDown={startDraw}
        onMouseMove={moveDraw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
        onTouchStart={startDraw}
        onTouchMove={moveDraw}
        onTouchEnd={endDraw}
      />
    </div>
  );
});

export default DrawingCanvas;