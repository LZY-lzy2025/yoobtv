import sys
import os
import json
import importlib.util
import logging
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
        # 路径防御：确保路径是绝对路径
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
            logger.info(f"成功加载 Spider 类: {module_name}")
            return module.Spider
        else:
            logger.error(f"模块中未找到 Spider 类: {module_name}")
            return None
    except Exception as e:
        logger.exception(f"加载模块异常 {filepath}: {e}")
        return None

# 健康检查接口
@app.route('/')
def health_check():
    return "IPTV Service OK (Port 5000)", 200

@app.route('/iptv.m3u')
def get_m3u():
    m3u_content = ["#EXTM3U"]
    
    # 尝试多种路径寻找 json
    possible_paths = ['iptv.json', 'app/iptv.json']
    config_path = None
    for p in possible_paths:
        if os.path.exists(p):
            config_path = p
            break
            
    if not config_path:
        logger.error("找不到 iptv.json")
        return "Config file not found", 500

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        return f"JSON Config Error: {e}", 500

    for item in config.get('lives', []):
        name = item.get('name')
        api_path = item.get('api')
        
        # 处理 file:// 前缀
        if api_path.startswith('file://'):
            clean_path = api_path.replace('file://', '')
        else:
            clean_path = api_path

        # 路径修正逻辑
        # Docker 中 WORKDIR 是 /app
        # 如果 json 写的是 Download/kzb.py，那么完整路径应该是 /app/Download/kzb.py
        if not os.path.isabs(clean_path):
            real_path = os.path.join(os.getcwd(), clean_path)
        else:
            real_path = clean_path

        logger.info(f"开始任务: {name} | 路径: {real_path}")
        
        SpiderClass = load_spider_class(real_path)
        if SpiderClass:
            try:
                spider = SpiderClass()
                ext_str = json.dumps(item.get('ext', {}))
                spider.init(ext_str)
                
                content = spider.liveContent(None)
                
                if content:
                    lines = content.split('\n')
                    # 过滤空行和重复头
                    valid_lines = [l for l in lines if l.strip() and '#EXTM3U' not in l]
                    m3u_content.extend(valid_lines)
                    logger.info(f"任务完成: {name} - 获取到 {len(valid_lines)//2} 个频道")
                else:
                    logger.warning(f"任务返回空: {name}")

            except Exception as e:
                logger.error(f"运行时错误 {name}: {e}")
        else:
            logger.error(f"跳过任务 {name}: 类加载失败")

    return Response('\n'.join(m3u_content), mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    # 本地测试用的启动代码，Docker 中不会走到这里
    app.run(host='0.0.0.0', port=5000)
