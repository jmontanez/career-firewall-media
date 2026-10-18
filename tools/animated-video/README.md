# Animated video pipeline (no slideshows)

Rule from Jason, Oct 17: every video uses animated clips, never still images with zoom/pan.

Each scene is a real AI-animated clip from HeyGen Video (`heygen-video-1`, text to video, 9:16, 1080p),
cut to the narration, captioned, with the clip's own sound effects under the voice.

1. Make a folder, e.g. `timecrumbs/<slug>/`, with `scenes.json` (copy `timecrumbs/boston-molasses/scenes.json`):
   one scene per beat, `narration` (whole sentences), `prompt` (what moves, camera, sound), `duration` (5-15s).
   Keep the shared `style` paragraph so a channel looks consistent. No text in frame; captions are added later.
2. `python3 make_video.py gen <folder>` generates any missing `clips/NN.mp4` (about $0.06 per second at 1080p,
   so a 9-scene short is about $3 from the HeyGen API wallet). Look at every clip; delete a bad one and re-run to redo it.
3. Put the narration in `<folder>/vo.mp3` (one take of all narrations in order; Timecrumbs uses vidIQ voice
   "George - Warm, Captivating Storyteller"; Career Firewall uses Jason's cloned voice).
4. `python3 make_video.py assemble <folder>` writes `<slug>-hq.mp4` (1080x1920, -14 LUFS) and `<slug>-preview.mp4`.
   It prints when each sentence lands so caption timing can be checked.

Run it from a local scratch copy of the folder; the shared folder is a network mount and ffmpeg is slow on it.
Still needs the usual QA watch with sound and muted before scheduling.
