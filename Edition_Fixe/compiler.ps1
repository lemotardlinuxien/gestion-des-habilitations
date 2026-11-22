
# ============================================================
# COMPILATION - GESTION DES HABILITATIONS
# Compatible Edition Fixe et Edition Nomade
# ============================================================

$ErrorActionPreference = "Stop"

# Dossier racine de l'édition
$DossierProjet = $PSScriptRoot

# Noms des dossiers
$DossierBuild = Join-Path $DossierProjet "Build"
$DossierDist = Join-Path $DossierProjet "Dist"

# Chemins des fichiers
$FichierMain = Join-Path $DossierProjet "main.py"
$FichierIcone = Join-Path $DossierProjet "icons\app.ico"
$DossierIcons = Join-Path $DossierProjet "icons"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  COMPILATION GESTION DES HABILITATIONS" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# 1. Vérification des fichiers nécessaires
# ------------------------------------------------------------

if (-not (Test-Path $FichierMain)) {
    Write-Host "ERREUR : main.py introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $FichierIcone)) {
    Write-Host "ERREUR : icone app.ico introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DossierIcons)) {
    Write-Host "ERREUR : dossier icons introuvable." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------
# 2. Nettoyage des anciennes compilations
# ------------------------------------------------------------

Write-Host "[1/4] Nettoyage des anciennes compilations..." -ForegroundColor Yellow

foreach ($Dossier in @($DossierBuild, $DossierDist)) {
    if (Test-Path $Dossier) {
        Remove-Item $Dossier -Recurse -Force
    }
}

# ------------------------------------------------------------
# 3. Compilation PyInstaller
# ------------------------------------------------------------

Write-Host "[2/4] Compilation avec PyInstaller..." -ForegroundColor Yellow
Write-Host ""

Push-Location $DossierProjet

try {
    $Arguments = @(
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--name", "GestionHabilitations",
        "--icon", $FichierIcone,
        "--add-data", "$DossierIcons;icons",
        "--distpath", "Dist",
        "--workpath", "Build",
        "--specpath", "Build",
        "main.py"
    )

    & python @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "La compilation PyInstaller a échoué."
    }
}
catch {
    Write-Host ""
    Write-Host "ERREUR : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}

# ------------------------------------------------------------
# 4. Vérification et création du raccourci
# ------------------------------------------------------------

Write-Host ""
Write-Host "[3/4] Vérification de l'exécutable..." -ForegroundColor Yellow

$DossierExe = Join-Path $DossierDist "GestionHabilitations"
$Executable = Join-Path $DossierExe "GestionHabilitations.exe"

if (-not (Test-Path $Executable)) {
    Write-Host "ERREUR : executable introuvable après compilation." -ForegroundColor Red
    exit 1
}

Write-Host "Exécutable vérifié." -ForegroundColor Green

Write-Host ""
Write-Host "[4/4] Création du raccourci Windows..." -ForegroundColor Yellow

try {
    $WshShell = New-Object -ComObject WScript.Shell

    $CheminRaccourci = Join-Path $DossierProjet "GestionHabilitations.lnk"

    $Shortcut = $WshShell.CreateShortcut($CheminRaccourci)
    $Shortcut.TargetPath = $Executable
    $Shortcut.WorkingDirectory = $DossierExe
    $Shortcut.Description = "Gestion des habilitations"
    $Shortcut.Save()
}
catch {
    Write-Host "ERREUR lors de la création du raccourci." -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

# ------------------------------------------------------------
# Résultat final
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  COMPILATION TERMINEE AVEC SUCCES !" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host ""
Write-Host "Dossier Build : $DossierBuild"
Write-Host "Dossier Dist  : $DossierDist"
Write-Host "Raccourci     : $CheminRaccourci"

Write-Host ""
