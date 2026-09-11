"""
图像质量分析平台 - HTTP 后端 (Python 标准库版)
无需安装 fastapi/uvicorn，直接 python app.py 运行
"""

import json
import os
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).parent

# 动态导入算法
sys.path.insert(0, str(BASE_DIR))
from algorithms import algorithm_registry


class CORSHandler(BaseHTTPRequestHandler):
    """支持 CORS 的 HTTP 请求处理器"""

    def log_message(self, format, *args):
        """简化日志输出"""
        print(f"[{self.command}] {self.path} - {format % args}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _send_js(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _send_css(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _send_file_binary(self, filepath, content_type="application/octet-stream"):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_json({"detail": "文件不存在: " + str(filepath)}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        print(f"[GET] 请求路径: {path}")

        if path == "/":
            # 返回首页
            index_path = BASE_DIR / ".." / "index.html"
            with open(index_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_html(content)

        elif path == "/app.js":
            js_path = BASE_DIR / ".." / "app.js"
            with open(js_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_js(content)

        elif path.startswith("/css/"):
            css_path = BASE_DIR / ".." / path.lstrip("/")
            if css_path.exists():
                with open(css_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._send_css(content)
            else:
                self._send_json({"detail": "CSS 文件不存在"}, 404)

        elif path == "/api/reference/colorchecker":
            # 返回当前色卡参考数据
            print("[GET] 返回色卡参考数据")
            try:
                from algorithms.color_checker import COLORCHECKER
                self._send_json({
                    "status": "success",
                    "name": "ColorChecker Classic (ColorBaby)",
                    "description": "X-Rite ColorChecker Classic 标准参考值，sRGB D65 色彩空间",
                    "patches": COLORCHECKER
                })
            except Exception as e:
                self._send_json({"detail": str(e)}, 500)

        elif path == "/api/reference/colorchecker/download":
            # 下载参考值 JSON 文件
            print("[GET] 下载参考值 JSON")
            json_path = BASE_DIR / "colorchecker_reference.json"
            self._send_file_binary(str(json_path), "application/json")

        else:
            self._send_json({"detail": f"路径不存在: {path}"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        print(f"[POST] 请求路径: {path}")

        if path.startswith("/api/analyze/"):
            algorithm_name = path.split("/")[-1]
            print(f"[POST] 算法名称: {algorithm_name}")

            if algorithm_name not in algorithm_registry:
                self._send_json({"detail": f"未知算法: {algorithm_name}"}, 404)
                return

            # 解析 multipart/form-data
            content_length = int(self.headers.get("Content-Length", 0))
            content_type = self.headers.get("Content-Type", "")

            try:
                # 读取请求体
                post_data = self.rfile.read(content_length)

                # 解析 form-data
                roi_data = {}
                color_space = "sRGB"
                white_point = "D65"
                image_bytes = None

                if "multipart/form-data" in content_type:
                    # 提取 boundary
                    boundary = content_type.split("boundary=")[-1].strip()
                    parts = post_data.split(("--" + boundary).encode())

                    for part in parts:
                        part = part.strip()
                        if not part or part == b"--":
                            continue

                        # 分离 header 和 body
                        try:
                            header_end = part.index(b"\r\n\r\n")
                            headers = part[:header_end].decode("utf-8", errors="ignore")
                            body = part[header_end + 4:]
                            # 去掉末尾的 \r\n--
                            if body.endswith(b"\r\n--"):
                                body = body[:-4]
                            elif body.endswith(b"\r\n"):
                                body = body[:-2]
                        except ValueError:
                            continue

                        # 解析 Content-Disposition
                        if "Content-Disposition" in headers:
                            if 'name="file"' in headers:
                                image_bytes = body
                            elif 'name="roi"' in headers:
                                roi_data = json.loads(body.decode("utf-8"))
                            elif 'name="color_space"' in headers:
                                color_space = body.decode("utf-8")
                            elif 'name="white_point"' in headers:
                                white_point = body.decode("utf-8")

                # 执行分析
                if image_bytes is None:
                    self._send_json({"detail": "未上传图片"}, 400)
                    return

                kwargs = {"roi": roi_data}
                if algorithm_name == "colorChecker":
                    kwargs["color_space"] = color_space
                    kwargs["white_point"] = white_point

                import asyncio
                result = asyncio.run(algorithm_registry[algorithm_name](image_bytes, **kwargs))
                self._send_json(result)

            except json.JSONDecodeError:
                self._send_json({"detail": "ROI 数据格式错误"}, 400)
            except Exception as e:
                self._send_json({"detail": str(e)}, 500)

        else:
            self._send_json({"detail": f"路径不支持 POST: {path}"}, 405)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), CORSHandler)
    print("=" * 50)
    print("图像质量分析平台后端已启动")
    print("访问地址: http://localhost:8000")
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()
