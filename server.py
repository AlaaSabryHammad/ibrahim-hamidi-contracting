#!/usr/bin/env python3
"""
لوحة تحكم مؤسسة إبراهيم حميدي العنزي للمقاولات
سيرفر محلي لإدارة المشاريع والفريق الفني ونشرها على GitHub Pages
"""

import json
import os
import sys
import subprocess
import base64
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 7000
BASE_DIR = Path(__file__).parent.resolve()
DATA_FILE = BASE_DIR / "data.json"
IMAGES_DIR = BASE_DIR / "images"


class AdminServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silence default logging

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_error(404, "File not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        # API routes
        if path == "/api/data":
            self._get_data()
            return

        # Serve images
        if path.startswith("/images/"):
            img_path = BASE_DIR / path.lstrip("/")
            ext = img_path.suffix.lower()
            ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                  ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "application/octet-stream")
            self._send_file(img_path, ct)
            return

        # Static files
        if path == "/" or path == "/admin" or path == "/admin.html":
            self._send_file(BASE_DIR / "admin.html", "text/html; charset=utf-8")
            return
        if path == "/index.html" or path == "/preview":
            self._send_file(BASE_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/data.json":
            self._send_file(DATA_FILE, "application/json; charset=utf-8")
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/api/data":
            self._save_data()
            return

        if path == "/api/publish":
            self._publish()
            return

        self.send_error(404, "Not found")

    # ===== API: Get Data =====
    def _get_data(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._send_json(data)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ===== API: Save Data =====
    def _save_data(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            # Process base64 images -> save to images/ folder
            IMAGES_DIR.mkdir(exist_ok=True)

            for section in ("projects", "team"):
                for item in data.get(section, []):
                    img = item.get("image", "")
                    if img.startswith("data:"):
                        # Extract mime type and data
                        m = re.match(r"data:(image/\w+);base64,(.+)", img)
                        if m:
                            mime = m.group(1)
                            b64 = m.group(2)
                            ext_map = {"image/jpeg": ".jpg", "image/png": ".png",
                                       "image/gif": ".gif", "image/webp": ".webp"}
                            ext = ext_map.get(mime, ".jpg")
                            img_name = f"{item['id']}{ext}"
                            img_path = IMAGES_DIR / img_name

                            with open(img_path, "wb") as f:
                                f.write(base64.b64decode(b64))

                            item["image"] = f"images/{img_name}"

            # Save data.json
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, 500)

    # ===== API: Publish to GitHub =====
    def _publish(self):
        try:
            os.chdir(BASE_DIR)

            # Git add
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True, text=True)

            # Check if there are changes
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if not status.stdout.strip():
                self._send_json({"success": True, "message": "لا توجد تغييرات جديدة"})
                return

            # Git commit
            subprocess.run(
                ["git", "commit", "-m", "تحديث المشاريع والفريق الفني - لوحة التحكم"],
                check=True, capture_output=True, text=True
            )

            # Git push
            result = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True)

            if result.returncode == 0:
                self._send_json({"success": True, "message": "تم النشر بنجاح!"})
            else:
                self._send_json({"success": False, "message": f"فشل الـ push: {result.stderr}"})
        except subprocess.CalledProcessError as e:
            self._send_json({"success": False, "message": f"Git error: {e.stderr or str(e)}"})
        except Exception as e:
            self._send_json({"success": False, "message": str(e)})


def main():
    print()
    print("=" * 60)
    print("  🏗️  لوحة تحكم مؤسسة إبراهيم حميدي العنزي للمقاولات")
    print("=" * 60)
    print()
    print(f"  📁 مجلد المشروع: {BASE_DIR}")
    print(f"  🌐 لوحة التحكم:  http://localhost:{PORT}")
    print(f"  👁️  معاينة الموقع: http://localhost:{PORT}/index.html")
    print()
    print("  💡 اضغط Ctrl+C للإغلاق")
    print("=" * 60)
    print()

    server = HTTPServer(("127.0.0.1", PORT), AdminServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  ✋ تم إغلاق السيرفر. مع السلامة!\n")
        server.server_close()


if __name__ == "__main__":
    main()
