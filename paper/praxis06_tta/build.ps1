param(
    [string]$Engine = "auto"
)

$ErrorActionPreference = "Stop"

function HasCommand($Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Push-Location $PSScriptRoot
try {
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
        latexmk -pdf -interaction=nonstopmode main.tex
    } elseif ($Engine -eq "pdflatex") {
        pdflatex -interaction=nonstopmode main.tex
        bibtex main
        pdflatex -interaction=nonstopmode main.tex
        pdflatex -interaction=nonstopmode main.tex
    } else {
        throw "Unsupported engine: $Engine"
    }
} finally {
    Pop-Location
}
