# Cria o atalho "Rastreador de Passagens" (com o ícone do avião) nesta pasta.
# Depois é só arrastar para a Área de Trabalho ou clicar com o direito > Fixar na barra de tarefas.
$pasta = $PSScriptRoot
$atalho = (New-Object -ComObject WScript.Shell).CreateShortcut("$pasta\Rastreador de Passagens.lnk")
$atalho.TargetPath = "$pasta\.venv\Scripts\pythonw.exe"
$atalho.Arguments = "`"$pasta\rastreador_app.pyw`""
$atalho.WorkingDirectory = $pasta
$atalho.IconLocation = "$pasta\recursos\icone.ico"
$atalho.Description = "Rastreador de Passagens"
$atalho.Save()
Write-Host "Atalho criado: $pasta\Rastreador de Passagens.lnk"
