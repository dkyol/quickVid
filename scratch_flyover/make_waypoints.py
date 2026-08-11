import math
import cv2
import numpy as np

tee = (38.9198692, -76.6837799)
green = (38.9229076, -76.6852765)
mid_lat = (tee[0] + green[0]) / 2
mid_lon = (tee[1] + green[1]) / 2
half_deg_lat = 0.0032
half_deg_lon = 0.0041

west, east = mid_lon - half_deg_lon, mid_lon + half_deg_lon
south, north = mid_lat - half_deg_lat, mid_lat + half_deg_lat

img = cv2.imread("scratch_flyover/hole8_square.jpg")
H, W = img.shape[:2]
print("source size:", W, H)

def lonlat_to_px(lat, lon):
    x = (lon - west) / (east - west) * W
    y = (north - lat) / (north - south) * H
    return np.array([x, y, 1.0])

tee_px = lonlat_to_px(*tee)
green_px = lonlat_to_px(*green)
print("tee px:", tee_px[:2], "green px:", green_px[:2])

dx = green_px[0] - tee_px[0]
dy = green_px[1] - tee_px[1]
angle_from_up = math.degrees(math.atan2(dx, -dy))  # clockwise offset of tee->green from straight-up
print("angle from up (cw+):", round(angle_from_up, 2))

# cv2.getRotationMatrix2D(center, angle, scale): angle in degrees, POSITIVE = counter-clockwise
# (OpenCV convention, y-down image coords still visually CCW for positive angle).
# We want to cancel a clockwise offset of `angle_from_up`, i.e. rotate CCW by angle_from_up.
center = (W / 2, H / 2)
M = cv2.getRotationMatrix2D(center, angle_from_up, 1.0)

# Determine expanded canvas size (like PIL expand=True) so nothing is clipped.
corners = np.array([[0, 0], [W, 0], [W, H], [0, H]], dtype=np.float64)
ones = np.ones((4, 1))
corners_h = np.hstack([corners, ones])
new_corners = (M @ corners_h.T).T
min_x, min_y = new_corners.min(axis=0)
max_x, max_y = new_corners.max(axis=0)
new_W = int(math.ceil(max_x - min_x))
new_H = int(math.ceil(max_y - min_y))
# Shift so all content is positive
M[0, 2] += -min_x
M[1, 2] += -min_y

rotated = cv2.warpAffine(img, M, (new_W, new_H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0))
print("rotated size:", new_W, new_H)

def apply(M, pt):
    v = M @ np.array([pt[0], pt[1], 1.0])
    return v

tee_r = apply(M, tee_px)
green_r = apply(M, green_px)
print("tee_r:", tee_r, "green_r:", green_r)
print("x diff (should be ~0):", tee_r[0] - green_r[0])
print("y diff (tee should be below green, larger y):", tee_r[1] - green_r[1])

cv2.imwrite("scratch_flyover/hole8_rotated_cv2.jpg", rotated, [cv2.IMWRITE_JPEG_QUALITY, 92])

dbg = rotated.copy()
cv2.circle(dbg, (int(tee_r[0]), int(tee_r[1])), 18, (0, 0, 255), 6)
cv2.circle(dbg, (int(green_r[0]), int(green_r[1])), 18, (255, 255, 0), 6)
cv2.imwrite("scratch_flyover/hole8_rotated_cv2_debug.jpg", dbg, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("saved")
