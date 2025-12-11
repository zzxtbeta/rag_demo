"""MarkItDown 文档转换器 - 支持多格式文件转换为 Markdown."""

from __future__ import annotations

import io
import logging
import os
import shutil
import sys
import tempfile
import time
import warnings
from typing import Optional

# 抑制 pydub ffmpeg 警告（因为我们禁用了音频处理插件）
warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning)

from markitdown import MarkItDown

logger = logging.getLogger(__name__)

# 全局 MarkItDown 转换器实例（单例）
_converter: Optional[MarkItDown] = None


def get_converter() -> MarkItDown:
    """获取或初始化 MarkItDown 转换器（禁用所有插件以避免 ffmpeg 依赖）."""
    global _converter
    if _converter is None:
        try:
            # 禁用所有插件以避免 ffmpeg 和其他外部依赖
            _converter = MarkItDown(enable_plugins=False)
            logger.info("[MARKITDOWN] 转换器已初始化（插件已禁用）")
        except Exception as e:
            logger.error(f"[MARKITDOWN] 转换器初始化失败: {str(e)}")
            raise
    return _converter


async def convert_file_to_markdown(
    file_path: str,
    filename: str,
    timeout: int = 60,
) -> tuple[str, float]:
    """
    将文件转换为 Markdown.

    参数：
        file_path: 待转换文件的路径
        filename: 原始文件名（用于日志）
        timeout: 转换超时时间（秒）

    返回：
        (markdown_content, conversion_time_ms) 元组

    异常：
        TimeoutError: 转换超时
        Exception: 转换失败
    """
    start_time = time.time()
    converter = get_converter()

    try:
        logger.info(f"[MARKITDOWN] 开始转换: {filename}")
        
        # 确保文件存在且可读
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"文件无法读取: {file_path}")
        
        result = converter.convert(file_path)
        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(f"[MARKITDOWN] 转换完成 {filename} 耗时 {elapsed_ms:.1f}ms")
        return result.text_content, elapsed_ms

    except Exception as e:
        logger.error(f"[MARKITDOWN] 转换失败 {filename}: {str(e)}")
        raise


async def convert_upload_file(
    file_bytes: bytes,
    filename: str,
    timeout: int = 60,
) -> tuple[str, float]:
    """
    将上传的文件字节转换为 Markdown.

    参数：
        file_bytes: 文件内容字节
        filename: 原始文件名
        timeout: 转换超时时间（秒）

    返回：
        (markdown_content, conversion_time_ms) 元组
    """
    # 创建临时目录以存储文件
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, filename)
    
    try:
        # 写入文件内容到磁盘
        with open(tmp_path, 'wb') as f:
            f.write(file_bytes)
        
        logger.debug(f"[MARKITDOWN] 临时文件已创建: {tmp_path} ({len(file_bytes)} 字节)")
        
        # 转换文件（按官方文档用法：传入文件路径字符串）
        start_time = time.time()
        converter = get_converter()
        
        logger.info(f"[MARKITDOWN] 开始转换: {filename}")
        
        # 确保文件存在且可读
        if not os.path.exists(tmp_path):
            raise FileNotFoundError(f"文件不存在: {tmp_path}")
        
        if not os.access(tmp_path, os.R_OK):
            raise PermissionError(f"文件无法读取: {tmp_path}")
        
        # 调用 MarkItDown 转换（官方用法：converter.convert(file_path_string)）
        result = converter.convert(tmp_path)
        markdown_content = result.text_content
        elapsed_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[MARKITDOWN] 转换完成 {filename} 耗时 {elapsed_ms:.1f}ms")
        
        return markdown_content, elapsed_ms
    
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[MARKITDOWN] 转换失败 {filename}: {error_msg}")
        raise
    
    finally:
        # 清理临时目录及其所有内容
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
                logger.debug(f"[MARKITDOWN] 临时目录已清理: {tmp_dir}")
        except Exception as e:
            logger.warning(f"[MARKITDOWN] 删除临时目录失败 {tmp_dir}: {str(e)}")


__all__ = ["get_converter", "convert_file_to_markdown", "convert_upload_file"]
