#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

import uvicorn

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 设置颜色（跨平台）
class Colors:
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_logo():
    logo = f"""
{Colors.CYAN}{Colors.BOLD}
     ██████╗ ██████╗  █████╗ ██╗   ██╗ █████╗ ██╗████████╗██╗   ██╗
    ██╔════╝ ██╔══██╗██╔══██╗██║   ██║██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
    ██║  ███╗██████╔╝███████║██║   ██║███████║██║   ██║    ╚████╔╝ 
    ██║   ██║██╔══██╗██╔══██║╚██╗ ██╔╝██╔══██║██║   ██║     ╚██╔╝  
    ╚██████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║  ██║██║   ██║      ██║   
     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   
{Colors.RESET}
{Colors.YELLOW}                    Welcome to GravAIty{Colors.RESET}
"""
    print(logo)

def main():
    # 获取项目根目录
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    src_dir = root_dir / "src"

    # 确保 src 在 sys.path 中
    sys.path.insert(0, str(src_dir))

    # 打印 logo
    print_logo()

    # 启动 FastAPI
    print(f"{Colors.GREEN}Starting FastAPI backend...{Colors.RESET}\n")

    config = uvicorn.Config("api.app:app", host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Server stopped.{Colors.RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()