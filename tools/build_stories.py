#!/usr/bin/env python3
"""Build the GoSki Stories pages from stories-src/.

    python3 tools/build_stories.py

Reads stories-src/site.json and every stories-src/<slug>/{story.json, body.html}
and writes:
  stories/index.html            list of stories, newest first
  stories/<slug>/index.html     each story, with Open Graph tags for Facebook
  ads-and-cookies/index.html    the ads and cookies notice AdSense needs
  ads.txt                       once an AdSense publisher id is set
and keeps the Stories entries in sitemap.xml and the AdSense site-verification
meta tag on the home page in step.

The site header, call-to-action band and footer are copied from
guides/index.html, so stories always match the rest of the site.
Images for a story live next to its built page in stories/<slug>/.
"""
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "stories-src"
OUT = ROOT / "stories"
SITE = "https://goskiapp.com"
CSS_VERSION = "20261116"
STORIES_CSS_VERSION = "20261121"  # bump when stories/stories.css changes


def load_shell():
    page = (ROOT / "guides" / "index.html").read_text(encoding="utf-8")
    top = page[page.index("<body"):page.index("<main")]
    bottom = page[page.index('<section class="cta-band"'):]
    return top, bottom


def esc(s):
    return html.escape(s, quote=True)


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def ad_head(site):
    client = site.get("adsense_client")
    if not client:
        return ""
    return (f'  <meta name="google-adsense-account" content="{esc(client)}">\n'
            f'  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(client)}" crossorigin="anonymous"></script>\n')


def ad_slot(site):
    client, slot = site.get("adsense_client"), site.get("in_article_slot")
    if not (client and slot):
        # No manual unit: Auto ads (switched on in AdSense) place ads themselves.
        return ""
    return ('<aside class="story-ad" aria-label="Advertisement"><span>Advertisement</span>'
            f'<ins class="adsbygoogle" style="display:block;text-align:center" data-ad-layout="in-article" '
            f'data-ad-format="fluid" data-ad-client="{esc(client)}" data-ad-slot="{esc(str(slot))}"></ins>'
            '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></aside>')


def head(title, description, url, image, image_w, image_h, og_type, site, extra_ld=None):
    ld = extra_ld or {}
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#020617">
  <meta name="color-scheme" content="dark">
  <meta name="apple-itunes-app" content="app-id=6759206548">
  <link rel="canonical" href="{url}">
  <link rel="icon" type="image/png" sizes="32x32" href="/assets/icon/icon-32.png">
  <link rel="apple-touch-icon" href="/assets/icon/icon-180.png">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{url}">
  <meta property="og:site_name" content="GoSki">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:image" content="{image}">
  <meta property="og:image:width" content="{image_w}">
  <meta property="og:image:height" content="{image_h}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preload" href="/fonts/inter-latin-wght.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/styles.css?v={CSS_VERSION}">
  <link rel="stylesheet" href="/stories/stories.css?v={STORIES_CSS_VERSION}">
{ad_head(site)}  <script type="application/ld+json">
{json.dumps(ld, indent=2, ensure_ascii=False)}
  </script>
</head>
"""


def crumbs(items):
    out = []
    for name, href in items:
        if href:
            out.append(f'<li><a href="{href}">{esc(name)}</a></li>')
        else:
            out.append(f'<li><span aria-current="page">{esc(name)}</span></li>')
    return '<ol class="crumbs">' + "".join(out) + "</ol>"


def breadcrumb_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + h}
        for i, (n, h) in enumerate(items)]}


def stories_footer_note():
    return ('<p class="story-note">GoSki Stories are free to read and supported by ads. '
            '<a href="/ads-and-cookies/">Ads and cookies</a></p>')


# The "See what GoSki does" section above every story's Sources (Kevin, 2026-11-20/21).
# 3D tab order (Kevin, 2026-11-21): two regular screens, one half regular / half satellite, then satellite screens.
# Big toggle buttons, in this order, each showing real app screens from /assets/screens/.
# Each screen: (file, width, height, title, caption, alt).
TOUR = [
    ("maps", "3D Resort Maps", "/trail-maps/", "See every trail map",
     '<path d="m8 3 4 8 5-5 5 15H2L8 3z"/>',
     "Every trail and lift on real 3D terrain. Spin, tilt and zoom to see how steep a run is before you ride it.",
     [("map-killington-3d-v2.webp", 720, 1561, "Killington, Vermont", "Trails, lifts and lodges on the 3D map.",
       "Killington 3D trail map in the GoSki app"),
      ("map-lake-louise-terrain-closeup-v1.webp", 720, 1561, "3D terrain up close", "Zoom in and tilt to see how steep each run really is.",
       "Close-up of Lake Louise's 3D terrain under Whitehorn Mountain in the GoSki app"),
      ("map-killington-split-v1.webp", 720, 1561, "Regular or satellite", "Switch on Satellite Overlay to see the real mountain photo.",
       "Killington 3D map in the GoSki app, left half the regular map, right half with Satellite Overlay"),
      ("map-killington-satellite-3d-v1.webp", 720, 1558, "Satellite Overlay", "The real mountain photo on the 3D map.",
       "Killington 3D trail map with Satellite Overlay in the GoSki app"),
      ("map-killington-satellite-closeup-v1.webp", 720, 1561, "Satellite Overlay up close", "High-definition photo: every tree line, trail and lift line.",
       "Close-up of Killington's Satellite Overlay photo with trails and lifts in the GoSki app"),
      ("map-killington-satellite-top-v1.webp", 720, 1558, "From above", "Every trail and lift over the satellite photo.",
       "Killington trail map from above with Satellite Overlay in the GoSki app")]),
    ("track", "Professional Telemetry & Ski Track", "/ski-tracker/", "How the Ski Tracker works",
     '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
     "The Ski Tracker follows your day: vertical, speed, distance and time, with every run drawn on the resort map and matched to the trails you skied.",
     [("session-live-v2.webp", 720, 1561, "Live stats", "Vertical, altitude, speed and distance while you ski.",
       "GoSki Ski Tracker showing vertical skied, altitude, distance and top speed"),
      ("session-route-v2.webp", 720, 1561, "Your route", "Every run on the map, colored by speed.",
       "A ski day's route drawn on the Killington trail map, colored by speed"),
      ("session-runs-v2.webp", 720, 1561, "Every run", "Matched to the trails you skied, with vertical and top speed.",
       "A recorded run in GoSki with the list of trails it followed")]),
    ("intel", "Mountain Intelligence", "/conditions/", "About Conditions",
     '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>'
     '<path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
     "Conditions on the 3D map: where the wind is strongest, which slopes are in the sun, where the wind piles powder or blows slopes bare, and how deep the snow is.",
     [("conditions-card-v2.webp", 720, 1564, "Conditions", "Wind, Powder Zone, Sun, Snow depth and Surface Conditions.",
       "The Conditions menu on the GoSki 3D map"),
      ("conditions-wind-v2.webp", 720, 1564, "Wind", "Wind speed and the windiest spots, hour by hour.",
       "Wind overlay on the Killington-Pico 3D map"),
      ("conditions-sun-v2.webp", 720, 1564, "Sun", "Sun and shade on every slope through the day.",
       "Sun overlay on the Killington-Pico 3D map"),
      ("conditions-powder-v2.webp", 720, 1564, "Powder Zone", "Where the wind piles snow and where it strips slopes bare.",
       "Powder Zone overlay on the Killington-Pico 3D map"),
      ("conditions-snow-depth-v2.webp", 720, 1564, "Snow depth", "Snow on the ground and new snow.",
       "Snow depth overlay on the Killington-Pico 3D map")]),
    ("forecast", "Advanced Forecast", "/features/#snow", "Snow forecasts and reports",
     '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.24"/><path d="M8 15h.01"/><path d="M8 19h.01"/>'
     '<path d="M12 17h.01"/><path d="M12 21h.01"/><path d="M16 15h.01"/><path d="M16 19h.01"/>',
     "Snow, rain, temperature and wind for the days ahead at every resort, and a map of where the next storm's snow will fall. Source: NOAA.",
     [("resort-forecast-v2.webp", 720, 1561, "Resort forecast", "Snow, rain, temperature and wind, hour by hour.",
       "The Killington forecast chart and table in GoSki"),
      ("forecast-map-v1.webp", 720, 1561, "Snow forecast map", "Where snow will fall over the next 48 hours.",
       "GoSki's snow forecast map over Utah, Idaho and Montana")]),
]

TOUR_SCRIPT = """<script>
(function () {
  var tabs = [].slice.call(document.querySelectorAll('.tour-tab'));
  if (!tabs.length) return;
  function show(tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
    if (focus) tab.focus();
    document.getElementById(tab.getAttribute('aria-controls')).dispatchEvent(new Event('tour:shown'));
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { show(t); });
    t.addEventListener('keydown', function (e) {
      var k = e.key, j = k === 'ArrowRight' || k === 'ArrowDown' ? i + 1 : k === 'ArrowLeft' || k === 'ArrowUp' ? i - 1 : k === 'Home' ? 0 : k === 'End' ? tabs.length - 1 : null;
      if (j === null) return;
      e.preventDefault();
      show(tabs[(j + tabs.length) % tabs.length], true);
    });
  });
  show(tabs[0]);

  // Swipe dots: when a row of screens is wider than the page, one dot per screen shows where you are,
  // and tapping a dot scrolls to that screen.
  [].slice.call(document.querySelectorAll('.tour-panel')).forEach(function (panel) {
    var row = panel.querySelector('.tour-phones'), dots = panel.querySelector('.tour-dots');
    var items = [].slice.call(row.children);
    items.forEach(function (item, n) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-label', 'Show screen ' + (n + 1) + ' of ' + items.length);
      b.addEventListener('click', function () { row.scrollTo({ left: item.offsetLeft - items[0].offsetLeft, behavior: 'smooth' }); });
      dots.appendChild(b);
    });
    function update() {
      dots.hidden = row.scrollWidth <= row.clientWidth + 4;
      // The current screen is the one at the row's left edge (the end of the row counts as the last screen).
      var max = row.scrollWidth - row.clientWidth, best = 0, bestD = Infinity;
      items.forEach(function (item, n) {
        var d = Math.abs(item.offsetLeft - items[0].offsetLeft - row.scrollLeft);
        if (d < bestD) { bestD = d; best = n; }
      });
      if (row.scrollLeft >= max - 2) best = items.length - 1;
      [].forEach.call(dots.children, function (b, n) { b.setAttribute('aria-current', n === best ? 'true' : 'false'); });
    }
    row.addEventListener('scroll', function () { window.requestAnimationFrame(update); }, { passive: true });
    window.addEventListener('resize', update);
    panel.addEventListener('tour:shown', update);
    update();
  });
})();
</script>"""


def tour_phone(src, w, h, title, cap, alt, href=None):
    img = f'<img src="{src}" width="{w}" height="{h}" loading="lazy" alt="{esc(alt)}">'
    text = f'<strong>{esc(title)}</strong>{esc(cap)}'
    if href:
        return f'<a class="tour-phone" href="{href}">{img}<span class="tour-phone__cap">{text}</span></a>'
    return f'<figure class="tour-phone">{img}<figcaption>{text}</figcaption></figure>'


def tour_section(slug, meta):
    """The button section. A story can put its own resorts in the 3D tab with
    "tour_maps" (and "tour_maps_lead") in story.json; otherwise TOUR's screens are used."""
    buttons, panels = [], []
    for i, (key, label, href, more, icon, lead, shots) in enumerate(TOUR):
        on = i == 0
        buttons.append(
            f'<button type="button" class="tour-tab" role="tab" id="tour-tab-{key}" aria-controls="tour-{key}" '
            f'aria-selected="{"true" if on else "false"}" tabindex="{0 if on else -1}">'
            f'<svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg><span>{esc(label)}</span></button>')
        if key == "maps" and meta.get("tour_maps"):
            lead = meta.get("tour_maps_lead", lead)
            phones = "".join(
                tour_phone(m["img"] if m["img"].startswith("/") else f'/stories/{slug}/{m["img"]}',
                           m.get("width", 645), m.get("height", 1398),
                           m["title"], m["caption"], m["alt"], m.get("href"))
                for m in meta["tour_maps"])
        else:
            phones = "".join(tour_phone(f"/assets/screens/{f}", w, h, title, cap, alt)
                             for f, w, h, title, cap, alt in shots)
        panels.append(
            f'<div class="tour-panel" id="tour-{key}" role="tabpanel" aria-labelledby="tour-tab-{key}" tabindex="0">'
            f'<p class="tour-panel__lead">{esc(lead)}</p>'
            f'<div class="tour-phones">{phones}</div>'
            f'<div class="tour-dots" hidden></div>'
            f'<a class="tour-more" href="{href}">{esc(more)} <span aria-hidden="true">→</span></a></div>')
    return f"""<section class="section story-tour" aria-labelledby="tour-title">
      <div class="wrap">
        <p class="eyebrow eyebrow--center">The GoSki app</p>
        <h2 id="tour-title">See what GoSki does</h2>
        <p class="lead tour-lead">Tap a feature to see real screens from the app.</p>
        <div class="tour-tabs" role="tablist" aria-label="GoSki features">{"".join(buttons)}</div>
        {"".join(panels)}
        <p class="tour-note">Some features require <a href="/pro/">GoSki PRO</a>.</p>
      </div>
    </section>
    {TOUR_SCRIPT}

    """


def build_story(slug, meta, body, site, top, bottom):
    url = f"{SITE}/stories/{slug}/"
    image = f"{SITE}/stories/{slug}/{meta['og_image']}"
    ad = ad_slot(site)
    body = body.replace("<!-- AD -->", ad)
    # The button section goes right after the article, above its Sources (Kevin, 2026-11-21).
    cut = body.find('<section class="story-sources"')
    main, sources = (body[:cut], body[cut:]) if cut >= 0 else (body, "")
    trail = [("Home", "/"), ("Stories", "/stories/"), (meta["title"], f"/stories/{slug}/")]
    ld = {"@context": "https://schema.org", "@graph": [
        breadcrumb_ld(trail),
        {"@type": "NewsArticle", "headline": meta["title"], "description": meta["description"],
         "datePublished": meta["date"], "dateModified": meta.get("updated", meta["date"]),
         "image": [image],
         "author": {"@type": "Organization", "name": "GoSki", "url": SITE + "/"},
         "publisher": {"@type": "Organization", "name": "GoSki",
                       "logo": {"@type": "ImageObject", "url": SITE + "/assets/icon/icon-512.png"}},
         "mainEntityOfPage": url}]}
    page = head(meta["title"], meta["description"], url, image,
                meta.get("og_image_width", 1200), meta.get("og_image_height", 630),
                "article", site, ld)
    page += top.replace('<body class="subpage">', '<body class="subpage story-page">')
    page += f"""<main id="main">
    <article class="story">
      <header class="page-hero story-head">
        <div class="wrap wrap--narrow">
          {crumbs([("Home", "/"), ("Stories", "/stories/"), (meta["kicker"], None)])}
          <p class="eyebrow">{esc(meta["kicker"])}</p>
          <h1>{esc(meta["title"])}</h1>
          <p class="lead">{esc(meta["dek"])}</p>
          <p class="updated">By GoSki · <time datetime="{meta["date"]}">{long_date(meta["date"])}</time></p>
        </div>
      </header>
      <div class="section story-section">
        <div class="wrap wrap--narrow">
          <div class="prose story-body">
{main}
          </div>
        </div>
      </div>
      {tour_section(slug, meta)}
      <div class="section story-section story-end">
        <div class="wrap wrap--narrow">
          <div class="prose story-body">
{sources}
          </div>
          {stories_footer_note()}
        </div>
      </div>
    </article>

    """
    page += bottom
    dest = OUT / slug / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


def build_index(stories, site, top, bottom):
    url = f"{SITE}/stories/"
    newest = stories[0][1]
    image = f"{SITE}/stories/{stories[0][0]}/{newest['og_image']}"
    trail = [("Home", "/"), ("Stories", "/stories/")]
    ld = {"@context": "https://schema.org", "@graph": [breadcrumb_ld(trail),
          {"@type": "CollectionPage", "name": "GoSki Stories", "url": url,
           "hasPart": [{"@type": "NewsArticle", "headline": m["title"],
                        "url": f"{SITE}/stories/{s}/", "datePublished": m["date"]} for s, m in stories]}]}
    desc = "Stories from the mountains: snow science, ski history and the strange things resorts do to open on time."
    page = head("GoSki Stories", desc, url, image, newest.get("og_image_width", 1200),
                newest.get("og_image_height", 630), "website", site, ld)
    page += top
    cards = []
    for slug, m in stories:
        cards.append(
            f'<li><a class="story-card" href="/stories/{slug}/">'
            f'<img src="/stories/{slug}/{m["card_image"]}" alt="{esc(m.get("card_image_alt", ""))}" loading="lazy">'
            f'<span class="story-card__text"><span class="eyebrow">{esc(m["kicker"])}</span>'
            f'<h2>{esc(m["title"])}</h2><p>{esc(m["dek"])}</p>'
            f'<time datetime="{m["date"]}">{long_date(m["date"])}</time></span></a></li>')
    page += f"""<main id="main">
    <section class="page-hero">
      <div class="wrap">
        {crumbs([("Home", "/"), ("Stories", None)])}
        <p class="eyebrow">Stories</p>
        <h1>GoSki Stories</h1>
        <p class="lead">Snow science, ski history and the strange things resorts do to open on time.</p>
      </div>
    </section>

    <section class="section" aria-label="All stories">
      <div class="wrap">
        <ul class="story-list">{"".join(cards)}</ul>
        {stories_footer_note()}
      </div>
    </section>

    """
    page += bottom
    (OUT / "index.html").write_text(page, encoding="utf-8")


def build_ads_page(site, top, bottom):
    url = f"{SITE}/ads-and-cookies/"
    title = "Ads and cookies on goskiapp.com | GoSki"
    desc = "How ads and cookies work on the GoSki website, and how to opt out of personalized ads."
    ld = {"@context": "https://schema.org", "@graph": [breadcrumb_ld([("Home", "/"), ("Ads and cookies", "/ads-and-cookies/")])]}
    page = head(title, desc, url, f"{SITE}/assets/og-image-v2.png", 1200, 630, "website", {}, ld)
    page += top
    page += f"""<main id="main">
    <section class="page-hero">
      <div class="wrap">
        {crumbs([("Home", "/"), ("Ads and cookies", None)])}
        <p class="eyebrow">Website</p>
        <h1>Ads and cookies</h1>
        <p class="lead">GoSki Stories are free to read because they show ads. This page explains how those ads work.</p>
        <p class="updated">Updated <time datetime="2026-11-19">November 19, 2026</time></p>
      </div>
    </section>

    <section class="section" aria-label="Ads and cookies">
      <div class="wrap wrap--narrow">
        <div class="prose">
          <h2>Where ads appear</h2>
          <p>Ads appear only on GoSki Stories pages (goskiapp.com/stories/). The GoSki app and the other pages of this website do not show ads.</p>
          <h2>Who serves them</h2>
          <p>Ads are served by Google AdSense. Third-party vendors, including Google, use cookies to serve ads based on your earlier visits to this website and other websites. Google's advertising cookies let Google and its partners serve ads to you based on your visits to this site and other sites on the internet.</p>
          <p>You can opt out of personalized advertising in Google's <a href="https://adssettings.google.com/">Ads Settings</a>, and opt out of some third-party vendors' cookies at <a href="https://www.aboutads.info/choices/">aboutads.info</a>. Learn more in <a href="https://policies.google.com/technologies/partner-sites">how Google uses information from sites that use its services</a>.</p>
          <h2>Consent</h2>
          <p>Visitors in the European Economic Area, the United Kingdom and Switzerland are asked for consent before personalized ads are shown, through Google's consent message. You can change your choice at any time from the privacy link that message adds to the page.</p>
          <h2>What GoSki itself collects</h2>
          <p>This website does not ask you to sign in and GoSki does not set its own tracking cookies on it. How the GoSki app handles your data is in the <a href="https://privacy.goskiapp.com/">GoSki Privacy Policy</a>.</p>
          <h2>Questions</h2>
          <p>Email <a href="mailto:support@goskiapp.com">support@goskiapp.com</a>.</p>
        </div>
      </div>
    </section>

    """
    page += bottom
    dest = ROOT / "ads-and-cookies" / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


def update_sitemap(stories):
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"  <!-- stories:start -->.*?<!-- stories:end -->\n", "", text, flags=re.S)
    newest = max(m.get("updated", m["date"]) for _, m in stories)
    lines = [f"  <url><loc>{SITE}/stories/</loc><lastmod>{newest}</lastmod></url>"]
    lines += [f"  <url><loc>{SITE}/stories/{s}/</loc><lastmod>{m.get('updated', m['date'])}</lastmod></url>"
              for s, m in stories]
    lines.append(f"  <url><loc>{SITE}/ads-and-cookies/</loc><lastmod>2026-11-19</lastmod></url>")
    block = "  <!-- stories:start -->\n" + "\n".join(lines) + "\n  <!-- stories:end -->\n"
    text = text.replace("</urlset>", block + "</urlset>")
    path.write_text(text, encoding="utf-8")


def update_home_and_ads_txt(site):
    client = site.get("adsense_client")
    home = ROOT / "index.html"
    text = home.read_text(encoding="utf-8")
    text = re.sub(r'  <meta name="google-adsense-account" content="[^"]*">\n', "", text)
    ads_txt = ROOT / "ads.txt"
    if client:
        text = text.replace("</head>", f'  <meta name="google-adsense-account" content="{esc(client)}">\n</head>', 1)
        pub = client.replace("ca-", "", 1)
        ads_txt.write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    elif ads_txt.exists():
        ads_txt.unlink()
    home.write_text(text, encoding="utf-8")


def main():
    site = json.loads((SRC / "site.json").read_text(encoding="utf-8"))
    top, bottom = load_shell()
    stories = []
    for d in sorted(p for p in SRC.iterdir() if p.is_dir()):
        meta = json.loads((d / "story.json").read_text(encoding="utf-8"))
        if meta.get("draft"):
            continue
        stories.append((d.name, meta, (d / "body.html").read_text(encoding="utf-8")))
    stories.sort(key=lambda s: s[1]["date"], reverse=True)
    for slug, meta, body in stories:
        build_story(slug, meta, body, site, top, bottom)
    build_index([(s, m) for s, m, _ in stories], site, top, bottom)
    build_ads_page(site, top, bottom)
    update_sitemap([(s, m) for s, m, _ in stories])
    update_home_and_ads_txt(site)
    print(f"Built {len(stories)} stories" + (" with AdSense " + site["adsense_client"] if site.get("adsense_client") else " (no AdSense id yet)"))


if __name__ == "__main__":
    main()
