$uri = "https://ne9zdvaamm.us-east-1.awsapprunner.com/ask"
$uri = "http://localhost:3000/ask"
$headers = @{ "Content-Type" = "application/json; charset=utf-8" }

$question = @"
Phân tích cổ phiếu FPT và đưa ra chiến lược đầu tư dài hạn
"@

[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$bodyObj = @{
    question = $question
    modelProvider = "bedrock"
    model = "bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0"
}

$body = $bodyObj | ConvertTo-Json -Depth 5 -Compress
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $bodyBytes | Select-Object -ExpandProperty answer | Out-File -FilePath "report.md" -Encoding utf8

Write-Host "Xong! Kiem tra file report.md" -ForegroundColor Green
