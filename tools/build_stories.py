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
STORIES_CSS_VERSION = "20261119"  # bump when stories/stories.css changes


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


def build_story(slug, meta, body, site, top, bottom):
    url = f"{SITE}/stories/{slug}/"
    image = f"{SITE}/stories/{slug}/{meta['og_image']}"
    ad = ad_slot(site)
    body = body.replace("<!-- AD -->", ad)
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
{body}
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
