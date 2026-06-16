import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
FOLDER         = "images"
DB_PATH        = "image_database/shape_database.json"
IMG_SIZE       = (500, 500)
N_CONTOUR_PTS  = 128          # points per contour after resampling
N_FOURIER      = 32           # fourier descriptor length
MIN_AREA_FRAC  = 0.02         # subject must fill at least 2% of frame


# ── Step 1: Background removal ────────────────────────────────────────────────

def extract_foreground_mask(img):
    """
    GrabCut background removal.
    Returns a binary mask (255 = foreground, 0 = background).
    """
    h, w   = img.shape[:2]
    margin = int(min(h, w) * 0.10)

    mask      = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # Tell GrabCut the subject is roughly inside the central 80%
    rect = (margin, margin, w - 2 * margin, h - 2 * margin)
    cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

    fg = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)

    # Morphological cleanup: close holes, remove noise specks
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  kernel)

    return fg


# ── Step 2: Contour extraction ────────────────────────────────────────────────

def find_main_contour(fg_mask):
    """
    Find the single largest contour from the binary mask.
    Rejects contours that are too small (likely noise).
    """
    contours, _ = cv2.findContours(
        fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)

    total_px = fg_mask.shape[0] * fg_mask.shape[1]
    if cv2.contourArea(c) < total_px * MIN_AREA_FRAC:
        return None

    return c


# ── Step 3: Resampling ────────────────────────────────────────────────────────

def resample_contour(pts, n=N_CONTOUR_PTS):
    """
    Resample an (M, 2) contour to exactly n evenly-spaced points
    by arc length. This is critical — two contours with different
    point counts can't be compared directly.
    """
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


# ── Step 4: Shape descriptor ──────────────────────────────────────────────────

def compute_fourier_descriptor(pts_norm, n_components=N_FOURIER):
    """
    Rotation / scale / translation invariant Fourier descriptor.

    How it works:
      - Treat each (x, y) point as a complex number x + iy
      - Take the FFT of the resulting complex signal
      - Drop DC component (makes it translation-invariant)
      - Take magnitudes (makes it rotation-invariant)
      - Divide by first coefficient (makes it scale-invariant)

    Input : normalized (n, 2) contour in [0, 1]
    Output: n_components floats ready for distance comparison
    """
    z    = pts_norm[:, 0] + 1j * pts_norm[:, 1]
    Z    = np.fft.fft(z)
    desc = np.abs(Z[1 : n_components + 1])   # skip DC, take magnitudes
    if desc[0] != 0:
        desc = desc / desc[0]                 # scale invariant
    return desc


# ── Step 5: Full pipeline for one image ───────────────────────────────────────

def process_image(image_path):
    """
    Runs the complete pipeline on one image.

    Returns a dict with:
      pts_pixel  — (128, 2) contour in pixel coordinates  → for overlay drawing
      pts_norm   — (128, 2) contour in [0, 1]             → for matching
      fourier    — (32,)  descriptor                       → for fast search
      fg_mask    — binary mask                             → for visualisation
      resized    — 500×500 BGR image                       → for visualisation
      area_ratio — fraction of frame the subject fills
      perimeter  — contour perimeter in pixels

    Returns None on failure.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    resized = cv2.resize(img, IMG_SIZE)

    # 1. Background removal
    fg_mask = extract_foreground_mask(resized)

    # 2. Main contour
    raw_cnt = find_main_contour(fg_mask)
    if raw_cnt is None:
        return None

    # 3. Douglas-Peucker simplification
    eps        = 0.002 * cv2.arcLength(raw_cnt, True)
    simplified = cv2.approxPolyDP(raw_cnt, eps, True)

    # ── pts_pixel: raw pixel coordinates (used ONLY for drawing overlays) ──
    pts_pixel = simplified.reshape(-1, 2).astype(float)
    pts_pixel = resample_contour(pts_pixel, N_CONTOUR_PTS)

    # ── pts_norm: translate → scale → [0, 1]  (used for matching & storage) ──
    #
    # WHY KEEP THEM SEPARATE?
    # Normalisation shifts and rescales the points, so you can't simply
    # multiply pts_norm back by 500 to get pixel positions.
    # Keeping pts_pixel untouched gives perfect overlay alignment.
    #
    pts_norm = pts_pixel.copy()
    pts_norm -= pts_norm.min(axis=0)     # translate: move top-left corner to origin
    span = pts_norm.max()                # largest coordinate value (x or y)
    if span == 0:
        return None
    pts_norm /= span                     # scale: squeeze everything into [0, 1]

    # 4. Fourier descriptor
    fourier = compute_fourier_descriptor(pts_norm)

    # 5. Metadata
    area_px  = float(cv2.contourArea(raw_cnt))
    perim_px = float(cv2.arcLength(raw_cnt, True))
    h, w     = resized.shape[:2]

    return {
        "pts_pixel":  pts_pixel,
        "pts_norm":   pts_norm,
        "fourier":    fourier,
        "fg_mask":    fg_mask,
        "resized":    resized,
        "area_ratio": area_px / (h * w),
        "perimeter":  perim_px,
    }


# ── Step 6: Visualisation (alignment-correct) ─────────────────────────────────

def visualize_result(result, image_path):
    """
    4-panel figure:
      [0] Original image
      [1] GrabCut binary mask
      [2] Contour overlay — drawn with pts_pixel so it lines up perfectly
      [3] Normalised shape fingerprint (abstract, for inspection)
    """
    resized   = result["resized"]
    fg_mask   = result["fg_mask"]
    pts_pixel = result["pts_pixel"]
    pts_norm  = result["pts_norm"]

    # ── Panel 3: overlay ──────────────────────────────────────────────────────
    overlay  = resized.copy()

    # cv2.polylines needs shape (N, 1, 2) dtype int32
    pts_draw = pts_pixel.reshape(-1, 1, 2).astype(np.int32)
    cv2.polylines(overlay, [pts_draw], isClosed=True, color=(0, 220, 0), thickness=2)

    # Every 8th point as a dot so we can see the sampling density
    for pt in pts_pixel[::8]:
        cv2.circle(overlay, (int(pt[0]), int(pt[1])), 5, (0, 80, 255), -1)

    # ── Layout ────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    fig.suptitle(os.path.basename(image_path), fontsize=13, fontweight="bold")

    axes[0].imshow(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Original")
    axes[0].axis("off")

    axes[1].imshow(fg_mask, cmap="gray")
    axes[1].set_title("GrabCut mask")
    axes[1].axis("off")

    axes[2].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    axes[2].set_title(f"Contour overlay ({N_CONTOUR_PTS} pts)")
    axes[2].axis("off")

    # Flip y-axis: image y goes DOWN, matplotlib y goes UP
    axes[3].plot(pts_norm[:, 0],  1 - pts_norm[:, 1],  "g-",  linewidth=1.5)
    axes[3].plot(pts_norm[::8, 0], 1 - pts_norm[::8, 1], "bo", markersize=4)
    axes[3].set_title("Shape fingerprint (normalised)")
    axes[3].set_aspect("equal")
    axes[3].set_xlim(-0.05, 1.05)
    axes[3].set_ylim(-0.05, 1.05)
    axes[3].axis("off")

    plt.tight_layout()
    plt.show()


# ── Step 7: JSON database ─────────────────────────────────────────────────────

def load_database(db_path=DB_PATH):
    """Load existing database, or return empty list if none exists."""
    if not os.path.exists(db_path):
        return []
    with open(db_path, "r") as f:
        db = json.load(f)
    return db.get("images", [])


def save_database(records, db_path=DB_PATH):
    """
    Write all records to JSON.

    Schema per record:
      id                  — integer index
      filename            — e.g. "leaf.jpg"
      path                — relative path used to read the image
      contour_normalized  — list of 128 [x, y] pairs, all in [0, 1]
                            used for accurate Procrustes / Hausdorff matching
      fourier_descriptor  — list of 32 floats
                            used for fast nearest-neighbour search
      area_ratio          — 0-1, how much of the frame the subject fills
      perimeter           — contour length in pixels (500×500 space)
    """
    db = {
        "created":    datetime.now().isoformat(timespec="seconds"),
        "img_size":   list(IMG_SIZE),
        "n_pts":      N_CONTOUR_PTS,
        "n_fourier":  N_FOURIER,
        "count":      len(records),
        "images":     records,
    }
    with open(db_path, "w") as f:
        json.dump(db, f, indent=2)
    print(f"\n✓  Saved {len(records)} records → {db_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [
        f for f in os.listdir(FOLDER)
        if os.path.splitext(f)[1].lower() in exts
    ]
    total = len(files)
    print(f"Found {total} image(s) in '{FOLDER}'\n")

    # Load any records already in the DB so we can append / skip
    existing_db    = load_database()
    existing_paths = {r["path"] for r in existing_db}
    records        = list(existing_db)   # start with what we already have
    failed         = []

    for i, filename in enumerate(files, 1):
        path = os.path.join(FOLDER, filename)
        print(f"[{i}/{total}]  {filename} ... ", end="", flush=True)

        # Skip images already in the database
        if path in existing_paths:
            print("already indexed, skipping.")
            continue

        result = process_image(path)

        if result is None:
            print("FAILED  (bad segmentation or subject too small)")
            failed.append(filename)
            continue

        ar = result["area_ratio"]
        print(f"OK  (area={ar:.2f})")

        # Visualise
        visualize_result(result, path)

        # Append JSON-serialisable record
        records.append({
            "id":                   len(records),
            "filename":             filename,
            "path":                 path,
            "contour_normalized":   result["pts_norm"].tolist(),   # [[x,y], ...]
            "fourier_descriptor":   result["fourier"].tolist(),    # [f0, f1, ...]
            "area_ratio":           round(float(ar), 4),
            "perimeter":            round(float(result["perimeter"]), 2),
        })

    save_database(records)

    print(f"\n{'─'*50}")
    print(f"  Indexed : {len(records) - len(existing_db)} new image(s)")
    print(f"  Total   : {len(records)} in database")
    if failed:
        print(f"  Failed  : {len(failed)}  → {failed}")
    print(f"  DB file : {DB_PATH}")
    print(f"{'─'*50}\n")


if __name__ == "__main__":
    main()