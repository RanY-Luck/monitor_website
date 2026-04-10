#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time     : 2025/12/5 11:34
# @Author   : 冉勇
# @File     : bot.py
# @Software : PyCharm
# @Desc     : 企业微信通知模块
import requests
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception
from pathlib import Path
from logger import log

try:
    BEIJING_TIMEZONE = ZoneInfo('Asia/Shanghai') if ZoneInfo else timezone(timedelta(hours=8), name='Asia/Shanghai')
except ZoneInfoNotFoundError:
    BEIJING_TIMEZONE = timezone(timedelta(hours=8), name='Asia/Shanghai')


class WeComNotifier:
    """企业微信机器人通知类"""

    def __init__(self, webhook_url):
        """
        初始化企业微信机器人

        参数:
            webhook_url: 企业微信机器人的Webhook地址
        """
        self.webhook_url = webhook_url
        # 从webhook_url提取key，用于文件上传
        self.robot_key = self._extract_key_from_webhook(webhook_url)
        log.info(f"企业微信通知器初始化完成")

    def _extract_key_from_webhook(self, webhook_url):
        """从webhook URL中提取key"""
        try:
            # webhook格式: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx
            if 'key=' in webhook_url:
                return webhook_url.split('key=')[1].split('&')[0]
            return None
        except:
            return None

    def _now(self):
        return datetime.now(BEIJING_TIMEZONE)

    def _format_now(self):
        return self._now().strftime('%Y-%m-%d %H:%M:%S')

    def upload_file(self, file_path):
        """
        上传文件到企业微信，获取media_id

        参数:
            file_path: 文件路径

        返回:
            (success: bool, media_id: str, message: str)
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                error_msg = f"文件不存在: {file_path}"
                log.error(error_msg)
                return False, None, error_msg

            # 检查文件大小（企业微信限制20MB）
            file_size = file_path.stat().st_size
            if file_size > 20 * 1024 * 1024:
                error_msg = f"文件过大: {file_size / 1024 / 1024:.2f}MB，超过20MB限制"
                log.error(error_msg)
                return False, None, error_msg

            log.info(f"开始上传文件: {file_path.name} ({file_size / 1024:.2f}KB)")

            # 企业微信文件上传接口
            upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={self.robot_key}&type=file"

            # 读取文件
            with open(file_path, 'rb') as f:
                files = {
                    'media': (file_path.name, f, 'application/octet-stream')
                }

                response = requests.post(upload_url, files=files, timeout=30)
                result = response.json()

                if result.get('errcode') == 0:
                    media_id = result.get('media_id')
                    log.success(f"✅ 文件上传成功，media_id: {media_id}")
                    return True, media_id, "上传成功"
                else:
                    error_msg = f"上传失败: {result.get('errmsg')}"
                    log.error(f"❌ {error_msg}")
                    return False, None, error_msg

        except requests.exceptions.Timeout:
            error_msg = "文件上传超时"
            log.error(f"❌ {error_msg}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"文件上传异常: {str(e)}"
            log.error(error_msg, exc_info=True)
            return False, None, error_msg

    def send_file(self, file_path):
        """
        发送文件到企业微信

        参数:
            file_path: 文件路径

        返回:
            (success: bool, message: str)
        """
        try:
            # 先上传文件获取media_id
            success, media_id, msg = self.upload_file(file_path)

            if not success:
                return False, msg

            # 发送文件消息
            data = {
                "msgtype": "file",
                "file": {
                    "media_id": media_id
                }
            }

            log.info("正在发送文件消息...")
            return self._send(data, "文件消息")

        except Exception as e:
            error_msg = f"发送文件失败: {str(e)}"
            log.error(error_msg, exc_info=True)
            return False, error_msg

    def send_text(self, content, mentioned_list=None, mentioned_mobile_list=None):
        """
        发送文本消息

        参数:
            content: 文本内容
            mentioned_list: 要@的用户列表（userid）
            mentioned_mobile_list: 要@的用户手机号列表
        """
        data = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list or [],
                "mentioned_mobile_list": mentioned_mobile_list or []
            }
        }
        return self._send(data, "文本消息")

    def send_markdown(self, content):
        """
        发送Markdown消息

        参数:
            content: Markdown格式的内容
        """
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        return self._send(data, "Markdown消息")

    def send_device_report_with_file(self, content, file_path=None):
        """
        发送设备报告（包含Excel文件）

        参数:
            content: Markdown格式的报告内容
            file_path: Excel文件路径（可选）

        返回:
            (success: bool, message: str)
        """
        try:
            # 先发送报告内容
            success, msg = self.send_markdown(content)

            if not success:
                return success, msg

            # 如果有文件，直接发送文件
            if file_path:
                file_path = Path(file_path)
                if file_path.exists():
                    log.info(f"准备发送Excel文件: {file_path.name}")

                    # 直接发送文件
                    file_success, file_msg = self.send_file(file_path)

                    if file_success:
                        log.success(f"✅ Excel文件发送成功")
                    else:
                        log.error(f"❌ Excel文件发送失败: {file_msg}")
                        # 文件发送失败时，发送文件路径提示
                        fallback_content = f"""# 📊 详细报告文件

**文件名**: `{file_path.name}`
**大小**: {file_path.stat().st_size / 1024:.2f} KB
**路径**: `{file_path.absolute()}`

> ⚠️ 文件发送失败: {file_msg}
> 💡 请从服务器路径直接获取文件
"""
                        self.send_markdown(fallback_content)

                    return file_success, file_msg

            return True, "报告发送成功"

        except Exception as e:
            error_msg = f"发送报告失败: {str(e)}"
            log.error(error_msg, exc_info=True)
            return False, error_msg

    def _send(self, data, msg_type="消息"):
        """
        发送消息到企业微信

        参数:
            data: 消息数据
            msg_type: 消息类型（用于日志）
        """
        try:
            log.debug(f"正在发送{msg_type}到企业微信...")

            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            result = response.json()

            if result.get('errcode') == 0:
                log.success(f"✅ {msg_type}发送成功")
                return True, "发送成功"
            else:
                error_msg = f"发送失败: {result.get('errmsg')}"
                log.error(f"❌ {msg_type}{error_msg}")
                return False, error_msg

        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            log.error(f"❌ {msg_type}发送超时")
            return False, error_msg
        except Exception as e:
            error_msg = f"发送异常: {str(e)}"
            log.error(f"❌ {msg_type}{error_msg}", exc_info=True)
            return False, error_msg

    def send_error_alert(self, error_message, device_id=None):
        """
        发送错误警报

        参数:
            error_message: 错误信息
            device_id: 设备ID（可选）
        """
        current_time = self._format_now()

        log.error(f"发送错误警报: {error_message}")

        content = f"""# ⚠️ 系统异常告警

> **时间**: {current_time}

## ❌ 错误信息
{error_message}
"""

        if device_id:
            content += f"\n**设备ID**: {device_id}"

        content += "\n\n> 请及时检查处理！"

        return self.send_markdown(content)

    def send_batch_result(
            self,
            results,
            format_name,
            total_devices,
            loop_count=1,
            concurrent_batch=10,
            delay_seconds=10,
            send_interval=0,
            host="",
            port=0,
            total_duration=None,
            success_rate=None,
            excel_file_path=None
    ):
        """发送优化的企业微信 Markdown 批量发送报告"""

        log.info("开始生成批量发送报告...")

        # 数据统计
        total_attempts = len(results)
        success_count = sum(1 for r in results if r['success'])
        failed_count = total_attempts - success_count

        # 计算成功率
        calculated_rate = (success_count / total_attempts * 100) if total_attempts > 0 else 0.0
        display_rate = success_rate if success_rate is not None else f"{calculated_rate:.2f}"
        rate_num = float(display_rate)

        # 获取当前时间
        current_time = self._format_now()

        # 状态判断
        if rate_num == 100:
            status_emoji = "✅"
            status_text = "全部成功"
            status_detail = "所有设备均成功发送！"
            status_color = "info"
        elif rate_num >= 95:
            status_emoji = "✅"
            status_text = "基本成功"
            status_detail = "仅少量失败，可忽略"
            status_color = "info"
        elif rate_num >= 80:
            status_emoji = "⚠️"
            status_text = "部分失败"
            status_detail = "建议检查网络连接"
            status_color = "warning"
        else:
            status_emoji = "❌"
            status_text = "大量失败"
            status_detail = "请立即处理！"
            status_color = "warning"

        # 按轮次统计
        loop_stats = []
        for loop_idx in range(loop_count):
            loop_results = [r for r in results if r.get('loop') == loop_idx + 1]
            if loop_results:
                loop_success = sum(1 for r in loop_results if r['success'])
                loop_stats.append(
                    {
                        'loop': loop_idx + 1,
                        'success': loop_success,
                        'total': len(loop_results)
                    }
                )

        # 失败设备统计
        all_failed = [r['device_id'] for r in results if not r['success']]
        failed_devices = all_failed[:10]
        total_failed = len(all_failed)

        # 构建 Markdown
        content = f"""# 📊 TCP 设备批量发送报告

> **发送时间**: {current_time}
> **目标地址**: {host}
> **执行状态**: {status_emoji} **{status_text}** - {status_detail}

## 📈 总体统计
- **设备总数**: {total_devices} 台
- **循环次数**: {loop_count} 轮
- **总发送次数**: {total_attempts} 次
- **成功次数**: <font color="{status_color}">**{success_count}**</font> 次
- **失败次数**: <font color="warning">**{failed_count}**</font> 次
- **成功率**: <font color="{status_color}">**{display_rate}%**</font>"""

        if total_duration:
            content += f"\n- **总耗时**: {total_duration}"

        content += f"""

## ⚙️ 发送配置
- **并发批次**: {concurrent_batch} 台/批
- **连接保持**: {delay_seconds} 秒
- **批次间隔**: {send_interval if send_interval > 0 else '无间隔'} 秒
- **数据格式**: {format_name}

## 📋 各轮次明细
"""

        # 添加每轮统计
        for stat in loop_stats:
            loop_rate = (stat['success'] / stat['total'] * 100) if stat['total'] > 0 else 0
            loop_emoji = "✅" if loop_rate == 100 else ("⚠️" if loop_rate >= 80 else "❌")
            content += f"\n{loop_emoji} **第 {stat['loop']} 轮**: {stat['success']}/{stat['total']} 成功 ({loop_rate:.1f}%)\n"

        # 失败设备列表
        if failed_devices:
            content += f"\n## ❌ 失败设备列表\n"
            for idx, device_id in enumerate(failed_devices, 1):
                content += f"{idx}. `{device_id}`\n"

            if total_failed > 10:
                content += f"\n> 还有 {total_failed - 10} 台设备失败，共计 **{total_failed}** 台\n"

        # 先发送报告
        success, msg = self.send_markdown(content)

        # 如果有Excel文件，发送文件
        if success and excel_file_path:
            log.info(f"发送Excel文件: {excel_file_path}")
            self.send_file(excel_file_path)

        return success, msg

    def send_start_notification(
            self, total_devices, loop_count, concurrent_batch,
            delay_seconds, send_interval, host, port, format_name
    ):
        """发送批量发送任务的开始通知"""

        log.info("发送任务开始通知...")

        current_time = self._format_now()

        # 预估耗时计算
        if send_interval > 0:
            batch_count = (total_devices + concurrent_batch - 1) // concurrent_batch
            single_round_time = (batch_count * send_interval) + delay_seconds
        else:
            single_round_time = (total_devices * 0.1) + delay_seconds

        total_time_seconds = single_round_time * loop_count
        total_time_minutes = total_time_seconds / 60

        if total_time_minutes < 1:
            time_display = f"约 {total_time_seconds:.0f} 秒"
        elif total_time_minutes < 60:
            time_display = f"约 {total_time_minutes:.1f} 分钟"
        else:
            hours = int(total_time_minutes // 60)
            minutes = int(total_time_minutes % 60)
            time_display = f"约 {hours} 小时 {minutes} 分钟"

        estimated_end_time = self._now() + timedelta(seconds=total_time_seconds)
        estimated_end_str = estimated_end_time.strftime('%H:%M:%S')

        content = f"""# 🚀 TCP 设备批量发送任务

> **开始时间**: {current_time}
> **目标地址**: {host}
> **预计完成**: {estimated_end_str} ({time_display})

## 📋 任务配置
- **设备总数**: {total_devices} 台
- **循环次数**: {loop_count} 轮
- **总发送次数**: {total_devices * loop_count} 次
- **并发批次**: {concurrent_batch} 台/批
- **连接保持**: {delay_seconds} 秒
- **批次间隔**: {send_interval if send_interval > 0 else '无间隔'} 秒
- **数据格式**: {format_name}

## 🔄 执行状态
⏳ **正在执行中**，请稍候...
"""

        return self.send_markdown(content)


    def send_monitor_report(self, results):
        """
        发送监控报告
        
        参数:
            results: list, 监控结果列表 [{'name': '正式服', 'success': True, 'msg': '...', 'code': 200}, ...]
        """
        current_time = self._format_now()
        
        # 统计
        total = len(results)
        success_count = sum(1 for r in results if r.get('success'))
        fail_count = total - success_count
        
        # 状态判断
        if fail_count == 0:
            status_emoji = "✅"
            status_text = "系统正常"
            status_color = "info"
        else:
            status_emoji = "❌"
            status_text = "发现异常" 
            status_color = "warning"

        content = f"""# 🔍 网站监控报告
> 时间: {current_time}
> 状态: {status_emoji} <font color="{status_color}">**{status_text}**</font>

## 📊 概览
- ✅ **正常**: {success_count}
- ❌ **异常**: {fail_count}
- ⚠️ **总计**: {total}

## 📋 详情
"""
        
        for r in results:
            name = r.get('name', '未知服务')
            is_success = r.get('success', False)
            code = r.get('code', 'N/A')
            msg = r.get('msg', '无详情')
            
            icon = "✅" if is_success else "❌"
            
            content += f"### {icon} {name}\n"
            content += f"- **状态码**: `{code}`\n"
            if not is_success:
                content += f"- **错误详情**: \n> {msg}\n"
            else:
                 content += f"- **响应**: {msg}\n"
            content += "\n"

        return self.send_markdown(content)


# 使用示例
# if __name__ == "__main__":
#     webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
#     notifier = WeComNotifier(webhook_url)
#     results = [
#         {'name': '正式服', 'success': True, 'code': 200, 'msg': 'OK'},
#         {'name': '测试服', 'success': False, 'code': 500, 'msg': 'Internal Server Error'}
#     ]
#     notifier.send_monitor_report(results)

