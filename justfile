build:
  uv run split_whatsapp_messages.py messages.json
  PYTHON_UNBUFFERED=1 uv run podcast.py

week := `date +%F`

deploy:
  gh release upload main {{week}}/podcast-{{week}}.mp3
  gh release upload main --clobber podcast.xml

push:
  git add .
  git commit -m"Update podcast"
  git push
