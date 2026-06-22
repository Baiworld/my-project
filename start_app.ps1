<#
.SYNOPSIS
  Windows 端一键启动 — Spark Streaming + Flask + Vue
.DESCRIPTION
  前提: 虚拟机上已运行 start_pipeline.sh (Flume + 数据生成)
  用法: .\start_app.ps1           # 启动全部
        .\start_app.ps1 -Stop     # 停止全部
#>

param([switch]$Stop)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step($msg) {
    Write-Host "[STEP] $msg" -ForegroundColor Blue
}
function Write-OK($msg) {
    Write-Host "[OK]   $msg" -ForegroundColor Green
}

if ($Stop) {
    Write-Step "停止所有服务..."
    Get-Process -Name "java" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*RealTimeAnalysis*" } | Stop-Process -Force
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" } | Stop-Process -Force
    Write-OK "所有服务已停止"
    exit 0
}

Write-Host ""
Write-Host "=============================================="
Write-Host "  基于 Spark 大数据的用户行为实时分析与混合推荐系统 — Windows 端一键启动"
Write-Host "=============================================="
Write-Host ""

# ── 1. Spark Streaming ──
Write-Step "启动 Spark Streaming..."
$sparkJar = Join-Path $Root "spark-streaming\target\spark-streaming-1.0-shaded.jar"
if (-not (Test-Path $sparkJar)) {
    Write-Host "  Jar 不存在，正在编译..."
    & "E:\apache-maven-3.9.6\bin\mvn.cmd" package -pl spark-streaming -DskipTests 2>&1 | Select-Object -Last 3
}
Remove-Item -Recurse -Force "$Root\checkpoints\streaming-v2" -ErrorAction SilentlyContinue
$sparkJob = Start-Job -Name "SparkStreaming" -ScriptBlock {
    Set-Location $using:Root
    spark-submit --class com.recommend.streaming.RealTimeAnalysisApp --master local[2] spark-streaming/target/spark-streaming-1.0-shaded.jar 2>&1 | Out-Null
}
Write-OK "Spark Streaming 已启动 (Job ID: $($sparkJob.Id))"

# ── 2. Flask ──
Write-Step "启动 Flask 后端..."
$flaskJob = Start-Job -Name "FlaskBackend" -ScriptBlock {
    Set-Location "$using:Root\flask-backend"
    python run.py
}
Start-Sleep -Seconds 4
try {
    $null = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -UseBasicParsing -TimeoutSec 3
    Write-OK "Flask :5000 已就绪"
} catch {
    Write-Host "  Flask 启动中，请稍候..." -ForegroundColor Yellow
}

# ── 3. Vue ──
Write-Step "启动 Vue 前端..."
$vueJob = Start-Job -Name "VueFrontend" -ScriptBlock {
    Set-Location "$using:Root\vue-frontend"
    npm run dev
}
Start-Sleep -Seconds 3
Write-OK "Vue :5173 已启动"

Write-Host ""
Write-Host "=============================================="
Write-Host "  全部启动完成！"
Write-Host "  前端: http://localhost:5173/dashboard"
Write-Host "  API:  http://localhost:5000/api/health"
Write-Host "  停止: .\start_app.ps1 -Stop"
Write-Host "=============================================="
Write-Host ""

# 前台等待
try {
    while ($true) {
        Start-Sleep -Seconds 10
        $sparkAlive = Get-Job -Name "SparkStreaming" -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        $flaskAlive = Get-Job -Name "FlaskBackend" -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" }
        if (-not $sparkAlive) { Write-Host "[WARN] Spark Streaming 已退出" -ForegroundColor Red }
        if (-not $flaskAlive) { Write-Host "[WARN] Flask 已退出" -ForegroundColor Red }
    }
} finally {
    Write-Host "正在清理..."
    Get-Job | Stop-Job -PassThru | Remove-Job
}
