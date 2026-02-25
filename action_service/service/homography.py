import cv2
import numpy as np


def compute_homography(src_points, dst_points):

    H, _ = cv2.findHomography(
        np.array(src_points, dtype=np.float32),
        np.array(dst_points, dtype=np.float32)
    )

    return H


def apply_homography(point, H):

    px = np.array([[point[0], point[1], 1]]).T
    mapped = np.dot(H, px)

    mapped /= mapped[2]

    return float(mapped[0]), float(mapped[1])