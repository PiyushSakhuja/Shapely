import { createFileRoute } from "@tanstack/react-router";
import Home from "../pages/Home/Home";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Shapely — Shape-based image search" },
      { name: "description", content: "Draw a rough silhouette and find visually similar images using contour-based shape matching." },
      { property: "og:title", content: "Shapely — Shape-based image search" },
      { property: "og:description", content: "Draw a rough silhouette and find visually similar images using contour-based shape matching." },
    ],
  }),
  component: Home,
});
