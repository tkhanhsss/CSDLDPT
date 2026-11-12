param(
    [string]$InputDocx = "$PSScriptRoot/GD1-GD2-CSDLDPT-23-03.docx"
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $InputDocx).Path
$output = [System.IO.Path]::ChangeExtension($source, '.pdf')
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($source, $false, $false)
    for ($pass = 0; $pass -lt 3; $pass++) {
        $null = $document.Fields.Update()
        $document.Repaginate()
    }
    $document.Save()
    $document.ExportAsFixedFormat($output, 17)
    $result = [ordered]@{
        renderer = 'Microsoft Word COM ExportAsFixedFormat'
        word_version = $word.Version
        pages = $document.ComputeStatistics(2)
        tables_of_contents = $document.TablesOfContents.Count
        output_pdf = $output
        rendered_at = (Get-Date).ToString('o')
    }
    $result | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/work/render_manifest.json" -Encoding UTF8
    $result | ConvertTo-Json
} finally {
    if ($null -ne $document) { $document.Close(0) }
    if ($null -ne $word) { $word.Quit() }
}
