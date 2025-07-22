#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import subprocess
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VnstatTrafficExporter:
    def __init__(self):
        # 从环境变量获取配置
        self.webhook_path = os.getenv('WEBHOOK_PATH', '/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae')
        self.start_day = int(os.getenv('START_DAY', '1'))  # 每月的起始日期
        self.port = int(os.getenv('PORT', '50000'))
        
        # 数据缓存
        self.cached_data = {
            "start_date": "",
            "in": 0,
            "out": 0
        }
        
        # 创建Flask应用
        self.app = Flask(__name__)
        self.setup_routes()
        
        # 启动数据收集线程
        self.data_thread = threading.Thread(target=self.data_collection_loop, daemon=True)
        self.data_thread.start()
        
        logger.info(f"VnstatTrafficExporter初始化完成")
        logger.info(f"Webhook路径: {self.webhook_path}")
        logger.info(f"起始日期: 每月{self.start_day}号")
        logger.info(f"端口: {self.port}")

    def setup_routes(self):
        """设置Flask路由"""
        @self.app.route(self.webhook_path, methods=['GET'])
        def webhook():
            return jsonify(self.cached_data)
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

    def calculate_start_date(self):
        """计算起始日期"""
        now = datetime.now()
        current_day = now.day
        
        if current_day >= self.start_day:
            # 本月的起始日期到今天
            start_date = datetime(now.year, now.month, self.start_day)
        else:
            # 上个月的起始日期到今天
            if now.month == 1:
                start_date = datetime(now.year - 1, 12, self.start_day)
            else:
                start_date = datetime(now.year, now.month - 1, self.start_day)
        
        return start_date

    def get_best_interface(self):
        """获取最佳网络接口"""
        try:
            # 执行vnstat --iflist命令
            result = subprocess.run(['vnstat', '--iflist'], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning(f"获取接口列表失败: {result.stderr}")
                return None
            
            # 解析输出，格式: "Available interfaces: eth0 docker0"
            output = result.stdout.strip()
            logger.info(f"vnstat --iflist 输出: {output}")
            
            if 'Available interfaces:' not in output:
                logger.warning("vnstat输出格式不符合预期")
                return None
            
            # 提取接口列表
            interface_part = output.split('Available interfaces:')[1].strip()
            interfaces = interface_part.split()
            
            logger.info(f"发现的接口: {interfaces}")
            
            # 过滤和排序接口
            preferred_interfaces = []
            
            for iface in interfaces:
                iface = iface.strip()
                if not iface:
                    continue
                
                # 跳过虚拟接口
                skip_prefixes = ('lo', 'docker', 'br-', 'veth', 'virbr')
                if any(iface.startswith(prefix) for prefix in skip_prefixes):
                    continue
                
                preferred_interfaces.append(iface)
            
            if not preferred_interfaces:
                logger.warning("未找到合适的物理网络接口")
                return None
            
            # 优先选择物理网卡接口
            for iface in preferred_interfaces:
                if iface.startswith(('eth', 'ens', 'enp', 'en', 'wlan', 'wlp')):
                    logger.info(f"选择网络接口: {iface}")
                    return iface
            
            # 如果没有找到标准命名的接口，选择第一个
            selected = preferred_interfaces[0]
            logger.info(f"选择网络接口: {selected}")
            return selected
            
        except subprocess.TimeoutExpired:
            logger.error("获取接口列表超时")
            return None
        except Exception as e:
            logger.error(f"获取接口列表时发生错误: {e}")
            return None

    def run_vnstat_command(self, start_date):
        """执行vnstat命令获取流量数据"""
        try:
            end_date = datetime.now()
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # 获取最佳接口
            interface = self.get_best_interface()
            
            if interface:
                # 使用指定接口获取流量数据
                cmd = ['vnstat', '-i', interface, '--begin', start_date_str, '--end', end_date_str, '--json']
                logger.info(f"使用接口 {interface} 获取流量数据")
            else:
                # 使用默认命令（所有接口）
                cmd = ['vnstat', '--begin', start_date_str, '--end', end_date_str, '--json']
                logger.info("使用默认命令获取流量数据")
            
            logger.info(f"执行vnstat命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return result.stdout, start_date_str
            else:
                logger.error(f"vnstat命令执行失败: {result.stderr}")
                return None, start_date_str
                
        except subprocess.TimeoutExpired:
            logger.error("vnstat命令执行超时")
            return None, start_date_str
        except Exception as e:
            logger.error(f"执行vnstat命令时发生错误: {e}")
            return None, start_date_str

    def parse_vnstat_output(self, output):
        """解析vnstat的JSON输出"""
        try:
            data = json.loads(output)
            
            total_rx = 0  # 接收字节数 (入站)
            total_tx = 0  # 发送字节数 (出站)
            
            # vnstat JSON格式可能因版本而异，这里处理常见的格式
            if 'interfaces' in data:
                for interface in data['interfaces']:
                    if 'traffic' in interface:
                        traffic = interface['traffic']
                        if 'total' in traffic:
                            total_rx += traffic['total'].get('rx', 0)
                            total_tx += traffic['total'].get('tx', 0)
                        elif 'day' in traffic:
                            # 如果有按天的数据，累加所有天的数据
                            for day_data in traffic['day']:
                                total_rx += day_data.get('rx', 0)
                                total_tx += day_data.get('tx', 0)
            
            # 转换为MB
            total_rx_mb = round(total_rx / (1024 * 1024), 2)
            total_tx_mb = round(total_tx / (1024 * 1024), 2)
            
            return total_rx_mb, total_tx_mb
            
        except json.JSONDecodeError as e:
            logger.error(f"解析vnstat JSON输出失败: {e}")
            # 如果JSON解析失败，尝试解析文本输出
            return self.parse_vnstat_text_output(output)
        except Exception as e:
            logger.error(f"处理vnstat输出时发生错误: {e}")
            return 0, 0

    def parse_vnstat_text_output(self, output):
        """解析vnstat的文本输出（作为JSON解析的备选方案）"""
        try:
            total_rx = 0
            total_tx = 0
            
            # 使用正则表达式从文本输出中提取流量数据
            lines = output.split('\n')
            for line in lines:
                # 寻找包含流量数据的行
                if 'rx:' in line.lower() and 'tx:' in line.lower():
                    # 提取数字
                    rx_match = re.search(r'rx:\s*([0-9.]+)\s*([KMGT]?B)', line, re.IGNORECASE)
                    tx_match = re.search(r'tx:\s*([0-9.]+)\s*([KMGT]?B)', line, re.IGNORECASE)
                    
                    if rx_match:
                        rx_value = float(rx_match.group(1))
                        rx_unit = rx_match.group(2).upper()
                        total_rx += self.convert_to_mb(rx_value, rx_unit)
                    
                    if tx_match:
                        tx_value = float(tx_match.group(1))
                        tx_unit = tx_match.group(2).upper()
                        total_tx += self.convert_to_mb(tx_value, tx_unit)
            
            return round(total_rx, 2), round(total_tx, 2)
            
        except Exception as e:
            logger.error(f"解析文本输出时发生错误: {e}")
            return 0, 0

    def convert_to_mb(self, value, unit):
        """将流量数据转换为MB"""
        unit = unit.upper()
        if unit == 'B':
            return value / (1024 * 1024)
        elif unit == 'KB':
            return value / 1024
        elif unit == 'MB':
            return value
        elif unit == 'GB':
            return value * 1024
        elif unit == 'TB':
            return value * 1024 * 1024
        else:
            return value

    def update_cached_data(self):
        """更新缓存的数据"""
        try:
            start_date = self.calculate_start_date()
            vnstat_output, start_date_str = self.run_vnstat_command(start_date)
            
            if vnstat_output:
                rx_mb, tx_mb = self.parse_vnstat_output(vnstat_output)
                
                self.cached_data = {
                    "start_date": start_date_str,
                    "in": rx_mb,
                    "out": tx_mb
                }
                
                logger.info(f"数据更新成功: {self.cached_data}")
            else:
                logger.warning("vnstat命令执行失败，使用上次缓存的数据")
                
        except Exception as e:
            logger.error(f"更新缓存数据时发生错误: {e}")

    def data_collection_loop(self):
        """数据收集循环，每5分钟执行一次"""
        logger.info("数据收集线程已启动")
        
        # 立即执行一次数据更新
        self.update_cached_data()
        
        while True:
            try:
                time.sleep(300)  # 5分钟 = 300秒
                self.update_cached_data()
            except Exception as e:
                logger.error(f"数据收集循环中发生错误: {e}")
                time.sleep(60)  # 发生错误时等待1分钟后重试

    def run(self):
        """启动Flask应用"""
        logger.info(f"启动Web服务，端口: {self.port}")
        logger.info(f"Webhook URL: http://localhost:{self.port}{self.webhook_path}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)

def main():
    exporter = VnstatTrafficExporter()
    exporter.run()

if __name__ == '__main__':
    main() 