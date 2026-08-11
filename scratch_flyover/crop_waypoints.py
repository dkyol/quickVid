import cv2

img = cv2.imread("scratch_flyover/hole8_rotated_cv2.jpg")
H, W = img.shape[:2]

tee = (1163.0, 1620.8)
green = (1163.0, 705.3)
cx = int((tee[0] + green[0]) / 2)

def save_crop(name, x0, y0, x1, y1, out_w, out_h):
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    crop = img[y0:y1, x0:x1]
    resized = cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(f"scratch_flyover/{name}.jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(name, "crop box:", (x0, y0, x1, y1), "-> saved", out_w, "x", out_h)

# A - establishing: whole hole, tee near bottom, green near top, portrait 9:16
save_crop("wp_A_establishing", cx - 384, int(green[1]) - 220, cx + 384, int(tee[1]) + 260, 1080, 1920)

# B - mid-flight: fairway landing area, the bend between tee and green
mid_y = int((tee[1] + green[1]) / 2)
save_crop("wp_B_fairway", cx - 340, mid_y - 420, cx + 340, mid_y + 420, 1080, 1920)

# C - arrival: green + surrounds, tight zoom
save_crop("wp_C_green", cx - 320, int(green[1]) - 260, cx + 320, int(green[1]) + 260, 1080, 1080)
