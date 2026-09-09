param(
    [switch]$RotateSecrets,
    [string]$AllowedOrigins = 'https://magnificent-creponne-47e91e.netlify.app'
)
$ErrorActionPreference = 'Stop'

$ProjectId = if ($env:GOOGLE_CLOUD_PROJECT) { $env:GOOGLE_CLOUD_PROJECT } else { 'gen-lang-client-0538207552' }
$Region = if ($env:CLOUD_RUN_REGION) { $env:CLOUD_RUN_REGION } else { 'us-central1' }
$Service = if ($env:CLOUD_RUN_SERVICE) { $env:CLOUD_RUN_SERVICE } else { 'thats-a-wrap-media-api' }
$EnvFile = Join-Path $PSScriptRoot '.env'
$Gcloud = (Get-Command gcloud.cmd -ErrorAction Stop).Source

if (-not (Test-Path $EnvFile)) {
    throw "Missing $EnvFile. Create it locally with the real backend values before deploying."
}

& $Gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com --project $ProjectId | Out-Null

$secretNames = @()
$tempFiles = @()
try {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $_ -notmatch '^\s*#') {
            $name = $Matches[1]
            $value = $Matches[2].Trim()
            if ($value.StartsWith('"') -and $value.EndsWith('"')) { $value = $value.Substring(1, $value.Length - 2) }
            if ($value.StartsWith("'") -and $value.EndsWith("'")) { $value = $value.Substring(1, $value.Length - 2) }
            if ($value.Length -eq 0) { return }

            if ($name -eq 'ALLOWED_ORIGINS') { return }

            $secretResource = & $Gcloud secrets list --filter="name:$name" --format='value(name)' --project $ProjectId
            if ($secretResource -and -not $RotateSecrets) {
                $secretNames += "$name=$name`:latest"
                return
            }

            $tempFile = Join-Path ([System.IO.Path]::GetTempPath()) ("thats-a-wrap-secret-" + [guid]::NewGuid().ToString('N'))
            [System.IO.File]::WriteAllText($tempFile, $value)
            $tempFiles += $tempFile

            if ($secretResource) {
                & $Gcloud secrets versions add $name --data-file=$tempFile --project $ProjectId | Out-Null
            } else {
                & $Gcloud secrets create $name --replication-policy=automatic --project $ProjectId | Out-Null
                & $Gcloud secrets versions add $name --data-file=$tempFile --project $ProjectId | Out-Null
            }
            $secretNames += "$name=$name`:latest"
        }
    }

    $serviceAccount = "thats-a-wrap-runtime@$ProjectId.iam.gserviceaccount.com"
    $accountExists = & $Gcloud iam service-accounts list --filter="email:$serviceAccount" --format='value(email)' --project $ProjectId
    if (-not $accountExists) {
        $previousErrorAction = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $Gcloud iam service-accounts create thats-a-wrap-runtime --display-name="That's A Wrap runtime" --project $ProjectId 2>&1 | Out-Null
        $createAccountExit = $LASTEXITCODE
        $ErrorActionPreference = $previousErrorAction
        if ($createAccountExit -ne 0) { throw "Could not create the Cloud Run runtime service account." }
    }
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $Gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$serviceAccount" --role="roles/secretmanager.secretAccessor" --project $ProjectId 2>&1 | Out-Null
    $bindingExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorAction
    if ($bindingExit -ne 0) { throw "Could not grant Secret Manager access to the Cloud Run runtime account." }

    & $Gcloud run deploy $Service --source $PSScriptRoot --project $ProjectId --region $Region --allow-unauthenticated --service-account $serviceAccount --set-secrets ($secretNames -join ',') --set-env-vars "ALLOWED_ORIGINS=$AllowedOrigins" --memory 4Gi --cpu 2 --max 3 --port 8000 --quiet
} finally {
    foreach ($tempFile in $tempFiles) {
        Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Output "Deployed service: $Service"
Write-Output "URL: $(& $Gcloud run services describe $Service --project $ProjectId --region $Region --format='value(status.url)')"