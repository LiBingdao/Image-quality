"""24 色卡分析算法

功能：
1. 支持用户框选 24 色卡区域（4 行 x 6 列）
2. 自动将 ROI 划分为 24 个色块并采样平均 RGB
3. 计算每个色块的 XYZ、CIELAB、CIELUV
4. 与 ColorChecker Classic 标准值对比，计算色差 ΔE

色彩空间：默认 sRGB，可选 Adobe RGB、Display P3
白点：默认 D65，可选 D50、C
"""

import numpy as np
from io import BytesIO
from PIL import Image
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path

# =============================================================================
# 加载参考文件（支持外部 JSON 自定义）
# =============================================================================

def load_colorchecker_reference(ref_path: str = None) -> List[dict]:
    """加载色卡参考数据，支持自定义 JSON 文件"""
    if ref_path and Path(ref_path).exists():
        with open(ref_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("patches", data)
    
    # 默认使用内置数据
    return COLORCHECKER.copy()


# 默认内置参考值（ColorChecker Classic, sRGB D65）
COLORCHECKER = [
    {"name": "Dark Skin",      "rgb": [115, 82, 68],   "lab": [37.54, 12.36, 13.92]},
    {"name": "Light Skin",     "rgb": [194, 150, 130], "lab": [64.30, 18.14, 17.81]},
    {"name": "Blue Sky",       "rgb": [98, 122, 157],  "lab": [49.54, -4.37, -21.57]},
    {"name": "Foliage",        "rgb": [87, 108, 67],   "lab": [43.27, -14.56, 26.87]},
    {"name": "Blue Flower",    "rgb": [133, 128, 177], "lab": [55.03, 10.92, -21.73]},
    {"name": "Bluish Green",   "rgb": [103, 189, 170], "lab": [71.37, -32.14, 2.31]},
    {"name": "Orange",         "rgb": [214, 126, 44],  "lab": [60.47, 35.20, 50.27]},
    {"name": "Purplish Blue",  "rgb": [80, 91, 166],   "lab": [40.14, 10.52, -45.63]},
    {"name": "Moderate Red",   "rgb": [193, 90, 99],   "lab": [50.29, 42.79, 14.13]},
    {"name": "Purple",         "rgb": [94, 60, 108],   "lab": [30.33, 21.79, -20.45]},
    {"name": "Yellow Green",   "rgb": [157, 188, 64],  "lab": [71.77, -24.77, 59.18]},
    {"name": "Orange Yellow",  "rgb": [224, 163, 46],  "lab": [72.24, 18.85, 64.73]},
    {"name": "Blue",           "rgb": [56, 61, 150],   "lab": [28.87, 18.14, -50.48]},
    {"name": "Green",          "rgb": [70, 148, 73],   "lab": [54.96, -39.72, 33.30]},
    {"name": "Red",            "rgb": [175, 54, 60],   "lab": [42.43, 51.09, 27.20]},
    {"name": "Yellow",         "rgb": [231, 199, 31],  "lab": [81.32, 3.54, 77.87]},
    {"name": "Magenta",        "rgb": [187, 86, 149],  "lab": [51.87, 48.64, -14.36]},
    {"name": "Cyan",           "rgb": [8, 133, 161],   "lab": [50.63, -22.34, -32.34]},
    {"name": "White",          "rgb": [243, 243, 242], "lab": [96.52, -0.43, 1.10]},
    {"name": "Neutral 8",      "rgb": [200, 200, 200], "lab": [81.26, -0.64, -0.29]},
    {"name": "Neutral 6.5",    "rgb": [160, 160, 160], "lab": [65.10, -0.70, -0.32]},
    {"name": "Neutral 5",      "rgb": [122, 122, 121], "lab": [50.47, -0.56, -0.26]},
    {"name": "Neutral 3.5",    "rgb": [85, 85, 85],    "lab": [35.21, -0.43, -0.21]},
    {"name": "Black",          "rgb": [52, 52, 52],    "lab": [20.64, -0.28, -0.15]},
]

# =============================================================================
# 色彩空间转换矩阵
# =============================================================================

def get_rgb_to_xyz_matrix(color_space: str = "sRGB") -> np.ndarray:
    """获取 RGB 到 XYZ 的转换矩阵（基于 D65 白点）"""
    if color_space == "sRGB":
        # sRGB D65
        return np.array([
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041]
        ])
    elif color_space == "Adobe RGB":
        return np.array([
            [0.5767309, 0.1855540, 0.1881852],
            [0.2973769, 0.6273491, 0.0752741],
            [0.0270343, 0.0705872, 0.9911085]
        ])
    elif color_space == "Display P3":
        return np.array([
            [0.48657095, 0.26566769, 0.19821729],
            [0.22897457, 0.69173850, 0.07928691],
            [0.00000000, 0.04539142, 1.04394437]
        ])
    else:
        return get_rgb_to_xyz_matrix("sRGB")


def get_white_point(white_point_name: str = "D65") -> np.ndarray:
    """获取标准白点 XYZ 值"""
    white_points = {
        "D65": np.array([95.047, 100.0, 108.883]),
        "D50": np.array([96.4212, 100.0, 82.5188]),
        "C":   np.array([98.074, 100.0, 118.232]),
    }
    return white_points.get(white_point_name, white_points["D65"])


def gamma_correct(rgb: np.ndarray) -> np.ndarray:
    """sRGB gamma 解码（线性化）"""
    return np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        np.power((rgb + 0.055) / 1.055, 2.4)
    )


def rgb_to_xyz(rgb: np.ndarray, color_space: str = "sRGB") -> np.ndarray:
    """RGB -> XYZ 转换"""
    rgb = rgb / 255.0
    rgb = gamma_correct(rgb)
    M = get_rgb_to_xyz_matrix(color_space)
    xyz = np.dot(M, rgb.T).T
    return xyz * 100  # 转为百分比


def xyz_to_lab(xyz: np.ndarray, white_point: np.ndarray) -> np.ndarray:
    """XYZ -> CIELAB 转换"""
    xyz = np.atleast_2d(xyz)
    wp = white_point.reshape(1, 3)

    ratio = xyz / wp
    f = np.where(ratio > np.power(6.0/29.0, 3),
                  np.power(ratio, 1.0/3.0),
                  ratio / (3 * np.power(6.0/29.0, 2)) + 4.0/29.0)

    L = 116 * f[:, 1:2] - 16
    a = 500 * (f[:, 0:1] - f[:, 1:2])
    b = 200 * (f[:, 1:2] - f[:, 2:3])

    return np.hstack([L, a, b])


def xyz_to_xy_chromaticity(xyz_val: np.ndarray) -> tuple:
    """XYZ -> xy 色度坐标"""
    X, Y, Z = xyz_val[0], xyz_val[1], xyz_val[2]
    total = X + Y + Z + 1e-10
    x = X / total
    y_val = Y / total
    return x, y_val


def xyz_to_luv(xyz: np.ndarray, white_point: np.ndarray) -> np.ndarray:
    """XYZ -> CIELUV 转换"""
    xyz = np.atleast_2d(xyz)
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]

    Xn, Yn, Zn = white_point
    Y_Yn = Y / Yn

    u_prime = 4 * X / (X + 15 * Y + 3 * Z + 1e-10)
    v_prime = 9 * Y / (X + 15 * Y + 3 * Z + 1e-10)

    un = 4 * Xn / (Xn + 15 * Yn + 3 * Zn)
    vn = 9 * Yn / (Xn + 15 * Yn + 3 * Zn)

    L = np.where(Y_Yn > np.power(6.0/29.0, 3),
                  116 * np.power(Y_Yn, 1.0/3.0) - 16,
                  Y_Yn * np.power(29.0/3.0, 3))

    u = 13 * L * (u_prime - un)
    v = 13 * L * (v_prime - vn)

    return np.vstack([L, u, v]).T


def delta_e_cie76(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """CIE76 ΔE 色差计算"""
    return np.sqrt(np.sum((lab1 - lab2) ** 2))


# =============================================================================
# 24 色卡分析主函数
# =============================================================================

async def analyze_color_checker(image_bytes: bytes, roi: dict = None, color_space: str = "sRGB", white_point: str = "D65", **kwargs) -> dict:
    """24 色卡分析

    Args:
        image_bytes: 图片字节流
        roi: ROI 区域 {"x": int, "y": int, "width": int, "height": int}

    Returns:
        包含 24 色块分析结果的 JSON 数据
    """
    # 解析图片
    image = Image.open(BytesIO(image_bytes))
    img_arr = np.array(image, dtype=np.float64)

    # 如果提供了 ROI，裁剪
    if roi:
        x, y = int(roi["x"]), int(roi["y"])
        w, h = int(roi["width"]), int(roi["height"])
        if len(img_arr.shape) == 3:
            img_arr = img_arr[y:y+h, x:x+w, :]
        else:
            img_arr = img_arr[y:y+h, x:x+w]

    print(f"[STEP 1] 图片尺寸: {img_arr.shape}, dtype: {img_arr.dtype}")
    
    # 转为 RGB（如果图片不是 RGB）
    if len(img_arr.shape) == 2:
        img_arr = np.stack([img_arr] * 3, axis=-1)
    elif img_arr.shape[2] > 3:
        img_arr = img_arr[:, :, :3]
    
    print(f"[STEP 2] 转换后尺寸: {img_arr.shape}")
    
    # 确保图像是 (H, W, 3) 格式
    if len(img_arr.shape) != 3 or img_arr.shape[2] != 3:
        return {
            "algorithm": "colorChecker",
            "status": "error",
            "message": f"图片格式不正确，需要 RGB 图像，当前 shape: {img_arr.shape}",
        }

    # 使用传入参数（重命名避免冲突）
    color_space_name = color_space if color_space in ["sRGB", "Adobe RGB", "Display P3"] else "sRGB"
    white_point_name = white_point if white_point in ["D65", "D50", "C"] else "D65"
    white_point_xyz = get_white_point(white_point_name)
    
    print(f"[STEP 3] 参数 - color_space: {color_space_name}, white_point: {white_point_name}")
    print(f"[STEP 3] white_point_xyz: {white_point_xyz}")

    # 将 ROI 划分为 4 行 x 6 列 = 24 个色块
    h, w = img_arr.shape[:2]
    print(f"[STEP 4] ROI 尺寸: {w}x{h}")
    
    rows, cols = 4, 6
    cell_h, cell_w = h / rows, w / cols
    print(f"[STEP 5] 单元格尺寸: {cell_w:.1f}x{cell_h:.1f}")

    # 采样区域（避开色块边界，取中心 64%，与前端网格缩进一致）
    margin_ratio = 0.18

    patches = []
    for r in range(rows):
        for c in range(cols):
            print(f"[STEP 6] 处理色块 row={r}, col={c}")
            
            # 计算当前色块边界
            x1 = int(c * cell_w + cell_w * margin_ratio)
            y1 = int(r * cell_h + cell_h * margin_ratio)
            x2 = int((c + 1) * cell_w - cell_w * margin_ratio)
            y2 = int((r + 1) * cell_h - cell_h * margin_ratio)

            patch = img_arr[y1:y2, x1:x2, :]
            print(f"[STEP 7] 色块 patch shape: {patch.shape}")
            
            mean_rgb = patch.mean(axis=(0, 1))  # 平均 RGB
            print(f"[STEP 8] mean_rgb: {mean_rgb}, type: {type(mean_rgb)}")

            # 转换到 XYZ, LAB, LUV
            print(f"[STEP 9] 调用 rgb_to_xyz...")
            xyz = rgb_to_xyz(mean_rgb, color_space_name)
            print(f"[STEP 10] xyz result: {xyz}, shape: {xyz.shape}")
            
            print(f"[STEP 11] 调用 xyz_to_lab...")
            lab = xyz_to_lab(xyz, white_point_xyz)
            print(f"[STEP 12] lab result: {lab}, shape: {lab.shape}")
            
            print(f"[STEP 13] 调用 xyz_to_luv...")
            luv = xyz_to_luv(xyz, white_point_xyz)
            print(f"[STEP 14] luv result: {luv}, shape: {luv.shape}")

            patch_idx = r * 6 + c
            standard = COLORCHECKER[patch_idx]

            # 参考值固定为 sRGB 空间：始终用 sRGB 矩阵转换，不受输入色彩空间影响
            # 仅白点跟随用户选择，使「实测」与「参考」处于同一白点下，色差才有可比性
            ref_rgb = np.array(standard["rgb"], dtype=np.float64)
            ref_xyz = rgb_to_xyz(ref_rgb, "sRGB")
            ref_lab = xyz_to_lab(ref_xyz, white_point_xyz)
            ref_luv = xyz_to_luv(ref_xyz, white_point_xyz)
            print(f"[STEP 15] ref_lab (sRGB, {white_point_name}): {ref_lab}")

            # 色差：输入图像(选中色彩空间+白点) vs 参考(sRGB+白点)
            print(f"[STEP 16] 调用 delta_e_cie76...")
            de = delta_e_cie76(lab[0], ref_lab[0])
            print(f"[STEP 17] delta_e: {de}")

            patches.append({
                "index": patch_idx + 1,
                "name": standard["name"],
                "rgb": {
                    "measured": [round(float(v), 2) for v in mean_rgb],
                    "standard": standard["rgb"]
                },
                "xyz": {
                    "measured": [round(float(xyz[i]), 4) for i in range(3)],
                    "standard": [round(float(ref_xyz[i]), 4) for i in range(3)],
                },
                "lab": {
                    "measured": [round(float(lab[0, i]), 4) for i in range(3)],
                    "standard": [round(float(ref_lab[0, i]), 4) for i in range(3)],
                },
                "luv": {
                    "measured": [round(float(luv[0, i]), 4) for i in range(3)],
                    "standard": [round(float(ref_luv[0, i]), 4) for i in range(3)],
                },
                "delta_e": round(float(de), 4),
            })
            print(f"[STEP 18] 色块 {patch_idx + 1} 处理完成\n")

    # 计算统计信息
    print(f"[STEP 19] 计算统计信息...")
    delta_e_values = [p["delta_e"] for p in patches]
    avg_delta_e = np.mean(delta_e_values)
    max_delta_e = np.max(delta_e_values)
    min_delta_e = np.min(delta_e_values)
    print(f"[STEP 20] 统计完成 - avg: {avg_delta_e:.4f}, max: {max_delta_e:.4f}, min: {min_delta_e:.4f}")

    print(f"[STEP 21] 返回结果")
    return {
        "algorithm": "colorChecker",
        "status": "success",
        "message": "24 色卡分析完成",
        "params": {
            "color_space": color_space_name,
            "white_point": white_point_name,
        },
        "statistics": {
            "avg_delta_e": round(float(avg_delta_e), 4),
            "max_delta_e": round(float(max_delta_e), 4),
            "min_delta_e": round(float(min_delta_e), 4),
        },
        "patches": patches,
    }
