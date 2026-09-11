"""线对分析

分辨率、对比度测试。
"""
import numpy as np
from io import BytesIO
from PIL import Image


async def analyze_line_pairs(image_bytes: bytes, roi: dict = None) -> dict:
    """线对分析"""
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "L":
        image = image.convert("L")
    arr = np.array(image, dtype=np.float64)

    return {
        "algorithm": "linePairs",
        "status": "success",
        "message": "线对算法框架已运行，实际计算待实现",
        "resolution": None,
        "contrast": None,
    }
