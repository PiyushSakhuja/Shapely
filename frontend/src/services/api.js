// Mock API for shape-based image search.
// Later, replace `mockSearch` with a real `fetch('/api/search', ...)` call.

const SAMPLE_TITLES = [
  "Heart Shaped Cloud",
  "Mountain Formation",
  "Coastal Silhouette",
  "Abstract Sculpture",
  "Forest Canopy",
  "Urban Skyline",
  "Desert Dune",
  "Ocean Wave",
  "Leaf Pattern",
  "Architectural Arch",
  "Bird in Flight",
  "River Bend",
];

function randomScore() {
  // Bias toward high scores so it feels like a "match"
  return Math.round((0.7 + Math.random() * 0.29) * 100) / 100;
}

function buildMockResults() {
  const count = 8 + Math.floor(Math.random() * 5);
  const results = Array.from({ length: count }, (_, i) => {
    const seed = 400 + Math.floor(Math.random() * 600);
    return {
      id: i + 1,
      title: SAMPLE_TITLES[i % SAMPLE_TITLES.length],
      score: randomScore(),
      imageUrl: `https://picsum.photos/seed/${seed + i}/600/600`,
    };
  });
  return results.sort((a, b) => b.score - a.score);
}

/**
 * Search for visually similar shapes.
 * @param {Blob} imageBlob - PNG blob of the user's drawing.
 * @returns {Promise<Array>}
 */
export async function searchSimilarShapes(imageBlob) {
  const form = new FormData();
  form.append(
    "file",
    imageBlob,
    "drawing.png"
  );
  const res = await fetch(
    "http://localhost:8000/api/search",
    {
      method: "POST",
      body: form
    }
  );
  if (!res.ok) {

    throw new Error("search failed");
  }
  return res.json();
}

// Real implementation (for later):
// export async function searchSimilarShapes(imageBlob) {
//   const form = new FormData();
//   form.append("image", imageBlob, "drawing.png");
//   const res = await fetch("/api/search", { method: "POST", body: form });
//   if (!res.ok) throw new Error("Search failed");
//   return res.json();
// }