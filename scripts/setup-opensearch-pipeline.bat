@echo off
REM OpenSearch Hybrid Search Pipeline Setup Script (Windows)
REM This script creates the required search pipeline for hybrid search functionality

set OPENSEARCH_URL=http://localhost:9201
set PIPELINE_NAME=hybrid-search-pipeline

echo OpenSearch Hybrid Search Pipeline Setup
echo ========================================

REM Check if curl is available
curl --version >nul 2>&1
if errorlevel 1 (
    echo Error: curl is not available. Please install curl or use Git Bash.
    pause
    exit /b 1
)

echo Checking OpenSearch connectivity...
curl -s "%OPENSEARCH_URL%/_cluster/health" >nul 2>&1
if errorlevel 1 (
    echo Error: Cannot connect to OpenSearch at %OPENSEARCH_URL%
    echo Please ensure OpenSearch is running and accessible.
    pause
    exit /b 1
)
echo Success: OpenSearch is accessible at %OPENSEARCH_URL%

echo.
echo Creating hybrid search pipeline...

REM Create temporary JSON file
echo { > temp_pipeline.json
echo   "description": "Post processor for hybrid search", >> temp_pipeline.json
echo   "phase_results_processors": [ >> temp_pipeline.json
echo     { >> temp_pipeline.json
echo       "normalization-processor": { >> temp_pipeline.json
echo         "normalization": { >> temp_pipeline.json
echo           "technique": "min_max" >> temp_pipeline.json
echo         }, >> temp_pipeline.json
echo         "combination": { >> temp_pipeline.json
echo           "technique": "harmonic_mean", >> temp_pipeline.json
echo           "parameters": { >> temp_pipeline.json
echo             "weights": [0.3, 0.7] >> temp_pipeline.json
echo           } >> temp_pipeline.json
echo         } >> temp_pipeline.json
echo       } >> temp_pipeline.json
echo     } >> temp_pipeline.json
echo   ] >> temp_pipeline.json
echo } >> temp_pipeline.json

curl -X PUT "%OPENSEARCH_URL%/_search/pipeline/%PIPELINE_NAME%" ^
  -H "Content-Type: application/json" ^
  -d @temp_pipeline.json

if errorlevel 1 (
    echo Error: Failed to create pipeline
    del temp_pipeline.json
    pause
    exit /b 1
)

REM Clean up temporary file
del temp_pipeline.json

echo.
echo Verifying pipeline creation...
curl -s "%OPENSEARCH_URL%/_search/pipeline/%PIPELINE_NAME%" | findstr "hybrid-search-pipeline" >nul
if errorlevel 1 (
    echo Error: Pipeline verification failed
    pause
    exit /b 1
)

echo Success: Pipeline verification successful

echo.
echo ========================================
echo OpenSearch hybrid search pipeline setup complete!
echo.
echo You can now use hybrid search with:
echo   VECTOR_DB=opensearch
echo   SEARCH_DB=opensearch
echo.
echo Weight configuration:
echo   [0.3, 0.7] = 30%% vector, 70%% text (keyword focus)
echo   [0.5, 0.5] = 50%% vector, 50%% text (balanced)
echo   [0.7, 0.3] = 70%% vector, 30%% text (semantic focus)
echo.
echo Pipeline URL: %OPENSEARCH_URL%/_search/pipeline/%PIPELINE_NAME%
echo.
pause
