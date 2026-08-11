import os
import ee
import requests

def load_env(path=".env"):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if v and k not in os.environ:
                os.environ[k] = v

load_env()
project = os.environ.get("EARTHENGINE_PROJECT")
if not project:
    raise SystemExit("EARTHENGINE_PROJECT not set in .env")

ee.Initialize(project=project)

# Renditions Golf Course, Davidsonville MD - OSM bounding box (way 266489451)
south, north = 38.9079935, 38.9302677
west, east = -76.6869528, -76.6694905

region = ee.Geometry.Rectangle([west, south, east, north])

naip = (
    ee.ImageCollection("USDA/NAIP/DOQQ")
    .filterBounds(region)
    .filterDate("2018-01-01", "2025-01-01")
    .sort("system:time_start", False)
)

count = naip.size().getInfo()
print("NAIP images found:", count)

image = naip.mosaic().clip(region)

url = image.getThumbURL({
    "region": region,
    "dimensions": 2000,
    "format": "jpg",
    "bands": ["R", "G", "B"],
})
print("URL:", url)

r = requests.get(url, timeout=60)
r.raise_for_status()
out_path = "scratch_flyover/course_wide.jpg"
with open(out_path, "wb") as f:
    f.write(r.content)
print("Saved:", out_path, len(r.content), "bytes")
