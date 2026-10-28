[CmdletBinding()]
param(
    [string]$Region = 'us-east-1',
    [string]$StackName = 'scalelab-project-01',
    [int]$RetryCount = 30,
    [int]$RetryDelaySeconds = 10
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw 'AWS CLI v2 was not found.'
}

$stackJson = aws cloudformation describe-stacks --stack-name $StackName --region $Region --output json
if ($LASTEXITCODE -ne 0) { throw "Could not find stack $StackName in $Region." }
$stack = $stackJson | ConvertFrom-Json
$outputs = @{}
foreach ($output in $stack.Stacks[0].Outputs) { $outputs[$output.OutputKey] = $output.OutputValue }
$baseUrl = $outputs['ApplicationURL'].TrimEnd('/')
$cssUrl = "$($outputs['StaticAssetsURL'].TrimEnd('/'))/site.css"

Write-Host "Checking $baseUrl/healthz ..."
$healthy = $false
for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
    try {
        $health = Invoke-WebRequest -Uri "$baseUrl/healthz" -TimeoutSec 10 -UseBasicParsing
        if ($health.StatusCode -eq 200 -and $health.Content.Trim() -eq 'ok') {
            $healthy = $true
            break
        }
    } catch {
        if ($attempt -eq $RetryCount) { throw }
        Write-Host "Health endpoint is not ready (attempt $attempt/$RetryCount); waiting ..."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
}
if (-not $healthy) { throw 'The ALB health endpoint did not return HTTP 200.' }

Write-Host "Checking homepage and RDS-backed counter ..."
$homepageOk = $false
for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
    try {
        $page = Invoke-WebRequest -Uri $baseUrl -TimeoutSec 10 -UseBasicParsing
        if ($page.StatusCode -eq 200 -and $page.Content.Contains('ScaleLab')) {
            $homepageOk = $true
            break
        }
    } catch {
        if ($attempt -eq $RetryCount) { throw }
        Write-Host "Homepage is waiting on the database (attempt $attempt/$RetryCount); waiting ..."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
}
if (-not $homepageOk) { throw 'Homepage did not return HTTP 200 with the database available.' }

Write-Host "Checking CloudFront asset $cssUrl ..."
$css = Invoke-WebRequest -Uri $cssUrl -TimeoutSec 20 -UseBasicParsing
if ($css.StatusCode -ne 200 -or -not $css.Content.Contains('.shell')) {
    throw 'CloudFront did not return the expected stylesheet.'
}

Write-Host 'All checks passed: ALB health, app-to-RDS page, and CloudFront static asset.'
