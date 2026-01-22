<#
menu_io.ps1

Module for I/O utilities in quick-start menu
#>

function Get-EnvVariable {
    <#
    .SYNOPSIS
    Reads a variable from an environment file.

    .PARAMETER VariableName
    Name of the variable to read.

    .PARAMETER EnvFile
    Path to the environment file.

    .PARAMETER DefaultValue
    Default value if variable is not found.

    .OUTPUTS
    System.String
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$VariableName,
        [string]$EnvFile = ".env",
        [string]$DefaultValue = ""
    )

    if (Test-Path $EnvFile) {
        $content = Get-Content $EnvFile -ErrorAction SilentlyContinue
        foreach ($line in $content) {
            if ($line -match "^$VariableName=(.*)$") {
                $value = $matches[1] -replace '^["'']|["'']$', ''
                return $value.Trim()
            }
        }
    }
    return $DefaultValue
}
