"""西门子星图分析

径向 MTF、分辨率测试。
"""
import numpy as np
from io import BytesIO
from PIL import Image


async def analyze_siemens_star(image_bytes: bytes, roi: dict = None) -> dict:
    """西门子星图分析"""
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "L":
        image = image.convert("L")
    arr = np.array(image, dtype=np.float64)

    return {
        "algorithm": "siemensStar",
        "status": "success",
        "message": "西门子星图算法框架已运行，实际计算待实现",
        "radial_mtf": [],
        "resolution": None,
    }
