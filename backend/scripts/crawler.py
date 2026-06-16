from icrawler.builtin import BingImageCrawler
import os
queries = [
    "forest",
    "mountain",
    "river",
    "waterfall",
    "lake",
    "beach",
    "clouds",
    "sunset landscape",
    "tree silhouette",
    "flower field"
]
for query in queries:
    crawler = BingImageCrawler(
        storage={"root_dir": f"nature_images/{query}"}
    )

    crawler.crawl(
        keyword=query,
        max_num=20
    )

print("Done")
print("Folder exists:", os.path.exists("test_images"))