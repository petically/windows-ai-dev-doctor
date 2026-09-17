[English](README.md) | [简体中文](README.zh-CN.md) | 繁體中文

# Windows AI Dev Doctor

以證據、審慎的判定和明確的安全操作，解釋 Windows 開發者工具問題。

**v0.1.0 · 可攜式 Windows x64 CLI**

本專案旨在協助回答「為什麼我的 AI/開發者工具無法在 Windows 上運作？」它絕不會
只因存在 Proxy、安裝了多個版本或連接埠被占用，就斷言發生故障。

## 目前可用功能

明確註冊的檢查項目共有 36 項：

| 類別 | 涵蓋範圍 |
| --- | --- |
| 系統（9） | Windows 版本/組建、PowerShell、Terminal、權限、磁碟、重要目錄、WebView2、GPU、相關處理程序 |
| 開發者工具（12） | Git 版本/設定/儲存庫、GitHub CLI/驗證、Python/啟動器/pip、Node/npm/npx、版本管理器 |
| AI 應用程式（3） | ChatGPT Desktop 偵測、Codex CLI 版本、Codex 設定/快取中繼資料 |
| 環境（3） | PATH 結構、選定的開發者路徑、可執行檔遮蔽 |
| 網路（9） | 環境/系統/WinHTTP Proxy、介面卡/路由、監聽連接埠、Proxy 層關聯、DNS/TCP/HTTPS |

目前已實作 CLI、單項檢查失敗隔離、嚴格的 TOML 設定、強制遮蔽敏感資訊、需主動啟用的本機
JSON/HTML 報告與記錄，以及需要確認的設定備份框架。
執行階段沒有 Python 套件相依性。應用程式偵測採取盡力而為的方式：
不會剖析專有狀態，對不確定或不支援的觀察結果會標示為 INFO/SKIPPED。

輸出範例（僅供說明，並非對你的電腦進行量測）：

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

## 安裝

若要進行開發，請在 Windows 10/11 上使用 Python 3.12+：

```powershell
git clone https://github.com/petically/windows-ai-dev-doctor.git
cd windows-ai-dev-doctor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\ai-dev-doctor.exe help
```

請從 [v0.1.0 release](https://github.com/petically/windows-ai-dev-doctor/releases/tag/v0.1.0)
下載 **可攜式 Windows x64 ZIP** 和 `SHA256SUMS.txt`。
使用 `Get-FileHash .\ai-dev-doctor-0.1.0-windows-x64.zip -Algorithm SHA256` 比對其雜湊值。
壓縮檔內含可執行檔及其隨附的執行階段。請解壓縮整個資料夾並執行 `ai-dev-doctor.exe`；不需要安裝
Python。請將 `_internal` 資料夾與可執行檔放在一起。可攜式套件未簽署；Windows SmartScreen/信譽警告可能會出現。
本專案不提供安裝程式。請驗證下載來源及已發布的檢查碼；不要停用
Windows 安全性控制。[CI 成品](https://github.com/petically/windows-ai-dev-doctor/actions)
可能需要登入 GitHub 才能下載。

採用 onedir 封裝是刻意的選擇：它啟動快速，也不會產生 onefile 執行階段解壓縮寫入。
不要只將可執行檔從套件中單獨複製出來。

## 使用方式

啟用環境後（或在解壓縮後的可執行檔目錄中）執行：

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

每次呼叫時，網路探測都需要傳入 `--network`，產生報告時也不例外。它們會直接查詢
`example.com` 和 `www.python.org`，不使用 Proxy 認證資訊，也不跟隨重新導向。
直接探測無法驗證已設定的 Proxy 路由。未知的引數/設定選項會被視為錯誤。結束代碼：**0** 表示沒有 FAIL/ERROR，
**1** 表示診斷出現 FAIL/ERROR，**2** 表示呼叫、設定、匯出或修復失敗；取消操作會傳回 **130**。

終端機輸出使用 ASCII 狀態標籤、可選的 TTY 色彩，並遵循 `NO_COLOR`。
JSON 標準輸出是單一文件；錯誤會寫入標準錯誤。

## 設定

選用的預設設定檔：`%USERPROFILE%\.ai-dev-doctor\config.toml`。不會自動建立任何內容。
可以透過 `diagnose --config path.toml` 傳入自訂設定（report 同樣支援）。
範例：

```toml
network_timeout = 4.0
command_timeout = 4.0
enabled_categories = ["system", "developer-tools", "ai-applications", "environment", "network"]
disabled_checks = []
verbose = false
```

每個命令或每個網路目標的逾時時間必須為 0.1–30 秒。設定大小上限為 64 KiB。
無法透過設定停用/啟用網路同意和敏感資訊遮蔽。未知的檢查 ID
和選項會被拒絕，而不會被靜默忽略。

## 安全性與隱私

- 預設情況下，診斷只檢查狀態，不會編輯設定或寫入記錄。
- 不包含遙測、分析或上傳。報告和記錄保留在本機。
- 對外探測需要明確同意；一般 DNS/IP 中繼資料會在網路上可見。
- 輸出邊界會移除機密資訊。盡可能減少資料收集；不會傾印驗證/設定內容。
- Git 設定檢查只報告選定的索引鍵是否存在；儲存庫檢查只報告數量，
  絕不會報告身分、分支、遠端儲存庫或檔案名稱。Git 狀態檢查會停用選用的索引
  更新、fsmonitor hook 和子模組走訪。
- ChatGPT/Codex 快取檢查僅限有邊界的中繼資料：目錄/檔案數量和彙總大小。
  它絕不會讀取快取或設定內容，也不提供刪除快取的功能。
- 不會走訪遠端/重新剖析的 PATH 位置，以防意外存取共用位置。
- 命令使用經過審查的允許清單、明確的可執行檔路徑、有邊界的輸出/期限，
  不使用 shell 或 stdin，並採用最小化環境。Windows 子處理程序樹會以不可分割的方式指派給自有 Job Object，
  並在完成、逾時或取消時清理。仍須信任已安裝的可執行檔。
- 報告/記錄檔需要明確指定路徑，而且絕不會覆寫現有檔案。
- 唯一的修復操作是備份**本工具本身現有且有效的設定**。它會預覽
  來源檔、備份檔和稽核檔，預設為 NO，需要以互動方式輸入 `yes`，會重新檢查輸入，
  拒絕重新剖析點/符號連結路徑，並記錄操作意圖/結果。試執行不會建立任何內容。
- 原始設定會保留。若之後手動編輯後需要還原，請檢查備份並
  手動將其內容複製回去；本工具不會靜默覆寫設定。

敏感資訊遮蔽是一種縱深防禦，並不能證明任意文字中絕無機密資訊。分享前請檢查
匯出內容。請參閱 [SECURITY.md](SECURITY.md) 和 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 報告

JSON schema 版本 `1` 包含 UTC 時間戳記、應用程式版本、系統中繼資料、狀態計數
和結構化結果。HTML 是自包含、已逸出、回應式且可離線使用的。
不含指令碼、外部資產，也不會自動啟動瀏覽器。若目的檔案已存在，操作會被拒絕。

## 開發與驗證

在可用的情況下，Windows 介面卡會使用結構化 Win32 API 和有文件記載的登錄位置。
在非 Windows 主機上，平台專屬檢查會傳回 SKIPPED，使測試和報告管線保持
可攜性，同時不會假裝已量測過 Windows 狀態。

已知限制：

- GitHub 驗證和固定目標連線能力需要 `--network`；直接探測並不能
  證明已設定的 Proxy 能夠運作。
- 已安裝的可執行檔和內建外掛程式被視為可信；命令期限並不是沙箱。
- 隨著未來版面配置變更，對 Store/套件管理應用程式的偵測可能不完整。
- 套件未簽署。本機 Windows 11 驗證並不能證明在全新 Windows 10/11、
  Store 版面配置、ARM64 或企業原則環境中的相容性；請參閱[驗證證據](RELEASE_READINESS.md)。
- 監聽連接埠關聯和參考路由證據僅支援 IPv4。IPv6/localhost 名稱
  Proxy 和自動 Proxy 探索仍未驗證。
- Git 身分檢查只檢查全域索引鍵是否存在；不會驗證本機身分和值。
  驗證探測測試已儲存的 GitHub 帳戶，不包括環境變數中的 token。

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

請使用虛擬環境中的 Python。測試使用模擬的系統/網路狀態和受控的
子處理程序。Windows Server 2022/2025 和 Linux CI 會測試 Python 3.12/3.13；Windows 還會建置並
進行獨立套件的冒煙測試。本機檔案系統探測依賴作業系統的回應能力；
這不是針對惡意外掛程式、可執行檔或同時存在的本機攻擊者的沙箱。

## 貢獻與授權

請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)、[AGENTS.md](AGENTS.md)、
[產品規格](SPEC.md)和[架構文件](ARCHITECTURE.md)。
社群行為準則請見 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
本專案採用 MIT 授權；請參閱 [LICENSE](LICENSE)。

已實作的診斷和設定備份功能如上所列。應用程式偵測、
GPU 登錄證據以及 Proxy/通道分類皆採用**盡力而為**的方式。快取修復、
專有應用程式狀態診斷、簽署和安裝程式均為**規劃中**，尚未
實作。缺少選用軟體只屬於資訊性提示；無法存取的狀態不能證明存在
故障。命令 stdout/stderr 不會成為報告附件。重新導向的 CLI 輸出採用 UTF-8。
