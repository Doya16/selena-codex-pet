param([switch]$NoLaunch, [switch]$NoStartMenu)
# 赛琳娜 Codex 桌宠 · 一键部署（完整包首次使用）
# 检查解压位置与文件、创建桌面和开始菜单快捷方式，然后启动桌宠。可重复运行。
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
function Say([string]$text, [string]$color = 'Gray') { Write-Host $text -ForegroundColor $color }
function Fail([string]$text) { Say ''; Say "部署没有完成：$text" 'Red'; exit 1 }

Say '赛琳娜 Codex 桌宠 · 一键部署' 'Magenta'
Say "位置：$root"

# 1. 必须是完整解压后的目录，而不是压缩软件的临时目录
$temp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')
if ($root.StartsWith($temp, [StringComparison]::OrdinalIgnoreCase) -or $root -match '\\(Rar\$|7z[A-Z0-9]+|Temp\d+_)') {
    Fail '看起来是在压缩包里直接运行的。请先把整个 ZIP 解压到一个文件夹（例如 D:\赛琳娜Codex桌宠），再双击里面的「一键部署.cmd」。'
}

# 2. 关键文件
$exe = Get-ChildItem -LiteralPath $root -Filter *.exe | Where-Object { $_.VersionInfo.InternalName -eq 'selena_pet' } | Select-Object -First 1
if (-not $exe) { Fail '没有找到 赛琳娜Codex桌宠启动.exe。请重新下载完整包并完整解压。' }
$current = Join-Path $root 'current-program.json'
if (-not (Test-Path -LiteralPath $current)) { Fail '缺少 current-program.json，完整包可能没有解压完整。' }
$version = (Get-Content -LiteralPath $current -Raw -Encoding UTF8 | ConvertFrom-Json).version
$program = Join-Path $root ".programs\$version\$($exe.Name)"
foreach ($need in @($program, (Join-Path $root 'assets\catalog.json'), (Join-Path $root 'defaults\settings.json'), (Join-Path $root 'tools\create_shortcut.ps1'))) {
    if (-not (Test-Path -LiteralPath $need)) { Fail "缺少文件：$need。请重新完整解压。" }
}
Say "版本：v$version" 'Green'

# 3. 目录需要可写（保存设置、一键更新都要写入这里）
try {
    $probe = Join-Path $root ('.deploy-check-' + [guid]::NewGuid().ToString('N'))
    [IO.File]::WriteAllText($probe, 'ok'); Remove-Item -LiteralPath $probe -Force
} catch { Fail '这个文件夹不能写入（例如 C:\Program Files）。请换到自己的文件夹，例如 D:\赛琳娜Codex桌宠。' }

# 4. Codex 客户端（只提醒，不阻止）
$codex = Test-Path -LiteralPath (Join-Path $env:LOCALAPPDATA 'OpenAI\Codex')
if ($codex) { Say '已找到 Codex 客户端。' 'Green' } else { Say '提示：没有找到 Codex 客户端。桌宠可以先运行，安装并登录 Codex 后会自动跟随任务。' 'Yellow' }

# 5. 快捷方式
$maker = Join-Path $PSScriptRoot 'create_shortcut.ps1'
$desktop = [Environment]::GetFolderPath('Desktop')
& $maker -Destination $desktop -Target $exe.FullName | Out-Null
Say "已创建桌面快捷方式：$($exe.BaseName)" 'Green'
if (-not $NoStartMenu) {
    $menu = [Environment]::GetFolderPath('Programs')
    if ($menu -and (Test-Path -LiteralPath $menu)) {
        & $maker -Destination $menu -Target $exe.FullName | Out-Null
        Say '已添加到开始菜单。' 'Green'
    }
}

# 6. 启动
if (-not $NoLaunch) {
    $running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase) -and $_.ProcessName -like '赛琳娜*' }
    if ($running) { Say '赛琳娜已经在运行了。' 'Green' }
    else { Start-Process -FilePath $exe.FullName -WorkingDirectory $root; Say '正在启动赛琳娜……' 'Green' }
}
Say ''
Say '部署完成。之后从桌面快捷方式启动；有新版本时，桌宠会提示一键更新。' 'Magenta'
