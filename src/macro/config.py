import os
import json
import sys
from dataclasses import dataclass
from typing import Optional

@dataclass
class MacroConfig:
    """
    宏观策略配置类 (JSON 驱动版 - 最终修正)
    """
    # 资产配置 (默认为空，由 load_config 填充)
    tech_proxy: str = "QQQ"
    tech_name: str = "科技股(纳指)"
    
    safe_haven_proxy: str = "GLD"
    safe_name: str = "避险黄金"
    
    crypto_proxy: str = "BTC-USD"
    crypto_name: str = "数字货币"
    
    target_asset: str = "000300.SS"
    target_name: str = "A股核心(沪深300)"
    
    # 参数配置
    lookback_days: int = 120
    volatility_window: int = 20

    # API 配置
    api_key: Optional[str] = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"

    def __post_init__(self):
        """初始化时加载 JSON 配置"""
        self._load_from_json()
        self._apply_runtime_overrides()

    def _load_from_json(self):
        # 智能定位 JSON 文件 (向上寻找项目根目录)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # src/macro -> src -> project_root
        project_root = os.path.dirname(os.path.dirname(current_dir))
        json_path = os.path.join(project_root, 'models_config.json')
        
        if not os.path.exists(json_path):
            print(f"⚠️ [MacroConfig] 配置文件未找到: {json_path}，将使用默认值")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 1. 加载资产 (Assets)
            assets = data.get('assets', {})
            if 'tech' in assets:
                self.tech_proxy = assets['tech']['symbol']
                self.tech_name = assets['tech']['name']
            if 'safe' in assets:
                self.safe_haven_proxy = assets['safe']['symbol']
                self.safe_name = assets['safe']['name']
            if 'crypto' in assets:
                self.crypto_proxy = assets['crypto']['symbol']
                self.crypto_name = assets['crypto']['name']
            if 'target' in assets:
                self.target_asset = assets['target']['symbol']
                self.target_name = assets['target']['name']

            # 2. 加载参数 (Settings)
            settings = data.get('macro_settings', {})
            self.lookback_days = settings.get('lookback_days', 120)
            self.volatility_window = settings.get('volatility_window', 20)

            # 3. 加载默认 Profile
            default_profile_name = data.get('default_profile')
            profiles = data.get('profiles', [])
            target_profile = next((p for p in profiles if p['name'] == default_profile_name), None)
            
            if target_profile:
                self.api_key = target_profile.get('api_key')
                self.base_url = target_profile.get('base_url')
                self.model = target_profile.get('model')

        except Exception as e:
            print(f"❌ [MacroConfig] 读取配置文件出错: {e}")

    def _apply_runtime_overrides(self):
        """
        应用运行时环境变量覆盖 (兼容 GUI 切换模型)
        注意：这里的 env 是 GUI 临时设置的内存变量，不是 .env 文件
        """
        env_api_key = os.getenv("DEEPSEEK_API_KEY")
        if env_api_key: self.api_key = env_api_key
        
        env_model = os.getenv("DEEPSEEK_MODEL")
        if env_model: self.model = env_model
        
        if not self.api_key:
            # 仅作为警告，不阻断初始化 (可能在 GUI 中稍后设置)
            print("⚠️ [MacroConfig] Warning: API Key is not set.")
