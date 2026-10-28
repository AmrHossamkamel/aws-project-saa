[CmdletBinding()]
param(
    [string]$Region = 'us-east-1',
    [string]$StackName = 'scalelab-project-01',
    [string]$AppName = 'scalelab',
    [string]$AppInstanceType = 't3.micro',
    [string]$DatabaseInstanceClass = 'db.t3.micro',
    [string]$DomainName = '',
    [string]$HostedZoneId = '',
    [string]$CertificateArn = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$template = Join-Path $repoRoot 'infra/template.yaml'
$staticDirectory = Join-Path $repoRoot 'app/static'

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw 'AWS CLI v2 was not found. Install it and configure credentials before deployment.'
}
if ($DomainName -and -not $HostedZoneId) {
    throw 'HostedZoneId is required when DomainName is provided.'
}
if ($HostedZoneId -and -not $DomainName) {
    throw 'DomainName is required when HostedZoneId is provided.'
}

$parameters = @(
    "AppName=$AppName",
    "AppInstanceType=$AppInstanceType",
    "DatabaseInstanceClass=$DatabaseInstanceClass",
    'MinCapacity=2',
    'DesiredCapacity=2',
    'MaxCapacity=6'
)
if ($DomainName) { $parameters += "DomainName=$DomainName" }
if ($HostedZoneId) { $parameters += "HostedZoneId=$HostedZoneId" }
if ($CertificateArn) { $parameters += "CertificateArn=$CertificateArn" }

Write-Host "Deploying $StackName in $Region ..."
aws cloudformation deploy `
    --template-file $template `
    --stack-name $StackName `
    --region $Region `
    --capabilities CAPABILITY_IAM `
    --parameter-overrides $parameters `
    --no-fail-on-empty-changeset
if ($LASTEXITCODE -ne 0) { throw 'CloudFormation deployment failed. Review the stack events in AWS.' }

$stackJson = aws cloudformation describe-stacks --stack-name $StackName --region $Region --output json
if ($LASTEXITCODE -ne 0) { throw 'Unable to read CloudFormation outputs.' }
$stack = $stackJson | ConvertFrom-Json
$outputs = @{}
foreach ($output in $stack.Stacks[0].Outputs) { $outputs[$output.OutputKey] = $output.OutputValue }

Write-Host 'Uploading static assets to the private S3 origin ...'
aws s3 sync $staticDirectory "s3://$($outputs['StaticAssetsBucketName'])/" `
    --region $Region `
    --delete `
    --cache-control 'public,max-age=86400'
if ($LASTEXITCODE -ne 0) { throw 'Static asset upload failed.' }

Write-Host 'Invalidating CloudFront cache ...'
aws cloudfront create-invalidation `
    --distribution-id $outputs['CloudFrontDistributionId'] `
    --paths '/*' `
    --region $Region | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'CloudFront invalidation request failed.' }

Write-Host ''
Write-Host "Application URL: $($outputs['ApplicationURL'])"
Write-Host "Static assets:   $($outputs['StaticAssetsURL'])/site.css"
Write-Host "Dashboard:       $($outputs['DashboardName'])"
Write-Host "Alarm topic ARN: $($outputs['AlarmTopicArn'])"
Write-Host 'The app may need several minutes to finish bootstrapping and pass ALB health checks.'
