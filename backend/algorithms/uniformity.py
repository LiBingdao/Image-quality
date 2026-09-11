"""均匀性分析

亮度、色彩、暗角测试。
"""
import numpy as np
from io import BytesIO
from PIL import Image


async def analyze_uniformity(image_bytes: bytes, roi: dict = None) -> dict:
    """均匀性分析"""
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "L":
        image = image.convert("L")
    arr = np.array(image, dtype=np.float64)

    return {
        "algorithm": "uniformity",
        "status": "success",
        "message": "均匀性算法框架已运行，实际计算待实现",
        "brightness_uniformity": None,
        "color_uniformity": None,
        "vignetting": None,
    }
