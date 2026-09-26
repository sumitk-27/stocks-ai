this is a helping md how we are doing what are we doing
1) create a venv in windows

New-Item -ItemType Directory -Force -Path "$HOME\projects\stocks-ai\backend"
Set-Location "$Home\projects\stocks-ai\backend"
python -m venv .venv --without-pip