[English](README.md) | 简体中文 | [繁體中文](README.zh-TW.md)

# Windows AI Dev Doctor

用证据、审慎的判断和明确的安全操作，解释 Windows 开发者工具问题。

**v0.1.0 · 便携式 Windows x64 CLI**

本项目旨在帮助回答“为什么我的 AI/开发者工具无法在 Windows 上运行？”它绝不会
仅凭存在代理、安装了多个版本或端口被占用，就断言发生了故障。

## 当前可用功能

显式注册的检查项共有 36 项：

| 类别 | 覆盖范围 |
| --- | --- |
| 系统（9） | Windows 版本/内部版本、PowerShell、Terminal、权限、磁盘、重要目录、WebView2、GPU、相关进程 |
| 开发者工具（12） | Git 版本/配置/仓库、GitHub CLI/身份验证、Python/启动器/pip、Node/npm/npx、版本管理器 |
| AI 应用（3） | ChatGPT Desktop 探测、Codex CLI 版本、Codex 配置/缓存元数据 |
| 环境（3） | PATH 结构、选定的开发者路径、可执行文件遮蔽 |
| 网络（9） | 环境/系统/WinHTTP 代理、适配器/路由、监听端口、代理层关联、DNS/TCP/HTTPS |

目前已实现 CLI、单项检查失败隔离、严格的 TOML 配置、强制脱敏、需主动启用的本地
JSON/HTML 报告与日志，以及需要确认的配置备份框架。
运行时没有 Python 包依赖。应用探测采用尽力而为的方式：
不会解析专有状态，对不确定或不支持的观察结果标记为 INFO/SKIPPED。

输出示例（仅供说明，并非对你的计算机进行测量）：

```text
Windows AI Dev Doctor 0.1.0

System
  [PASS] Windows system: Windows 11 platform detected
Developer Tools
  [PASS] Git version: Git 2.49.0.windows.1 is executable
AI Applications
  [INFO] ChatGPT Desktop: ChatGPT indicators were found
Environment
  [WARNING] PATH structure: 2 PATH findings
Network
  [INFO] Proxy environment: Proxy environment detected
  [SKIPPED] DNS connectivity: Network probe requires --network consent
  [SKIPPED] TCP connectivity: Network probe requires --network consent
  [SKIPPED] HTTPS connectivity: Network probe requires --network consent
```

## 安装

如需进行开发，请在 Windows 10/11 上使用 Python 3.12+：

```powershell
git clone https://github.com/petically/windows-ai-dev-doctor.git
cd windows-ai-dev-doctor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\ai-dev-doctor.exe help
```

从 [v0.1.0 release](https://github.com/petically/windows-ai-dev-doctor/releases/tag/v0.1.0)
下载 **便携式 Windows x64 ZIP** 和 `SHA256SUMS.txt`。
使用 `Get-FileHash .\ai-dev-doctor-0.1.0-windows-x64.zip -Algorithm SHA256` 比对其哈希值。
压缩包中包含可执行文件及其捆绑的运行时。请解压整个文件夹并运行 `ai-dev-doctor.exe`；无需安装
Python。请将 `_internal` 文件夹与可执行文件放在一起。便携包未签名；Windows SmartScreen/信誉警告可能会出现。
本项目不提供安装程序。请验证下载来源和已发布的校验和；不要禁用
Windows 安全控制。[CI 构件](https://github.com/petically/windows-ai-dev-doctor/actions)
可能需要登录 GitHub 才能下载。

采用 onedir 打包是有意的选择：它启动快，也不会产生 onefile 运行时解压写入。
不要只将可执行文件从便携包中单独复制出来。

## 使用方法

激活环境后（或在解压后的可执行文件目录中）运行：

```powershell
ai-dev-doctor diagnose
ai-dev-doctor doctor
ai-dev-doctor diagnose --verbose
ai-dev-doctor diagnose --json
ai-dev-doctor diagnose --category ai-applications
ai-dev-doctor diagnose --category network
ai-dev-doctor diagnose --network
ai-dev-doctor explain git-repository
ai-dev-doctor report --output doctor-report.json
ai-dev-doctor report --output doctor-report.html
ai-dev-doctor diagnose --log-file local-events.jsonl
ai-dev-doctor fix --dry-run backup-config
ai-dev-doctor fix backup-config
ai-dev-doctor version
```

每次调用时，网络探测都需要传入 `--network`，生成报告时也不例外。它们会直接查询
`example.com` 和 `www.python.org`，不使用代理凭据，也不跟随重定向。
直接探测并不能验证已配置的代理路由。未知参数/配置选项会被视为错误。退出码：**0** 表示没有 FAIL/ERROR，
**1** 表示诊断出现 FAIL/ERROR，**2** 表示调用、配置、导出或修复失败；取消操作返回 **130**。

终端输出使用 ASCII 状态标签，可选 TTY 颜色，并遵循 `NO_COLOR`。
JSON 标准输出是单个文档；错误写入标准错误。

## 配置

可选的默认配置文件：`%USERPROFILE%\.ai-dev-doctor\config.toml`。不会自动创建任何内容。
可以通过 `diagnose --config path.toml` 传入自定义配置（report 同样支持）。
示例：

```toml
network_timeout = 4.0
command_timeout = 4.0
enabled_categories = ["system", "developer-tools", "ai-applications", "environment", "network"]
disabled_checks = []
verbose = false
```

每条命令或每个网络目标的超时时间必须为 0.1–30 秒。配置大小上限为 64 KiB。
无法通过配置禁用/启用网络同意和脱敏。未知的检查 ID
和选项会被拒绝，而不会被静默忽略。

## 安全与隐私

- 默认情况下，诊断只检查状态，不会编辑配置或写入日志。
- 不包含遥测、分析或上传。报告和日志保留在本地。
- 出站探测需要明确许可；常规 DNS/IP 元数据会在网络上可见。
- 输出边界会移除敏感信息。尽量减少数据收集；不会转储身份验证/配置内容。
- Git 配置检查仅报告选定键是否存在；仓库检查只报告数量，
  不会报告身份、分支、远程仓库或文件名。Git 状态检查会禁用可选的索引
  更新、fsmonitor hook 和子模块遍历。
- ChatGPT/Codex 缓存检查仅限有边界的元数据：目录/文件数量和汇总大小。
  它绝不会读取缓存或配置内容，也不提供缓存删除功能。
- 不会遍历远程/重解析的 PATH 位置，以防意外访问共享目录。
- 命令使用经过审查的允许列表、明确的可执行文件路径、有边界的输出/期限，
  不使用 shell 或 stdin，并采用最小化环境。Windows 子进程树会被原子地分配给自有 Job Object，
  并在完成、超时或取消时清理。仍需信任已安装的可执行文件。
- 报告/日志文件需要明确指定路径，而且绝不会覆盖现有文件。
- 唯一的修复操作是备份**本工具自身现有且有效的配置**。它会预览
  源文件、备份文件和审计文件，默认为 NO，需要交互式输入 `yes`，会重新检查输入，
  拒绝重解析点/符号链接路径，并记录操作意图/结果。试运行不会创建任何内容。
- 原始配置会保留。若后续手动编辑后需要恢复，请检查备份并
  手动将其内容复制回去；本工具不会静默覆盖配置。

脱敏是一种纵深防御，并不能证明任意文本中绝无敏感信息。分享前请检查
导出内容。参阅 [SECURITY.md](SECURITY.md) 和 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 报告

JSON schema 版本 `1` 包含 UTC 时间戳、应用版本、系统元数据、状态计数
和结构化结果。HTML 是自包含、已转义、响应式且可离线使用的。
不含脚本、外部资源，也不会自动启动浏览器。若目标文件已存在，操作会被拒绝。

## 开发与验证

在可用的情况下，Windows 适配器会使用结构化 Win32 API 和有文档说明的注册表位置。
在非 Windows 主机上，特定于平台的检查会返回 SKIPPED，使测试和报告流水线保持
可移植性，同时不会假装已经测量过 Windows 状态。

已知限制：

- GitHub 身份验证和固定目标连通性需要 `--network`；直接探测并不能
  证明已配置的代理能够工作。
- 已安装的可执行文件和内置插件被视为可信；命令期限并不是沙箱。
- 随着未来布局变化，对 Store/包管理应用的探测可能不完整。
- 便携包未签名。本地 Windows 11 验证并不能证明在全新 Windows 10/11、
  Store 布局、ARM64 或企业策略环境中的兼容性；参阅[验证证据](RELEASE_READINESS.md)。
- 监听端口关联和参考路由证据仅支持 IPv4。IPv6/localhost 名称
  代理和自动代理发现仍未经验证。
- Git 身份检查仅检查全局键是否存在；不会验证本地身份和值。
  身份验证探测测试已存储的 GitHub 账户，不包括环境变量中的 token。

```powershell
python -m pip install -e ".[dev,build]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
python scripts/scan_source.py
python -m build
python -m PyInstaller --clean --noconfirm ai-dev-doctor.spec
python scripts/smoke_package.py dist/ai-dev-doctor/ai-dev-doctor.exe
```

请使用虚拟环境中的 Python。测试使用虚假的系统/网络状态和受控的
子进程。Windows Server 2022/2025 和 Linux CI 会测试 Python 3.12/3.13；Windows 还会构建并
冒烟测试独立便携包。本地文件系统探测依赖操作系统的响应能力；
这不是针对恶意插件、可执行文件或并发本地攻击者的沙箱。

## 贡献与许可证

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)、[AGENTS.md](AGENTS.md)、
[产品规范](SPEC.md)和[架构文档](ARCHITECTURE.md)。
社区行为准则参见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
本项目采用 MIT 许可证；参见 [LICENSE](LICENSE)。

已实现的诊断和配置备份功能如上所列。应用探测、
GPU 注册表证据以及代理/隧道分类均采用**尽力而为**的方式。缓存修复、
专有应用状态诊断、签名和安装程序均为**规划中**，尚未
实现。缺少可选软件只属于信息性提示；无法访问的状态不能证明存在
故障。命令 stdout/stderr 不会作为报告附件。重定向的 CLI 输出采用 UTF-8。
