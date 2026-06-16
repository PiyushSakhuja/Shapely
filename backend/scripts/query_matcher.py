"""
query_matcher.py
────────────────
Usage:
    python query_matcher.py <image_path>

Examples:
    python query_matcher.py my_photo.jpg       # real photo  → GrabCut pipeline
    python query_matcher.py my_sketch.png      # hand-drawn  → threshold pipeline

What it does:
    1. Auto-detects whether the query is a sketch or a real photo
    2. Extracts the silhouette contour using the same pipeline as shape_indexer.py
    3. Compares against shape_database.json in two stages:
         Stage 1 — Fourier L2      : runs on ALL records, eliminates obvious mismatches
         Stage 2 — Hausdorff dist  : runs on top 50 from stage 1, gives accurate ranking
    4. Displays results in order — best shape match first

Requires:
    pip install opencv-python numpy matplotlib scipy
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import json
import sys
import os
from scipy.spatial.distance import directed_hausdorff

# ── Must match shape_indexer.py exactly ───────────────────────────────────────
IMG_SIZE      = (500, 500)
N_CONTOUR_PTS = 128
N_FOURIER     = 32
DB_PATH       = "image_database/shape_database.json"
query_path = "query1.png"

# ── Matching config ───────────────────────────────────────────────────────────
SHORTLIST_N = 50   # how many candidates survive the Fourier pass
RESULTS_N   = 10   # how many final results to show


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════════════════════

def load_database(db_path=DB_PATH):
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Database '{db_path}' not found.\n"
            "Run shape_indexer.py first to build it."
        )
    with open(db_path) as f:
        db = json.load(f)
    records = db.get("images", [])
    print(f"✓ Loaded {len(records)} records from '{db_path}'")
    return records


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED UTILITIES  (identical to shape_indexer.py)
# ══════════════════════════════════════════════════════════════════════════════

def resample_contour(pts, n=N_CONTOUR_PTS):
    """Resample an (M,2) contour to exactly n evenly-spaced points by arc length."""
    diffs  = np.diff(pts, axis=0)
    dists  = np.hypot(diffs[:, 0], diffs[:, 1])
    cumlen = np.concatenate([[0], np.cumsum(dists)])
    total  = cumlen[-1]
    if total == 0:
        return pts
    targets = np.linspace(0, total, n, endpoint=False)
    rx = np.interp(targets, cumlen, pts[:, 0])
    ry = np.interp(targets, cumlen, pts[:, 1])
    return np.stack([rx, ry], axis=1)


def normalize_contour(pts_pixel):
    """
    Translate to origin, then scale to [0, 1].
    Returns (pts_norm, min_xy, span) so we can reverse it for visualization.
    """
    pts   = pts_pixel.copy().astype(float)
    min_xy = pts.min(axis=0)
    pts   -= min_xy
    span   = pts.max()
    if span == 0:
        return None, None, None
    pts /= span
    return pts, min_xy, span


def compute_fourier_descriptor(pts_norm, n_components=N_FOURIER):
    """
    Translation / rotation / scale invariant Fourier descriptor.
    Treat (x, y) as complex numbers, FFT, drop DC, take magnitudes, normalise.
    """
    z    = pts_norm[:, 0] + 1j * pts_norm[:, 1]
    Z    = np.fft.fft(z)
    desc = np.abs(Z[1 : n_components + 1])
    if desc[0] != 0:
        desc = desc / desc[0]
    return desc


def find_main_contour(mask, min_area_frac=0.02):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < mask.shape[0] * mask.shape[1] * min_area_frac:
        return None
    return c


# ══════════════════════════════════════════════════════════════════════════════
#  QUERY PROCESSING  (auto-detects sketch vs photo)
# ══════════════════════════════════════════════════════════════════════════════

def is_sketch(img):
    """
    A sketch is mostly white/light background with dark strokes.
    If >60 % of pixels are brighter than 200, call it a sketch.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray > 200)) > 0.60


def build_mask_from_sketch(resized):
    """
    Sketch pipeline:
      invert → threshold → dilate (connect broken strokes) → fill interior
    No GrabCut needed — the background is already white.
    """
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # Invert so drawn strokes become white (foreground)
    inv = cv2.bitwise_not(gray)

    # Threshold: anything that isn't background becomes white
    _, thresh = cv2.threshold(inv, 25, 255, cv2.THRESH_BINARY)

    # Dilate to bridge small gaps in freehand strokes
    k       = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    dilated = cv2.dilate(thresh, k, iterations=2)

    # Fill the interior of the shape so we get a solid silhouette
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled      = np.zeros_like(dilated)
    cv2.drawContours(filled, contours, -1, 255, cv2.FILLED)

    # Final smooth
    filled = cv2.morphologyEx(filled, cv2.MORPH_CLOSE, k)
    return filled


def build_mask_from_photo(resized):
    """
    Photo pipeline: GrabCut to isolate the main subject.
    Identical to shape_indexer.py so query and database are processed the same way.
    """
    h, w      = resized.shape[:2]
    margin    = int(min(h, w) * 0.10)
    mask      = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    rect      = (margin, margin, w - 2 * margin, h - 2 * margin)

    cv2.grabCut(resized, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    fg = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)

    k  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, k)
    return fg


def process_query_image(image_path):
    """
    Full query processing pipeline.

    Returns a dict:
        pts_pixel   — (128, 2) contour in pixel coords  →  for drawing overlays
        pts_norm    — (128, 2) contour in [0, 1]        →  for matching
        fourier     — (32,)   descriptor vector
        fg_mask     — binary mask (for visualization)
        resized     — 500×500 BGR image
        image_type  — "sketch" or "photo"
    Returns None on failure.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: '{image_path}'")

    resized    = cv2.resize(img, IMG_SIZE)
    image_type = "sketch" if is_sketch(resized) else "photo"
    print(f"  Detected type  : {image_type}")

    fg_mask = (build_mask_from_sketch(resized)
               if image_type == "sketch"
               else build_mask_from_photo(resized))

    raw_cnt = find_main_contour(fg_mask)
    if raw_cnt is None:
        print("  ERROR: Could not find a usable contour in the query image.")
        print("  Tip: make sure the subject fills at least ~10% of the image.")
        return None

    # Simplify with Douglas-Peucker
    eps        = 0.002 * cv2.arcLength(raw_cnt, True)
    simplified = cv2.approxPolyDP(raw_cnt, eps, True)

    # ── Keep pixel coords separate from normalized coords ──────────────────────
    #    (same pattern as shape_indexer.py to guarantee correct overlay alignment)
    pts_pixel = simplified.reshape(-1, 2).astype(float)
    pts_pixel = resample_contour(pts_pixel, N_CONTOUR_PTS)

    pts_norm, _, _ = normalize_contour(pts_pixel)
    if pts_norm is None:
        return None

    fourier = compute_fourier_descriptor(pts_norm)

    print(f"  Contour points : {N_CONTOUR_PTS}")
    print(f"  Area fraction  : {cv2.contourArea(raw_cnt) / (IMG_SIZE[0]*IMG_SIZE[1]):.3f}")

    return {
        "pts_pixel":  pts_pixel,
        "pts_norm":   pts_norm,
        "fourier":    fourier,
        "fg_mask":    fg_mask,
        "resized":    resized,
        "image_type": image_type,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  DISTANCE METRICS
# ══════════════════════════════════════════════════════════════════════════════

def fourier_distance(desc_a, desc_b):
    """
    L2 distance between two Fourier descriptor vectors.
    Very fast (32 numbers), good for eliminating bad matches.
    Already invariant to rotation, scale, translation, and starting point.
    """
    return float(np.linalg.norm(desc_a - desc_b))


def hausdorff_distance(pts_a, pts_b):
    """
    Symmetric Hausdorff distance between two normalized contours.

    For each point in A it finds the nearest point in B (not by index — by
    actual nearest-neighbor search), and vice versa.  Takes the max of both
    directed distances.

    This means:
      - Order / starting-point invariant  ✓
      - Scale invariant (both contours in [0,1])  ✓
      - Sensitive to local shape differences  ✓
      - Penalizes outlier mismatches  ✓
    """
    d_ab = directed_hausdorff(pts_a, pts_b)[0]
    d_ba = directed_hausdorff(pts_b, pts_a)[0]
    return max(d_ab, d_ba)


# ══════════════════════════════════════════════════════════════════════════════
#  TWO-STAGE MATCHING
# ══════════════════════════════════════════════════════════════════════════════

def match_against_database(query, db_records,
                            shortlist_n=SHORTLIST_N,
                            results_n=RESULTS_N):
    """
    Stage 1 — Fourier L2 on every record in the database.
              Runs in milliseconds even for 100k records (just 32 multiplications each).
              Returns the top shortlist_n candidates.

    Stage 2 — Hausdorff distance on the shortlisted candidates only.
              More expensive but far more accurate for fine shape discrimination.
              Returns the top results_n candidates sorted best → worst.

    Returns a list of dicts:
        {
          "record"             : the database record dict,
          "fourier_distance"   : float,
          "hausdorff_distance" : float,   ← primary sort key
        }
    """
    query_fourier = np.array(query["fourier"])
    query_pts     = np.array(query["pts_norm"])

    # ── Stage 1: Fourier ───────────────────────────────────────────────────────
    print(f"\n  Stage 1 — Fourier pass on {len(db_records)} records ...", end=" ", flush=True)

    scored = []
    for record in db_records:
        db_vec = np.array(record["fourier_descriptor"])
        dist   = fourier_distance(query_fourier, db_vec)
        scored.append((dist, record))

    scored.sort(key=lambda x: x[0])
    shortlisted = scored[:shortlist_n]
    print(f"shortlisted top {len(shortlisted)}")

    # ── Stage 2: Hausdorff ─────────────────────────────────────────────────────
    print(f"  Stage 2 — Hausdorff pass on {len(shortlisted)} candidates ...", end=" ", flush=True)

    results = []
    for fourier_dist, record in shortlisted:
        db_pts = np.array(record["contour_normalized"])
        h_dist = hausdorff_distance(query_pts, db_pts)
        results.append({
            "record":             record,
            "fourier_distance":   round(fourier_dist,  5),
            "hausdorff_distance": round(h_dist,         5),
        })

    results.sort(key=lambda x: x["hausdorff_distance"])
    print("done")

    return results[:results_n]


# ══════════════════════════════════════════════════════════════════════════════
#  VISUALISATION
# ══════════════════════════════════════════════════════════════════════════════

def draw_contour_overlay(img_bgr, pts_pixel, color=(0, 220, 0)):
    """Draw contour polyline + sample dots on a copy of img_bgr."""
    out      = img_bgr.copy()
    pts_draw = pts_pixel.reshape(-1, 1, 2).astype(np.int32)
    cv2.polylines(out, [pts_draw], isClosed=True, color=color, thickness=2)
    for pt in pts_pixel[::8]:
        cv2.circle(out, (int(pt[0]), int(pt[1])), 5, (0, 80, 255), -1)
    return out


def score_to_stars(h_dist, max_dist=0.3):
    """Convert a Hausdorff distance to a 1–5 star rating."""
    ratio = min(h_dist / max_dist, 1.0)
    stars = round(5 * (1 - ratio))
    return "★" * max(stars, 1) + "☆" * (5 - max(stars, 1))


def visualize_matches(query_path, query_result, matches):
    """
    Layout
    ──────
    Top band  : Query image | Mask | Contour overlay | Shape fingerprint
    Separator : title bar
    Grid      : matched images with contour overlay + score labels
    """
    n    = len(matches)
    cols = min(5, n) if n > 0 else 1
    rows = max(1, (n + cols - 1) // cols)

    fig_h = 5.2 + rows * 4.4
    fig   = plt.figure(figsize=(20, fig_h), facecolor="#f4f4f4")

    q_top    = 1.00
    q_bottom = 1.00 - (5.0 / fig_h)

    # ── Query band ────────────────────────────────────────────────────────────
    gs_q = fig.add_gridspec(1, 4,
                             left=0.02, right=0.98,
                             top=q_top - 0.01, bottom=q_bottom + 0.01,
                             wspace=0.04)

    axq = [fig.add_subplot(gs_q[i]) for i in range(4)]

    axq[0].imshow(cv2.cvtColor(query_result["resized"], cv2.COLOR_BGR2RGB))
    axq[0].set_title("Query image", fontsize=10, fontweight="bold")

    axq[1].imshow(query_result["fg_mask"], cmap="gray")
    axq[1].set_title(f"Mask ({query_result['image_type']})", fontsize=10)

    overlay_q = draw_contour_overlay(query_result["resized"], query_result["pts_pixel"])
    axq[2].imshow(cv2.cvtColor(overlay_q, cv2.COLOR_BGR2RGB))
    axq[2].set_title(f"Contour  ({N_CONTOUR_PTS} pts)", fontsize=10)

    pn = query_result["pts_norm"]
    axq[3].plot(pn[:, 0], 1 - pn[:, 1], "g-", lw=1.5)
    axq[3].plot(pn[::8, 0], 1 - pn[::8, 1], "bo", ms=3)
    axq[3].set_title("Shape fingerprint", fontsize=10)
    axq[3].set_aspect("equal")
    axq[3].set_xlim(-0.05, 1.05)
    axq[3].set_ylim(-0.05, 1.05)

    for ax in axq:
        ax.axis("off")

    # ── Separator label ───────────────────────────────────────────────────────
    sep_y = q_bottom - 0.01
    fig.text(0.5, sep_y,
             f"Top {n} shape matches  —  sorted by Hausdorff distance  (lower = better match)",
             ha="center", va="top",
             fontsize=11, fontweight="bold", color="#333333",
             bbox=dict(facecolor="#e0e0e0", edgecolor="none", pad=4))

    # ── Results grid ──────────────────────────────────────────────────────────
    grid_top    = sep_y - 0.045
    grid_bottom = 0.02

    gs_r = fig.add_gridspec(rows, cols,
                             left=0.02, right=0.98,
                             top=grid_top, bottom=grid_bottom,
                             wspace=0.06, hspace=0.40)

    for i, match in enumerate(matches):
        row_i, col_i = divmod(i, cols)
        ax = fig.add_subplot(gs_r[row_i, col_i])
        ax.set_facecolor("#dddddd")

        record = match["record"]
        h_dist = match["hausdorff_distance"]
        f_dist = match["fourier_distance"]

        img_bgr = cv2.imread(record["path"])

        if img_bgr is not None:
            img_r = cv2.resize(img_bgr, IMG_SIZE)

            # Draw the database silhouette over the matched image in orange.
            # NOTE: the normalized contour is scaled to fill [0,1] — so
            # multiplying by 500 stretches the shape to fill the frame.
            # It shows the SHAPE geometry, not the exact pixel position.
            db_pts_px  = np.array(record["contour_normalized"]) * 500
            pts_draw   = db_pts_px.reshape(-1, 1, 2).astype(np.int32)
            cv2.polylines(img_r, [pts_draw], True, (0, 140, 255), 2)

            ax.imshow(cv2.cvtColor(img_r, cv2.COLOR_BGR2RGB))
        else:
            ax.text(0.5, 0.5, "File not found",
                    ha="center", va="center",
                    transform=ax.transAxes, fontsize=9, color="#888")

        stars = score_to_stars(h_dist)
        ax.set_title(
            f"#{i+1}  {record['filename']}\n"
            f"{stars}   Haus: {h_dist:.4f}   Four: {f_dist:.4f}",
            fontsize=7.5, pad=3, linespacing=1.4
        )
        ax.axis("off")

    # Fill empty grid cells
    total_cells = rows * cols
    for j in range(n, total_cells):
        r, c = divmod(j, cols)
        fig.add_subplot(gs_r[r, c]).axis("off")

    # ── Save + show ───────────────────────────────────────────────────────────
    out_file = "match_results.png"
    plt.savefig(out_file, dpi=130, bbox_inches="tight")
    print(f"\n  Saved visualization → {out_file}")
    plt.show()


# ══════════════════════════════════════════════════════════════════════════════
#  RESULTS TABLE (terminal)
# ══════════════════════════════════════════════════════════════════════════════

def print_results_table(matches):
    w = 32
    print(f"\n  {'#':>3}  {'File':<{w}}  {'Hausdorff':>10}  {'Fourier':>10}  Match")
    print("  " + "─" * (w + 36))
    for i, m in enumerate(matches, 1):
        stars = score_to_stars(m["hausdorff_distance"])
        print(
            f"  {i:>3}  {m['record']['filename']:<{w}}  "
            f"{m['hausdorff_distance']:>10.5f}  "
            f"{m['fourier_distance']:>10.5f}  "
            f"{stars}"
        )
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # if len(sys.argv) < 2:
    #     print(__doc__)
    #     sys.exit(0)

    # query_path = sys.argv[1]
    # if not os.path.exists(query_path):
    #     print(f"Error: '{query_path}' not found.")
    #     sys.exit(1)

    print(f"\n{'═'*52}")
    print(f"  Shape Query Matcher")
    print(f"{'═'*52}")
    print(f"  Query  : {query_path}")
    print(f"  DB     : {DB_PATH}")
    print(f"{'─'*52}")

    # 1. Load the database built by shape_indexer.py
    db_records = load_database()
    if not db_records:
        print("Database is empty — run shape_indexer.py first.")
        sys.exit(1)

    # 2. Process query image (auto-detects sketch vs photo)
    print("\n  Processing query image ...")
    query = process_query_image(query_path)
    if query is None:
        print("  Failed to extract contour. Exiting.")
        sys.exit(1)

    # 3. Run two-stage matching
    print("\n  Running two-stage shape matching ...")
    matches = match_against_database(query, db_records,
                                      shortlist_n=SHORTLIST_N,
                                      results_n=RESULTS_N)

    # 4. Print table to terminal
    print_results_table(matches)

    # 5. Show visual results
    visualize_matches(query_path, query, matches)


if __name__ == "__main__":
    main()