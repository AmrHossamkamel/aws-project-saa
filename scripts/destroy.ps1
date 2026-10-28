[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [string]$Region = 'us-east-1',
    [string]$StackName = 'scalelab-project-01'
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw 'AWS CLI v2 was not found.'
}

$stackJson = aws cloudformation describe-stacks --stack-name $StackName --region $Region --output json
if ($LASTEXITCODE -ne 0) { throw "Could not find stack $StackName in $Region." }
$stack = $stackJson | ConvertFrom-Json
$bucket = ($stack.Stacks[0].Outputs | Where-Object OutputKey -eq 'StaticAssetsBucketName').OutputValue
if (-not $bucket) { throw 'The stack did not return its static asset bucket. No cleanup was performed.' }

if ($PSCmdlet.ShouldProcess("CloudFormation stack '$StackName' in $Region", 'Empty the stack asset bucket and delete all stack resources')) {
    Write-Warning 'This removes the stack, its RDS database without a final snapshot, and all files in its private static asset bucket.'
    aws s3 rm "s3://$bucket/" --recursive --region $Region
    if ($LASTEXITCODE -ne 0) { throw 'Could not empty the stack asset bucket; stack deletion was stopped.' }

    aws cloudformation delete-stack --stack-name $StackName --region $Region
    if ($LASTEXITCODE -ne 0) { throw 'CloudFormation did not accept the delete request.' }
    aws cloudformation wait stack-delete-complete --stack-name $StackName --region $Region
    if ($LASTEXITCODE -ne 0) { throw 'Stack deletion did not complete. Review CloudFormation events.' }
    Write-Host "Stack $StackName was deleted. Review your account for retained backups or unrelated resources."
}
