import cv2
import numpy as np
from typing import Tuple, Dict, Any

def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Detects text orientation/skew angle and rotates image to upright alignment.
    Returns (deskewed_image, detected_angle).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Invert and threshold
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Find non-zero coordinates
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return image, 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # Normalize angle to [-45, 45]
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle

    # Ignore micro-jitters
    if abs(angle) < 0.3 or abs(angle) > 30.0:
        return image, 0.0

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        image, rot_mat, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return deskewed, float(angle)


def denoise_image(image: np.ndarray) -> np.ndarray:
    """Removes scan artifacts, sensor speckles, and grain noise."""
    if len(image.shape) == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)


def binarize_image(image: np.ndarray) -> np.ndarray:
    """Applies Otsu adaptive binarization for clear OCR text segmentation."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Slight Gaussian blur to reduce high-frequency salt-and-pepper noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return binary


def preprocess_document_image(image: np.ndarray) -> Dict[str, Any]:
    """
    Executes full computer vision pre-processing pipeline:
    1. Deskew
    2. Denoise
    3. Binarize
    """
    deskewed, angle = deskew_image(image)
    denoised = denoise_image(deskewed)
    binary = binarize_image(denoised)

    return {
        "processed_image": denoised,
        "binary_image": binary,
        "skew_angle_detected": angle,
        "preprocessing_applied": ["deskew", "denoise", "otsu_binarize"]
    }
