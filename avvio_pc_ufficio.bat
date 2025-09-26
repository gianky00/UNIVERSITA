@echo off
title Avvio Applicazione con Setup

echo.
echo =======================================================
echo     Controllo e Installazione delle Dipendenze...
echo =======================================================
echo.

rem Assicura di usare il pip associato all'interprete Python corretto
"C:\Program Files (x86)\Thonny\python.exe" -m pip install -r requirements.txt

echo.
echo =======================================================
echo     Installazione completata. Avvio applicazione...
echo =======================================================
echo.

rem Avvia lo script principale
"C:\Program Files (x86)\Thonny\python.exe" "C:\Users\Coemi\Desktop\SCRIPT\UNIVERSITA\codici\python\app\main.py"

echo.
echo =======================================================
echo     Esecuzione terminata.
echo =======================================================
pause