param([string]$InputPptx, [string]$OutputPdf)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject PowerPoint.Application
try {
  $presentation = $app.Presentations.Open($InputPptx, $true, $false, $false)
  $presentation.SaveAs($OutputPdf, 32)
  $presentation.Close()
} finally {
  $app.Quit()
}
