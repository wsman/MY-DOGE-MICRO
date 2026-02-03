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

    # 代理配置
    proxy_url: Optional[str] = None
    proxy_enabled: bool = False

    def __post_init__(self):
        """初始化时加载 JSON 配置"""
        self._load_from_json()
        self._apply_runtime_overrides()
        
    def _validate_config(self, config_data):
        """
        验证配置文件结构完整性
        
        Args:
            config_data (dict): 加载的 JSON 配置数据
            
        Raises:
            ValueError: 如果配置缺少必要字段或格式错误
        """
        # 检查顶级必需字段
        required_top_fields = ['profiles', 'default_profile', 'assets']
        for field in required_top_fields:
            if field not in config_data:
                raise ValueError(f"配置缺少必要顶级字段: {field}")
        
        # 检查 profiles 数组
        profiles = config_data.get('profiles', [])
        if not isinstance(profiles, list):
            raise ValueError("profiles 必须是一个数组")
        
        if len(profiles) == 0:
            raise ValueError("profiles 数组不能为空")
        
        # 检查每个 profile 的必要字段
        required_profile_fields = ['name', 'base_url', 'model', 'api_key']
        for i, profile in enumerate(profiles):
            for field in required_profile_fields:
                if field not in profile:
                    raise ValueError(f"profile {i} ({profile.get('name', '未命名')}) 缺少字段: {field}")
        
        # 检查 default_profile 是否在 profiles 中
        default_profile_name = config_data.get('default_profile')
        if default_profile_name not in [p.get('name') for p in profiles]:
            raise ValueError(f"default_profile '{default_profile_name}' 不在 profiles 列表中")
        
        # 检查 assets 结构
        assets = config_data.get('assets', {})
        required_assets = ['tech', 'safe', 'crypto', 'target']
        for asset_key in required_assets:
            if asset_key not in assets:
                raise ValueError(f"assets 中缺少资产: {asset_key}")
            
            asset = assets[asset_key]
            if 'symbol' not in asset or 'name' not in asset:
                raise ValueError(f"资产 {asset_key} 缺少 symbol 或 name 字段")
        
        # 检查 macro_settings
        macro_settings = config_data.get('macro_settings', {})
        if 'lookback_days' not in macro_settings or 'volatility_window' not in macro_settings:
            raise ValueError("macro_settings 中缺少 lookback_days 或 volatility_window")
        
        # 检查 proxy_settings
        proxy_settings = config_data.get('proxy_settings', {})
        if 'enabled' not in proxy_settings:
            raise ValueError("proxy_settings 中缺少 enabled 字段")

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
            
            # 验证配置文件结构
            self._validate_config(data)
            
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

            # 4. 加载代理配置
            proxy_settings = data.get('proxy_settings', {})
            self.proxy_enabled = proxy_settings.get('enabled', False)
            self.proxy_url = proxy_settings.get('url')

            print(f"✅ [MacroConfig] 配置文件加载成功: {json_path}")

        except json.JSONDecodeError as e:
            print(f"❌ [MacroConfig] JSON 格式错误: {e}")
            print(f"   请检查 {json_path} 文件的 JSON 语法")
        except ValueError as e:
            print(f"❌ [MacroConfig] 配置验证失败: {e}")
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
