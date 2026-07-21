#!/usr/bin/env python3
"""
易经占卜 · Supabase Storage 部署脚本
将静态文件上传到 Supabase Storage 公开存储桶，通过 Supabase CDN 提供访问。

用法:
  python deploy_supabase.py

首次运行前，请在下方 SUPABASE_URL 和 SUPABASE_KEY 填入你的项目信息。
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ============ 配置区域 ============
# 从 Supabase Dashboard → Settings → API 获取
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xdsntdqiicczpleihbah.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # service_role key

BUCKET_NAME = "yijing"  # 存储桶名称

# 需要部署的文件列表
DEPLOY_FILES = [
    ("index.html",   "text/html"),
    ("app.js",       "application/javascript"),
    ("styles.css",   "text/css"),
    ("download.html","text/html"),
]
# ==================================

BASE_DIR = Path(__file__).parent


def api_request(method, path, data=None, content_type="application/json", is_binary=False):
    """发送 Supabase API 请求

    注意：新版 Supabase 密钥 (sb_publishable_ / sb_secret_) 不是 JWT，
    不能放在 Authorization: Bearer 头里，只能放在 apikey 头里。
    旧版 JWT 密钥 (anon / service_role) 可以同时放在两个头里。
    """
    url = f"{SUPABASE_URL}{path}"
    headers = {
        "apikey": SUPABASE_KEY,
    }
    # 旧版 JWT 密钥 (eyJ 开头) 可以放 Authorization 头
    # 新版密钥 (sb_ 开头) 只能放 apikey 头
    if SUPABASE_KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

    if is_binary:
        # 文件上传 - data 是 bytes
        headers["Content-Type"] = content_type
        headers["x-upsert"] = "true"  # 覆盖已存在的文件
        body = data
    else:
        headers["Content-Type"] = content_type
        body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return e.code, err_body
    except Exception as e:
        return -1, str(e)


def create_bucket():
    """检查/创建公开存储桶

    使用 service_role key 时可直接创建；使用 anon key 时若桶不存在，
    需要先在 Supabase Dashboard → Storage 里手动创建。
    """
    print(f"\n[1/3] 检查存储桶 '{BUCKET_NAME}'...")

    status, resp = api_request("GET", f"/storage/v1/bucket/{BUCKET_NAME}")
    if status == 200:
        print(f"  -> 存储桶已存在")
        return True

    # 使用 service_role 时尝试创建
    status, resp = api_request("POST", "/storage/v1/bucket", {
        "name": BUCKET_NAME,
        "id": BUCKET_NAME,
        "public": True,
        "file_size_limit": 52428800,  # 50MB
    })

    if status in (200, 201):
        print(f"  -> 存储桶创建成功")
        return True
    elif "already" in str(resp).lower() or status == 409:
        print(f"  -> 存储桶已存在，继续")
        return True
    else:
        # anon key 通常没有创建桶权限，但如果桶已存在仍可上传
        resp_str = str(resp).lower()
        if "row-level security" in resp_str or "unauthorized" in resp_str:
            print(f"  -> 当前密钥无创建桶权限，继续尝试上传（若桶已存在则会成功）")
            return True
        print(f"  -> 创建失败 [{status}]: {resp}")
        return False


def upload_file(filename, content_type):
    """上传单个文件"""
    filepath = BASE_DIR / filename
    if not filepath.exists():
        print(f"  -> [跳过] {filename} 不存在")
        return False

    file_data = filepath.read_bytes()
    size_kb = len(file_data) / 1024
    print(f"  -> 上传 {filename} ({size_kb:.1f} KB)...")

    status, resp = api_request(
        "POST",
        f"/storage/v1/object/{BUCKET_NAME}/{filename}",
        data=file_data,
        content_type=content_type,
        is_binary=True,
    )

    if status in (200, 201):
        print(f"     成功 ✓")
        return True
    else:
        print(f"     失败 [{status}]: {resp}")
        return False


def main():
    if not SUPABASE_KEY:
        print("=" * 50)
        print("错误: 未设置 SUPABASE_KEY")
        print()
        print("请通过环境变量传入:")
        print('  Windows CMD:  set SUPABASE_KEY=eyJhbG... && python deploy_supabase.py')
        print('  Windows PS:  $env:SUPABASE_KEY="eyJhbG..."; python deploy_supabase.py')
        print('  Bash:        SUPABASE_KEY=eyJhbG... python deploy_supabase.py')
        print()
        print("或在脚本顶部直接填入 SUPABASE_KEY 的值。")
        print()
        print("获取方式: Supabase Dashboard → Settings → API → service_role key")
        print("=" * 50)
        sys.exit(1)

    print("=" * 50)
    print("  易经占卜 · Supabase Storage 部署")
    print("=" * 50)
    print(f"  项目: {SUPABASE_URL}")
    print(f"  桶名: {BUCKET_NAME}")
    print(f"  文件: {', '.join(f[0] for f in DEPLOY_FILES)}")
    print("=" * 50)

    # 1. 创建存储桶
    if not create_bucket():
        print("\n部署失败: 无法创建存储桶")
        sys.exit(1)

    # 2. 上传文件
    print(f"\n[2/3] 上传文件...")
    success_count = 0
    for filename, content_type in DEPLOY_FILES:
        if upload_file(filename, content_type):
            success_count += 1

    # 3. 输出访问地址
    print(f"\n[3/3] 部署完成!")
    print(f"  成功上传: {success_count}/{len(DEPLOY_FILES)} 个文件")
    print()
    print("=" * 50)
    print("  访问地址:")
    print(f"  主页: {SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/index.html")
    print(f"  下载: {SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/download.html")
    print("=" * 50)


if __name__ == "__main__":
    main()
