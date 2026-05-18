param(
    [string]$Engine = "auto",
    [ValidateSet("main", "thesis_chapter")]
    [string]$Target = "main"
)

$ErrorActionPreference = "Stop"

function HasCommand($Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Push-Location $PSScriptRoot
try {
    $tex = "$Target.tex"
    if ($Engine -eq "auto") {
        if (HasCommand "latexmk") {
            $Engine = "latexmk"
        } elseif (HasCommand "pdflatex") {
            $Engine = "pdflatex"
        } else {
            throw "No LaTeX engine found. Install TeX Live/MiKTeX or compile this folder in Overleaf/GitHub Actions."
        }
    }

    if ($Engine -eq "latexmk") {
        latexmk -pdf -interaction=nonstopmode $tex
    } elseif ($Engine -eq "pdflatex") {
        pdflatex -interaction=nonstopmode $tex
        bibtex $Target
        pdflatex -interaction=nonstopmode $tex
        pdflatex -interaction=nonstopmode $tex
    } else {
        throw "Unsupported engine: $Engine"
    }
} finally {
    Pop-Location
}
