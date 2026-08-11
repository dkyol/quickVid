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
ee.Initialize(project=os.environ["EARTHENGINE_PROJECT"])

# Hole 8 tee/green from OSM golf=hole ref=8 (verified against real yardage + bunker/creek layout)
tee = (38.9198692, -76.6837799)
green = (38.9229076, -76.6852765)
mid_lat = (tee[0] + green[0]) / 2
mid_lon = (tee[1] + green[1]) / 2

# ~700m square around the hole, generous margin for post-rotate crop
half_deg_lat = 0.0032
half_deg_lon = 0.0041  # wider to account for longitude compression at this latitude

region = ee.Geometry.Rectangle([
    mid_lon - half_deg_lon, mid_lat - half_deg_lat,
    mid_lon + half_deg_lon, mid_lat + half_deg_lat,
])

naip = (
    ee.ImageCollection("USDA/NAIP/DOQQ")
    .filterBounds(region)
    .filterDate("2018-01-01", "2025-01-01")
    .sort("system:time_start", False)
)
image = naip.mosaic().clip(region)

url = image.getThumbURL({
    "region": region,
    "dimensions": "1800x1800",  # explicit square grid: our region is ~709x712m (near-square in true ground meters)
    "format": "jpg",
    "bands": ["R", "G", "B"],
})
r = requests.get(url, timeout=60)
r.raise_for_status()
out_path = "scratch_flyover/hole8_square.jpg"
with open(out_path, "wb") as f:
    f.write(r.content)
print("Saved:", out_path, len(r.content), "bytes")
