$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path
$excludedDirs = @(".git", "node_modules", ".next", "dist", "build", "out", ".turbo", ".vercel")
$allowedExtensions = @(
  ".md", ".txt", ".yml", ".yaml", ".json", ".js", ".jsx", ".ts", ".tsx",
  ".css", ".scss", ".html", ".toml", ".ps1"
)
$allowedNames = @(".env.example", ".gitignore", ".editorconfig", ".gitattributes", "license")
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$files = Get-ChildItem -Path $repoRoot -Recurse -File -Force | Where-Object {
  $fullName = $_.FullName
  foreach ($dir in $excludedDirs) {
    if ($fullName -like "*\$dir\*") {
      return $false
    }
  }

  $name = $_.Name.ToLowerInvariant()
  $ext = $_.Extension.ToLowerInvariant()
  return ($allowedNames -contains $name) -or ($allowedExtensions -contains $ext)
}

foreach ($file in $files) {
  $path = $file.FullName
  $text = [System.IO.File]::ReadAllText($path)
  $text = $text -replace "`r`n", "`n"
  $text = $text -replace "`r", "`n"
  $text = $text.TrimEnd("`n")
  $text = "$text`n"
  [System.IO.File]::WriteAllText($path, $text, $utf8NoBom)

  if ($path.StartsWith($repoRoot)) {
    $relativePath = $path.Substring($repoRoot.Length).TrimStart("\")
  } else {
    $relativePath = $path
  }
  Write-Host "Normalized: $relativePath"
}
