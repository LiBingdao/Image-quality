"""算法注册中心 - 所有图像质量分析算法在此注册"""

from .slanted_edge import analyze_slanted_edge
from .siemens_star import analyze_siemens_star
from .dead_leaves import analyze_dead_leaves
from .line_pairs import analyze_line_pairs
from .color_checker import analyze_color_checker
from .gray_scale import analyze_gray_scale
from .checkerboard import analyze_checkerboard
from .uniformity import analyze_uniformity

algorithm_registry = {
    "slantedEdge": analyze_slanted_edge,
    "siemensStar": analyze_siemens_star,
    "deadLeaves": analyze_dead_leaves,
    "linePairs": analyze_line_pairs,
    "colorChecker": analyze_color_checker,
    "grayScale": analyze_gray_scale,
    "checkerboard": analyze_checkerboard,
    "uniformity": analyze_uniformity,
}

def list_algorithms():
    """返回所有可用算法列表"""
    return list(algorithm_registry.keys())
