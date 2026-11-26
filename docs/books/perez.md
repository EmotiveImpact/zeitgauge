# Carlota Perez: Technological Revolutions and Financial Capital (2002)

**Subtitle:** The Dynamics of Bubbles and Golden Ages.

## The book in one paragraph

Every fifty to sixty years a cluster of new technologies arrives that is cheap enough, and broad enough, to remake the whole economy. Perez shows that each of these surges follows the same two-act shape. In the first act, money pours into the new technology, a bubble forms, inequality widens and the old institutions struggle. The bubble bursts. In the second act, rules and habits catch up, the new technology spreads into ordinary life, and the gains are shared more widely. Her central claim is that the crash in the middle is a normal part of the pattern, and that the golden age which follows depends on society reshaping its institutions to fit the new technology.

## The key ideas

### 1. Five surges since 1771

Each surge starts with a "big bang" event in a core country:

- **1771, the Industrial Revolution.** Arkwright's mill at Cromford, Britain.
- **1829, the Age of Steam and Railways.** The Rocket locomotive on the Liverpool to Manchester line, Britain.
- **1875, the Age of Steel, Electricity and Heavy Engineering.** Carnegie's Bessemer steel plant, Pittsburgh, USA.
- **1908, the Age of Oil, the Car and Mass Production.** The first Model T, Detroit, USA.
- **1971, the Age of Information and Telecommunications.** The Intel microprocessor, Santa Clara, USA.

### 2. Two periods, four phases, one turning point

- **Installation period**
  - *Irruption:* the new technology appears and early adopters pile in.
  - *Frenzy:* finance takes over, prices run ahead of real earnings, a bubble forms.
- **Turning point:** the bubble bursts, a recession follows, and society argues about new rules. This can take years.
- **Deployment period**
  - *Synergy:* the technology spreads into everything, production investment leads, a golden age of broad growth.
  - *Maturity:* the paradigm runs out of steam, markets saturate, and the seeds of the next surge appear.

### 3. Financial capital and production capital

Perez separates money that seeks quick gains (financial capital) from money tied to making things (production capital). In installation, financial capital leads and decouples from the real economy, which feeds the bubble. In deployment, production capital takes the lead and growth becomes steadier and more widely shared.

### 4. The techno-economic paradigm

Each surge brings a new "common sense" for how to organise work and business. It has three parts:

- **A key input that becomes very cheap:** cotton, then coal and iron, then steel, then oil, then microchips.
- **New infrastructure:** canals, railways, electric grids, roads, the internet.
- **A new organisational model:** the factory, the joint-stock company, the assembly line, the network.

### 5. Institutions lag behind technology

The technology moves faster than laws, education, welfare and finance. The mismatch causes tension: unemployment in old industries, anger at new fortunes, regions left behind. The turning point is the moment the institutions are rebuilt.

### 6. Inequality rises in installation and falls in deployment

Each frenzy has its gilded age. Each golden age widens access, usually through a new consumption pattern. In the fourth surge that was the suburban home, the car and household appliances.

### 7. Bubbles leave useful infrastructure behind

Railway mania bankrupted investors and left Britain with railways. The dotcom crash left the world with cheap fibre. The crash transfers a built network from speculators to the public at a low price, which is what makes deployment possible.

### 8. Where we are now (her view and others)

Perez dates the information surge's installation from 1971 to 2000. She sees a long turning point: first the dotcom crash, then the 2008 financial crisis. In her view the golden age has not yet fully arrived, and it needs deliberate policy. She has argued for "smart green growth". Others treat AI as the big bang of a sixth surge. Either way, the AI market today shows frenzy behaviour: heavy investment well ahead of revenue, high valuations and intense hype.

## What Zeitgauge takes from it

- **Rule P1: a tech wave overlay.** Each monthly readings file carries `tech_wave` (`install`, `turn` or `deploy`). `playbook.py` adds the matching advice. This is set by judgement each month and recorded in the file, so it can be scored later.
- **Rule P2: what to build in each phase.**
  - *Install:* sell picks and shovels to people trying the new tool: templates, courses, starter kits, integrations.
  - *Turn:* watch for cheap leftovers after the crash, then bundle cheap infrastructure into simple products.
  - *Deploy:* mass-market products that use the technology quietly inside familiar things. This is where the largest consumer fortunes are made.
- **Rule P3: track the key input's price.** For AI this is the cost per unit of model output. A steep, sustained fall in that price is a deployment signal. It belongs in a future `tech` lens.
- **Rule P4: turning point signposts.** Watch for:
  - a sharp fall in tech valuations
  - new regulation of the technology
  - consolidation (weak players vanish)
  - falling input prices

  When two or more appear, revisit the `tech_wave` setting.
- **Rule P5: an inequality check.** A frenzy phase widens the gap between asset owners and earners. In the society lens, `house_earnings` is the proxy. If it keeps rising during a frenzy, favour products that serve people priced out (renters, younger adults).

## Limits

- The dates are clearer looking back than in real time. Use the phase as a lens, and keep score of calls about it (see `tetlock.md`).
- Perez wrote about core countries. Places outside the core, and different social groups, can sit in different phases at the same time.

## Combinations worth making

- **Perez with Minsky:** credit froth measures how hot the frenzy is (see `docs/frameworks.md`).
- **Perez with Bass and Rogers diffusion:** Perez gives the era, and the adoption curve gives the timing within it for a single product category.
- **Perez with Kondratiev:** Perez supplies a mechanism and phase signals for the long wave. That is why Zeitgauge uses her model in place of Kondratiev's contested price-wave dating.
