"""枯叶图分析

纹理、降噪、锐化测试。
"""
import numpy as np
from io import BytesIO
from PIL import Image


async def analyze_dead_leaves(image_bytes: bytes, roi: dict = None) -> dict:
    """枯叶图分析"""
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "L":
        image = image.convert("L")
    arr = np.array(image, dtype=np.float64)

    return {
        "algorithm": "deadLeaves",
        "status": "success",
        "message": "枯叶图算法框架已运行，实际计算待实现",
        "texture_score": None,
        "noise_level": None,
        "sharpness": None,
    }
