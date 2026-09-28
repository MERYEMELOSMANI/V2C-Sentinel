param([string]$InputDoc, [string]$OutputPdf)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
try {
  $document = $app.Documents.Open($InputDoc, $false, $true)
  foreach ($section in $document.Sections) {
    foreach ($footer in $section.Footers) {
      if ($footer.Exists) { [void]$footer.Range.Fields.Update() }
    }
    foreach ($header in $section.Headers) {
      if ($header.Exists) { [void]$header.Range.Fields.Update() }
    }
  }
  [void]$document.Fields.Update()
  $document.ExportAsFixedFormat($OutputPdf, 17)
  $document.Close(0)
} finally { $app.Quit() }
