# Shapely

**Draw a shape. Discover echoes in the world.**

Shapely is a contour-based image retrieval system that lets users sketch a rough shape and search for visually similar images based on **geometry**, not semantic meaning.

Unlike traditional image search engines that recognize objects ("heart", "tree", "mountain"), Shapely focuses on **visual silhouettes**. A rough heart sketch might return a heart-shaped cloud, a mountain gap, a leaf, or any naturally occurring structure with a similar outline.

---

## Demo

```text
User Sketch
     ↓
Contour Extraction
     ↓
Fourier Shape Descriptor
     ↓
Shape Database Search
     ↓
Hausdorff Re-ranking
     ↓
Top Matching Images
```

---

## Features

* 🎨 Freehand sketch canvas built with React
* 📤 Upload sketch directly to FastAPI backend
* 🔍 Automatic sketch/photo detection
* ✂️ Contour extraction and normalization
* 📐 Fourier descriptors for shape representation
* ⚡ Two-stage retrieval pipeline:

  * Fourier descriptor search
  * Hausdorff distance reranking
* 🖼️ Real-time image result display
* 🌿 Designed for discovering accidental or natural shape similarities

---

## Example

Draw:

```text
❤️
```

Possible results:

* ☁️ Heart-shaped cloud
* 🏔️ Mountain gap
* 🍃 Leaf silhouette
* 🌊 Ocean formation
* 🏛️ Architectural arch

The system searches by **shape**, not by object category.

---

## Tech Stack

### Frontend

* React
* Vite
* HTML Canvas API
* CSS Modules

### Backend

* FastAPI
* OpenCV
* NumPy

### Shape Matching

* Contour extraction
* Contour normalization
* Fourier descriptors
* Hausdorff distance
* Two-stage retrieval pipeline

---

## Project Structure

```text
shapely/

├── frontend/
│
│   ├── src/
│   │
│   ├── components/
│   │   ├── DrawingCanvas/
│   │   ├── ResultsGrid/
│   │   ├── SearchControls/
│   │   └── ...
│   │
│   ├── pages/
│   │   └── Home/
│   │
│   └── services/
│
└── backend/

    ├── app/

    │   ├── routes/
    │   │   └── search.py

    │   ├── services/
    │   │   └── matching_service.py

    │   └── main.py

    ├── uploads/

    ├── images/

    └── image_database/
```

---

## Getting Started

### Frontend

```bash
cd frontend

npm install

npm run dev
```

Runs on:

```text
http://localhost:5173
```

---

### Backend

Create virtual environment:

```bash
python -m venv .venv
```

Activate:

```bash
# Windows

.venv\Scripts\activate

# Linux / Mac

source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run server:

```bash
uvicorn app.main:app --reload
```

Backend runs on:

```text
http://localhost:8000
```

Swagger docs:

```text
http://localhost:8000/docs
```


## Vision

Shapely explores a different kind of search.

Instead of asking:

> "What is this object?"

it asks:

> "What else in the world looks like this?"

A rough sketch becomes a way to discover hidden visual similarities across nature, architecture, clouds, shadows, and beyond.

---

Built with curiosity, computer vision, and too many contour points.
