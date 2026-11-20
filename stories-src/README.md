# GoSki Stories

Articles at https://goskiapp.com/stories/, made to be linked from the first comment of
GoSki's Facebook posts. They are the only pages on the site that show ads.

## Add a story

1. Pick a short slug, e.g. `winch-cat`. The story will live at `goskiapp.com/stories/winch-cat/`.
2. Create `stories-src/<slug>/story.json` (copy `snow-farming/story.json`):
   - `title`, `description` (Facebook and Google show it), `dek` (line under the headline),
     `kicker` (small label above the headline), `date` (YYYY-MM-DD), optional `updated`.
   - `og_image`: the 1200x630 image Facebook shows in the link preview.
   - `card_image` and `card_image_alt`: the picture on the Stories list.
   - `"draft": true` keeps a story out of the build.
3. Write `stories-src/<slug>/body.html`: only the article body (figures, paragraphs, `<h2>`/`<h3>`).
   Put `<!-- AD -->` where an in-article ad may go (about every 3 to 4 paragraphs, never more than 3).
   End with a "See these mountains in 3D" section of GoSki 3D map screens for resorts relevant to
   the story (`.story-3d` / `.story-phones`, as in snow-farming), each linking to its `/resorts/<id>/` page.
4. Put the images in `stories/<slug>/` (JPEG, about 1200 px wide for photos, under 500 KB each).
5. Run `python3 tools/build_stories.py`. It writes the story page, the Stories list, the sitemap
   entries and `ads-and-cookies/`. Commit the source and the built files together.
6. After it is live, paste the URL into https://developers.facebook.com/tools/debug/ and press
   "Scrape Again" so Facebook picks up the preview image.

## "See what GoSki does" (every story, automatic)

Every story page ends, after the article, with a section of four big toggle buttons, in this order
(Kevin, 2026-11-20): **3D Resort Maps**, **Professional Telemetry & Ski Track**, **Mountain Intelligence**,
**Advanced Forecast**. Each shows real app screens from `/assets/screens/`: the 3D maps; the tracker's live stats,
route and recorded runs; the Conditions menu with the Wind, Sun, Powder Zone and Snow depth overlays; the resort
forecast table and the snow forecast map. `build_stories.py` adds it (`TOUR`); stories don't write it in `body.html`.
To change a screen, add a new 720-px WebP under a new file name and point `TOUR` at it.

## Ads (Google AdSense)

Set the ids in `stories-src/site.json` and rebuild:

- `adsense_client`: the publisher id, `ca-pub-` followed by 16 digits. This adds the AdSense script to
  every story page, the verification tag to the home page, and `/ads.txt`.
- `in_article_slot`: optional. The id of an "In-article" ad unit made in AdSense (Ads > By ad unit).
  With it, each `<!-- AD -->` becomes that unit. Without it, AdSense Auto ads places ads itself.

The app pages never get the AdSense script, only `/stories/`.
