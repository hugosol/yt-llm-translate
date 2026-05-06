---
name: yt-llm-translate
description: Download YouTube videos and generate translated subtitles. Use this whenever the user provides a YouTube URL and asks to download the video, generate subtitles, translate subtitles, or create bilingual captions. Default translation target is Chinese. Even if the user only says "download this video" or "get subtitles for this," trigger this skill when a YouTube link is involved.
---

Run the entry script using the full path to the skill's scripts directory. Do not change the current working directory — output files should land in the user's workspace, not the skill directory.
All workflow steps (download, punctuator, translate) are handled by the scripts.

```
python "<path-to-skill>/scripts/entry.py" "<youtube_url>"
```
