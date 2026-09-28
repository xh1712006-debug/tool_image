@echo off
chcp 65001 > nul
cls
echo =========================================================================
echo    CHAY TOOL TREN GOOGLE CHROME THAT CO SAN TAI KHOAN GMAIL (CDP MODE)
echo =========================================================================
echo.
echo [1] Dang kiem tra va ket noi vao Google Chrome that cua may...
echo [2] Profile dang dung: Default (xh1712006@gmail.com)
echo.
echo Meo: Ban co the doi profile bang cach sua: --cdp-profile "Profile 3"
echo.
python src/main.py --game Garena --start 0 --end 3 --prefix ivanclone --password Longcon@1234 --assistant --no-proxy --cdp
pause
