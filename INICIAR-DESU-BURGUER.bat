@echo off
rem Inicia o Desu Burguer no Windows com dois cliques.
title Desu Burguer
cd /d "%~dp0"
echo Iniciado em %DATE% %TIME% > iniciar-log.txt
where node >> iniciar-log.txt 2>&1
node --version >> iniciar-log.txt 2>&1

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Node.js nao encontrado neste computador.
  echo  Instale a versao LTS em https://nodejs.org e depois abra este arquivo de novo.
  echo.
  start "" https://nodejs.org/pt-br
  pause
  exit /b 1
)

node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>22||(a===22&&b>=13)?0:1)"
if errorlevel 1 (
  echo.
  echo  Seu Node.js e antigo. Precisa ser 22.13 ou mais novo. Versao atual:
  node --version
  echo  Instale a versao LTS em https://nodejs.org e abra este arquivo de novo.
  echo.
  start "" https://nodejs.org/pt-br
  pause
  exit /b 1
)

node --disable-warning=ExperimentalWarning scripts\create-admin.js --if-missing
if errorlevel 1 (
  echo.
  echo  Nao foi possivel criar o administrador. Feche esta janela e tente de novo.
  pause
  exit /b 1
)

echo.
echo  Abrindo http://localhost:3000 no navegador...
echo  Para DESLIGAR o sistema, feche esta janela ou aperte Ctrl+C.
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:3000"
node --disable-warning=ExperimentalWarning server\index.js
pause
