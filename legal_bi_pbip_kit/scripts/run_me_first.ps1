$ErrorActionPreference = "Stop"
param(
    [switch] $Watch
)
Set-Location $PSScriptRoot\..

if ($Watch) {
    Write-Host "Watch mode: regenerating whenever scripts\*.py or scripts\report_assets\*.json change."
    Write-Host "Press Ctrl+C to stop.`n"
    py scripts\watch_pbip.py @args
    exit $LASTEXITCODE
}

py scripts\generate_legal_bi_pbip.py @args
Write-Host ""
Write-Host "Generated PBIP under output\Sidley_BI_Modernization_Demo"
Write-Host "Open output\Sidley_BI_Modernization_Demo\Sidley_BI_Modernization_Demo.pbip in Power BI Desktop."
Write-Host ""
Write-Host "Auto-regen while you edit:"
Write-Host "  .\scripts\run_me_first.ps1 -Watch"
Write-Host "  .\scripts\run_me_first.ps1 -Watch --out path\to\output"
Write-Host ""
Write-Host "To rehearse the Databricks pipeline locally:"
Write-Host "  py scripts\generate_legal_bi_pbip.py --databricks --dry-run"
