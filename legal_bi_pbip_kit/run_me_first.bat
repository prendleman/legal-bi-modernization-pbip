@echo off
cd /d "%~dp0"
py scripts\generate_legal_bi_pbip.py %*
echo.
echo Generated PBIP under output\Sidley_BI_Modernization_Demo
echo Open output\Sidley_BI_Modernization_Demo\Sidley_BI_Modernization_Demo.pbip in Power BI Desktop.
echo.
echo To rehearse the Databricks pipeline locally:
echo   py scripts\generate_legal_bi_pbip.py --databricks --dry-run
echo.
pause
