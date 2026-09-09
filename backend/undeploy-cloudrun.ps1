$ErrorActionPreference = 'Stop'

$ProjectId = if ($env:GOOGLE_CLOUD_PROJECT) { $env:GOOGLE_CLOUD_PROJECT } else { 'gen-lang-client-0538207552' }
$Region = if ($env:CLOUD_RUN_REGION) { $env:CLOUD_RUN_REGION } else { 'us-central1' }
$Service = if ($env:CLOUD_RUN_SERVICE) { $env:CLOUD_RUN_SERVICE } else { 'thats-a-wrap-media-api' }
$Gcloud = (Get-Command gcloud.cmd -ErrorAction Stop).Source

& $Gcloud run services delete $Service --project $ProjectId --region $Region --quiet
Write-Output "Deleted Cloud Run service: $Service"