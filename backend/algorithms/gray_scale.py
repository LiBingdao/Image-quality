"""灰阶分析

Gamma、动态范围测试。
"""
import numpy as np
from io import BytesIO
from PIL import Image


async def analyze_gray_scale(image_bytes: bytes, roi: dict = None) -> dict:
    """灰阶分析"""
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "L":
        image = image.convert("L")
    arr = np.array(image, dtype=np.float64)

    return {
        "algorithm": "grayScale",
        "status": "success",
        "message": "灰阶算法框架已运行，实际计算待实现",
        "gamma": None,
        "dynamic_range": None,
    }
