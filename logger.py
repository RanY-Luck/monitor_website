from loguru import logger as log
import sys

# 配置 logger
log.remove()  # 移除默认处理程序
log.add(sys.stderr, level="INFO")  # 添加新的处理程序
log.add("logs/monitor.log", rotation="10 MB", retention="10 days", level="DEBUG")

# 导出 log 对象
__all__ = ["log"]
