# -*- coding: utf-8 -*-
import requests
import os
import json
import time
from dotenv import load_dotenv
from logger import log
from bot import WeComNotifier

# 加载环境变量
load_dotenv()

# 配置
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", 60))
REPORT_ONLY_ON_ERROR = os.getenv("REPORT_ONLY_ON_ERROR", "true").lower() == "true"

def check_single_url(name, url):
    """
    检查单个URL状态
    返回: dict {'name': name, 'success': bool, 'code': int, 'msg': str}
    """
    if not url:
        return {'name': name, 'success': True, 'code': 0, 'msg': '未配置URL (跳过)'}

    log.info(f"正在检查 {name}: {url}")

    try:
        response = requests.get(url, timeout=30)
        code = response.status_code
        
        # 调试输出
        log.debug(f"[{name}] HTTP状态码: {code}")
        
        try:
            data = response.json()
            # log.debug(f"[{name}] 响应内容: {json.dumps(data, ensure_ascii=False)}")
        except ValueError:
            return {
                'name': name, 
                'success': False, 
                'code': code, 
                'msg': f"响应不是有效的 JSON: {response.text[:100]}..."
            }

        # 严格校验规则
        # 规则: {'statusCode': 200, 'message': None, 'data': '1'}
        expected_response = {'statusCode': 200, 'message': None, 'data': '1'}
        
        if data != expected_response:
             # 生成差异
            return {
                'name': name,
                'success': False,
                'code': code,
                'msg': f"数据不符合预期!\n期望: {expected_response}\n实际: {data}"
            }
        else:
            return {
                'name': name,
                'success': True,
                'code': code,
                'msg': json.dumps(data, ensure_ascii=False)
            }

    except requests.exceptions.RequestException as e:
        return {
            'name': name,
            'success': False,
            'code': 0,
            'msg': f"请求异常: {str(e)}"
        }
    except Exception as e:
        return {
            'name': name,
            'success': False,
            'code': 0,
            'msg': f"未知错误: {str(e)}"
        }

def run_monitor_loop():
    """
    主监控循环
    """
    webhook_url = os.getenv("WEBHOOK_URL")
    notifier = None
    
    if not webhook_url or "YOUR_KEY_HERE" in webhook_url:
        log.warning("未配置有效的 WEBHOOK_URL，将仅打印日志")
    else:
        notifier = WeComNotifier(webhook_url)

    # 定义要监控的列表
    # 每次循环重新读取环境变量，以便支持动态修改（如果运行环境支持热加载env的话，通常docker需要重启，但本地改文件可能生效） 
    # Update: dotenv通常只加载一次。如果需要动态配置，得重写加载逻辑，但简便起见，这里假设重启生效。
    
    log.info(f"监控服务启动 | 检查间隔: {MONITOR_INTERVAL}秒 | 仅报错推送: {REPORT_ONLY_ON_ERROR}")
    
    while True:
        monitors = [
            ("正式服", os.getenv("MONITOR_URL_PROD")),
            ("测试服", os.getenv("MONITOR_URL_TEST"))
        ]
        
        results = []
        has_error = False
        
        for name, url in monitors:
            result = check_single_url(name, url)
            results.append(result)
            if not result['success']:
                has_error = True
        
        # 决定是否发送通知
        should_notify = False
        if notifier:
            if has_error:
                should_notify = True
                log.error("发现异常，准备发送通知...")
            elif not REPORT_ONLY_ON_ERROR:
                should_notify = True
                log.info("发送定期报告...")
        
        if should_notify and notifier:
            try:
                notifier.send_monitor_report(results)
            except Exception as e:
                log.error(f"发送通知失败: {e}")
        
        if not has_error:
            log.info("本轮检查全部通过 ✅")
            
        time.sleep(MONITOR_INTERVAL)

if __name__ == "__main__":
    try:
        run_monitor_loop()
    except KeyboardInterrupt:
        log.info("停止监控")
