# Social media signals

Social platforms show what people are worried about days before it reaches official data. Zeitgauge can count how many posts a day mention money-worry terms on each platform and add that count to the daily pulse.

Every platform is **off** until you switch it on. Run `zeitgauge social` at any time to see what is on, what it costs and what is missing.

---

## What each platform costs

Prices were checked on 26 November 2026. Check again before switching on.

**Bluesky: free**
- Official API. Search needs a signed-in account, so use an app password.
- No location filter, so the UK terms lean on British wording such as "skint".

**YouTube: free within a quota**
- 10,000 units a day. Each search page costs 100 units, so about 100 searches a day.
- The default settings use 400 units a day per region.

**X: pay per use**
- No subscription since February 2026. Reading posts costs about $0.005 each ($5 per 1,000).
- Zeitgauge only asks for counts, about $0.005 per request. One request a day covers the daily signal, about $0.15 a month.
- The optional hourly alert adds about $3.70 a month per region.
- A monthly budget (default $5) stops all calls once it is reached.
- The X API caps pay-per-use at 3 million post reads a month. Zeitgauge reads none.

**Reddit: needs a commercial agreement**
- The free tier is for non-commercial use only. A paid product needs a signed agreement, and Reddit does not publish the price.
- Reddit stopped approving new public API requests on 31 October 2026 and plans to end public access in March 2027.
- The adapter will not run until `approved_use = true`, which you should set only once Reddit has approved this use in writing.

**TikTok: no official route**
- The Research API is for non-profit academic research only. Commercial users are not eligible.
- The Commercial Content API covers EU ads only.
- Creative Center trend pages have no official API.
- If you become a verified TikTok advertiser, ask TikTok about discovery data through the API for Business. An adapter can be added then.

---

## Why there is no "way around"

Scraping sites that forbid it, or slipping past a platform's blocks, breaks their terms. Accounts get banned, data stops without warning and a paid product built on it carries legal risk. Every adapter here uses an official API with your own keys.

Plenty of the same signal is available legitimately:
- **Google Trends** shows what people search for (already in the pulse config, off by default).
- **Wikipedia pageviews** show what people read up on (in the pulse).
- **GDELT** covers news in over 100 languages (in the pulse and alerts).
- **Bluesky and YouTube** are free through their APIs.
- **Licensed vendors** resell social data under contract if Zeitgauge later needs TikTok or Instagram coverage.

---

## How to switch a platform on

1. Get the keys (the `how_to` line for each platform in `config/social.toml` says where).
2. Save them as repository secrets: Settings > Secrets and variables > Actions > New repository secret.
   - Bluesky: `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`
   - YouTube: `YOUTUBE_API_KEY`
   - X: `X_BEARER_TOKEN`
   - Reddit: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
3. Set `enabled = true` for that platform in `config/social.toml` and commit.
4. The next morning's run starts counting. The platform joins the pulse after 37 days of counts. X fills in its last 7 days on the first run, so it gets there sooner.

To switch off, set `enabled = false`. Stored counts stay in `data/social/<region>/`.

---

## How it feeds the pulse

- Each platform's daily total across its terms becomes one pulse signal, at half weight, because social chatter is noisy.
- More money-worry posts than usual counts as worse for households.
- Terms marked as "capped" hit the page limit, so the true count was higher. If a term caps often, make it narrower or raise `max_pages`.

Edit the terms per region in `config/social.toml`. Choose phrases people use when money is tight. Brand names and news topics tend to follow a single story, which drowns out the mood.
