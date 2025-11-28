import sys
import os
import json
import importlib.util
import logging
import requests
import time
import traceback
from flask import Flask, Response

# 设置日志格式
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def load_spider_class(filepath):
    """动态加载 Python 脚本中的 Spider 类"""
    try:
        if not os.path.isabs(filepath):
            filepath = os.path.join(os.getcwd(), filepath)

        if not os.path.exists(filepath):
            logger.error(f"FATAL: 文件不存在 -> {filepath}")
            return None

        module_name = os.path.basename(filepath).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        
        if spec is None or spec.loader is None:
            logger.error(f"FATAL: 无法读取模块 -> {filepath}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'Spider'):
            return module.Spider
        else:
            logger.error(f"模块中未找到 Spider 类: {module_name}")
            return None
    except Exception as e:
        logger.exception(f"加载模块异常 {filepath}: {e}")
        return None

@app.route('/')
def index():
    return """
    <h1>IPTV Service Online</h1>
    <p>服务已运行，但如果获取不到数据，请点击下方链接排查：</p>
    <ul>
        <li><a href='/iptv.m3u'>获取订阅链接 (M3U)</a></li>
        <li><a href='/debug'><b>进入诊断模式 (Debug)</b></a> - 点这里看详细报错</li>
    </ul>
    """

@app.route('/debug')
def debug_page():
    logs = []
    
    def log(msg):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        line = f"[{timestamp}] {msg}"
        print(line)
        logs.append(line)

    log("=== 开始网络环境诊断 ===")
    
    # 1. 测试外部网络连通性
    try:
        ip_info = requests.get('https://api.ipify.org?format=json', timeout=5).json()
        log(f"当前服务器公网 IP: {ip_info.get('ip')} (请检查该IP是否被目标站屏蔽)")
    except Exception as e:
        log(f"无法获取公网 IP (网络可能不通): {e}")

    # 2. 测试目标网站连通性
    targets = [
        ("快直播 API", "https://kzb29rda.com/prod-api/iptv/getIptvList?liveType=0&deviceType=1"),
        ("Yoo体育", "http://www.yoozb.live/")
    ]

    for name, url in targets:
        log(f"正在测试连接: {name}...")
        try:
            # 模拟浏览器的 Header
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            start = time.time()
            resp = requests.get(url, headers=headers, timeout=10, verify=False)
            latency = (time.time() - start) * 1000
            log(f"  -> 连接成功! 状态码: {resp.status_code}, 耗时: {latency:.0f}ms")
            log(f"  -> 返回数据长度: {len(resp.content)} bytes")
            if resp.status_code != 200:
                log(f"  -> 警告: 状态码非 200，可能是被拦截或服务器错误。")
                log(f"  -> 返回前100字符: {resp.text[:100]}")
        except Exception as e:
            log(f"  -> 连接失败! 错误信息: {str(e)}")

    log("\n=== 开始脚本执行测试 ===")
    
    # 3. 模拟执行爬虫
    try:
        config_path = 'iptv.json'
        if not os.path.exists(config_path):
             config_path = 'app/iptv.json'
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for item in config.get('lives', []):
                name = item.get('name')
                api_path = item.get('api')
                clean_path = api_path.replace('file://', '')
                if not os.path.isabs(clean_path):
                    clean_path = os.path.join(os.getcwd(), clean_path)
                
                log(f"执行脚本: {name}")
                SpiderClass = load_spider_class(clean_path)
                if SpiderClass:
                    try:
                        spider = SpiderClass()
                        spider.init(json.dumps(item.get('ext', {})))
                        
                        # 捕获标准输出 (stdout) 是很难的，我们这里只能看返回值
                        # 真正的错误通常是打印出来的，这里我们尝试捕获异常
                        content = spider.liveContent(None)
                        lines = content.split('\n')
                        valid_count = sum(1 for l in lines if l.strip() and '#EXT' not in l)
                        log(f"  -> 执行完成。获取到结果行数: {len(lines)}")
                        log(f"  -> 有效频道数 (估算): {valid_count // 2}")
                        
                        # 检查是否有错误标记
                        error_lines = [l for l in lines if "错误" in l or "Error" in l]
                        if error_lines:
                             log(f"  -> 发现脚本返回了错误信息: {error_lines}")
                        else:
                             log(f"  -> 脚本看似运行正常")
                             
                    except Exception as e:
                        log(f"  -> 脚本运行时崩溃: {traceback.format_exc()}")
                else:
                    log(f"  -> 无法加载脚本类")
        else:
            log("找不到 iptv.json")

    except Exception as e:
        log(f"测试过程发生未知错误: {e}")

    # 生成 HTML 报告
    html = """
    <html>
    <head>
        <title>Debug Report</title>
        <style>
            body { background: #1e1e1e; color: #d4d4d4; font-family: monospace; padding: 20px; }
            .log { white-space: pre-wrap; word-wrap: break-word; }
            .success { color: #4ec9b0; }
            .error { color: #f44747; }
            .warning { color: #cca700; }
        </style>
    </head>
    <body>
        <h2>IPTV Debug Log</h2>
        <div class="log">
    """
    for line in logs:
        color_class = ""
        if "失败" in line or "错误" in line or "Error" in line: color_class = "error"
        elif "成功" in line: color_class = "success"
        elif "警告" in line: color_class = "warning"
        
        html += f'<div class="{color_class}">{line}</div>'
    
    html += "</div></body></html>"
    return html

@app.route('/iptv.m3u')
def get_m3u():
    m3u_content = ["#EXTM3U"]
    
    possible_paths = ['iptv.json', 'app/iptv.json']
    config_path = None
    for p in possible_paths:
        if os.path.exists(p):
            config_path = p
            break
            
    if not config_path:
        return "Config file not found", 500

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        return f"JSON Config Error: {e}", 500

    for item in config.get('lives', []):
        name = item.get('name')
        api_path = item.get('api')
        if api_path.startswith('file://'):
            clean_path = api_path.replace('file://', '')
        else:
            clean_path = api_path

        if not os.path.isabs(clean_path):
            real_path = os.path.join(os.getcwd(), clean_path)
        else:
            real_path = clean_path

        logger.info(f"Task: {name}")
        
        SpiderClass = load_spider_class(real_path)
        if SpiderClass:
            try:
                spider = SpiderClass()
                spider.init(json.dumps(item.get('ext', {})))
                content = spider.liveContent(None)
                if content:
                    lines = content.split('\n')
                    valid_lines = [l for l in lines if l.strip() and '#EXTM3U' not in l]
                    m3u_content.extend(valid_lines)
            except Exception as e:
                logger.error(f"Error in {name}: {e}")
                # 在 M3U 里保留错误信息，但 debug 页面能看到更多
                m3u_content.append(f"# 错误: {name} 运行失败")

    return Response('\n'.join(m3u_content), mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
