@echo off
cd /d "%~dp0"
echo === SCB — Sistema Campeonato Brasileiro ===
if not exist dados\scb.sqlite (
  echo Base nao encontrada — construindo do snapshot local...
  python -m scb.ingest
  python -m scb.elo_engine
  python -m scb.features_pit
  python -m scb.draw_curve
  python -m scb.predictor
)
python -m scb.web --open
pause
