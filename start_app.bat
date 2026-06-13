@echo off
chcp 65001 >nul
cd /d "%~dp0"

if /I "%~1"=="stop" goto :stop

echo ==============================================
echo   鍐峰惎鍔ㄦ贩鍚堟帹鑽愮郴缁?鈥?涓€閿惎鍔?echo ==============================================
echo.

REM 鈹€鈹€ 1. Spark Streaming 鈹€鈹€
echo [1/3] 鍚姩 Spark Streaming...
if not exist "spark-streaming\target\spark-streaming-1.0-shaded.jar" (
    echo   缂栬瘧 Spark Streaming...
    call E:\apache-maven-3.9.6\bin\mvn package -pl spark-streaming -DskipTests -q
)
rmdir /s /q checkpoints\streaming-v2 2>nul
start "SparkStreaming" spark-submit --class com.recommend.streaming.RealTimeAnalysisApp --master local[2] spark-streaming/target/spark-streaming-1.0-shaded.jar

REM 鈹€鈹€ 2. Flask 鈹€鈹€
echo [2/3] 鍚姩 Flask 鍚庣...
start "FlaskBackend" cmd /c "cd /d flask-backend && python run.py"

REM 鈹€鈹€ 3. Vue 鈹€鈹€
echo [3/3] 鍚姩 Vue 鍓嶇...
start "VueFrontend" cmd /c "cd /d vue-frontend && npm run dev"

echo.
echo ==============================================
echo   鍚姩瀹屾垚锛?echo   鍓嶇: http://localhost:5173/dashboard
echo   API:  http://localhost:5000/api/health
echo.
echo   鍏抽棴: start_app.bat stop
echo ==============================================
timeout /t 5 >nul
goto :eof

:stop
echo ==============================================
echo   鍐峰惎鍔ㄦ贩鍚堟帹鑽愮郴缁?鈥?鍏抽棴
echo ==============================================
echo.
taskkill /FI "WINDOWTITLE eq SparkStreaming" /F 2>nul && echo   Spark Streaming: 宸插仠姝?|| echo   Spark Streaming: 鏈繍琛?taskkill /FI "WINDOWTITLE eq FlaskBackend" /F 2>nul && echo   Flask: 宸插仠姝?|| echo   Flask: 鏈繍琛?taskkill /FI "WINDOWTITLE eq VueFrontend" /F 2>nul && echo   Vue: 宸插仠姝?|| echo   Vue: 鏈繍琛?echo.
echo 鍏ㄩ儴宸插叧闂€?goto :eof
