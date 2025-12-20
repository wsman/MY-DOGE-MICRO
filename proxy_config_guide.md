# 代理配置指南

## 概述

本指南介绍如何配置 MY-DOGE QUANT SYSTEM 通过 VPN 代理访问雅虎财经接口。系统使用 `yfinance` 库获取金融数据，现已支持代理配置。

## 配置步骤

### 1. 复制配置文件模板

如果您还没有配置文件，请先复制模板：

```bash
cp models_config.template.json models_config.json
```

### 2. 编辑配置文件

打开 `models_config.json` 文件，找到 `proxy_settings` 部分：

```json
"proxy_settings": {
    "enabled": false,
    "url": "http://127.0.0.1:7890"
}
```

修改为您的代理设置：

- **enabled**: 设置为 `true` 启用代理
- **url**: 设置代理服务器地址，格式为：
  - HTTP 代理: `http://127.0.0.1:7890`
  - SOCKS5 代理: `socks5://127.0.0.1:7890`
  - 需要认证的代理: `http://用户名:密码@代理地址:端口`

### 3. 示例配置

#### 示例 1: 启用 HTTP 代理（端口 7890）
```json
"proxy_settings": {
    "enabled": true,
    "url": "http://127.0.0.1:7890"
}
```

#### 示例 2: 启用 SOCKS5 代理
```json
"proxy_settings": {
    "enabled": true,
    "url": "socks5://127.0.0.1:7890"
}
```

#### 示例 3: 带认证的代理
```json
"proxy_settings": {
    "enabled": true,
    "url": "http://user:password@proxy.example.com:8080"
}
```

### 4. 验证配置

运行测试脚本验证代理配置：

```bash
python test_proxy_config.py
```

如果看到 "数据获取成功" 消息，说明代理配置正确。

## 故障排除

### 1. 代理连接失败

**症状**: 数据获取失败，网络超时

**解决方案**:
1. 确认代理服务器正在运行
2. 检查代理地址和端口是否正确
3. 尝试在浏览器或其他应用中测试代理连接
4. 检查防火墙设置

### 2. 代理认证失败

**症状**: 连接被拒绝，认证错误

**解决方案**:
1. 确认用户名和密码正确
2. 检查代理服务器是否支持匿名访问
3. 尝试使用不带认证的代理地址测试

### 3. 数据获取缓慢

**症状**: 数据下载速度很慢

**解决方案**:
1. 检查代理服务器的网络连接
2. 尝试不同的代理服务器
3. 考虑禁用代理测试直接连接

## 高级配置

### 环境变量覆盖

除了配置文件，您还可以通过环境变量临时覆盖代理设置：

```bash
# Windows PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

# 然后运行系统
python src/interface/dashboard.py
```

### 程序化配置

在代码中直接配置代理：

```python
from src.macro.config import MacroConfig

config = MacroConfig()
config.proxy_enabled = True
config.proxy_url = "http://127.0.0.1:7890"
```

## 注意事项

1. **安全性**: 不要在配置文件中硬编码敏感密码，考虑使用环境变量
2. **性能**: 代理会增加网络延迟，可能影响数据获取速度
3. **兼容性**: 确保代理服务器支持 HTTPS 连接
4. **日志**: 启用详细日志可以查看代理连接状态

## 技术支持

如果遇到问题，请检查：
- 系统日志文件
- 网络连接状态
- 代理服务器配置

如需进一步帮助，请参考项目文档或提交 Issue。
