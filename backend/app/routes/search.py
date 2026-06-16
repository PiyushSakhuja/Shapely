# app/routes/search.py
from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from app.services.matching_service import (
    process_query_image,
    load_database,
    match_against_database
)
router = APIRouter()
DB_RECORDS = load_database()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/api/search")
async def search(file: UploadFile = File(...)):
    filepath = UPLOAD_DIR / file.filename

    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())

    query = process_query_image(str(filepath))
    matches = match_against_database(query, DB_RECORDS)

    results = []
    for m in matches:
        record = m["record"]
        results.append({
            "id": int(record["id"]),
            "title": record["filename"],
            "score": float(round(max(0, 1 - float(m["hausdorff_distance"])), 3)),
            "imageUrl": f"http://localhost:8000/{record['path'].replace('\\', '/')}",
            "hausdorff": float(m["hausdorff_distance"]),
            "fourier": float(m["fourier_distance"]),
            "area": float(record["area_ratio"]),
        })

    return results