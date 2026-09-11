"""棋盘格分析

畸变、标定、角点检测。
"""
import numpy as np
from io import BytesIO
from PIL import Image


async def analyze_checkerboard(image_bytes: bytes, roi: dict = None) -> dict:
    """棋盘格分析"""
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "L":
        image = image.convert("L")
    arr = np.array(image, dtype=np.float64)

    return {
        "algorithm": "checkerboard",
        "status": "success",
        "message": "棋盘格算法框架已运行，实际计算待实现",
        "distortion": None,
        "corners": [],
    }
