Import-Module Javinizer

Write-Host "Javinizer Recurse Loop Started"

while ($true) {
    Write-Host "Running Recurse..."
    Javinizer -Path '/data' -DestinationPath '/data' -Recurse
    Start-Sleep -Seconds 300
}
