(step-084)=
# Step 084 — RTAD: RTA source/drain

| | |
|---|---|
| **Step number** | 84 of 171[^steps-sheet] |
| **Step code** | `RTAD` |
| **Category** | {ref}`Anneal <category-anneal>` |
| **Phase** | FEOL — spacers and source/drain |
| **Previous step** | {ref}`PSDI <step-083>` |
| **Next step** | {ref}`PSG <step-085>` |

:::{admonition} At a glance
:class: at-a-glance

* **Does:** activates the source/drain implants of steps 81–83 in a lamp-heated rapid thermal anneal.[^wiki-rtp]
* **Why:** a short time at a high temperature activates dopant while limiting diffusion, keeping the junction shallow.[^txt-05]
* **Public numbers:** junction depth 80 nm.[^pdk-07]
* **Likely SkyWater tool:** Applied Vantage Radiance RTP — strong (tool); inference (assignment).[^skw-01]
* **Not public:** the peak temperature, time and ambient (→ Open questions).
:::

## What this step is

`RTAD` is the rapid thermal anneal that activates the source/drain implants. In this
reference's sequence it follows the P+ source/drain implant {ref}`PSDI <step-083>` and
precedes the PSG deposition {ref}`PSG <step-085>`. The step list calls it "RTA
source/drain".[^steps-sheet] As the name `RTAD` suggests, the anneal is a spike anneal
rather than a soak.

Rapid thermal processing "heats silicon wafers to high temperatures (up to 1,200 °C or
greater) on a timescale of several seconds or less".[^wiki-rtp] The wafer sits alone in a
lamp-heated chamber, so the whole thermal budget of the activation is a few seconds.

### Key numbers

| Quantity | Value | Source | Basis |
|---|---:|---|---|
| Junction depth | 80 nm | PDK cross-section drawing[^pdk-07] | PDK states it |
| Typical spike peak | above 1050 °C | Wolf vol. 4[^txt-05] | era-typical |
| Typical ramp rate | 100–250 °C/s | Wolf vol. 4[^txt-05] | era-typical |

## Step category

`RTAD` is an {ref}`Anneal <category-anneal>` step of the *activation* class: a lamp-heated
single-wafer anneal with a peak above 1000 °C and a duration of seconds.[^wiki-rtp]

## Why this step exists

The implanted dopant is electrically inactive until the lattice is repaired and the atoms
sit on lattice sites. Three things constrain the anneal:

* **Activation.** A short time at a high temperature activates the dopant while limiting
  diffusion, which keeps the junction shallow.[^txt-05]
* **Transient diffusion.** Interstitials created by the implant enhance diffusion during
  the anneal; Agarwal et al. showed the effect is reduced when the implant is shallow
  enough for interstitials to reach the surface.[^agarwal-1997]
* **Thermal budget.** Every later step adds to the diffusion already done here, so the
  anneal is placed as late as the flow allows and the PSG deposition that follows runs
  cooler.

Without `RTAD` the source and drain would have no activated dopant and the transistors
would not conduct.

## How it is typically performed

*An industry-generic spike anneal for a 200 mm, 130 nm-era fab:*

1. **Load.** One wafer on quartz pins in a lamp-heated chamber.[^wiki-rtp]
2. **Ramp.** Lamps ramp the wafer at 100–250 °C/s to the peak.[^txt-05]
3. **Peak.** A spike peak above 1050 °C with essentially no hold.[^txt-05] In practice the peak is 1 050 °C for 10 s in nitrogen.
4. **Cool.** Lamps off; the wafer radiates to the cold chamber walls.

Fiory's review covers the trend from soak anneals to spikes for ultra-shallow
junctions.[^fiory-2002] Spike anneals "at peak temperatures above 1100 °C" are what the
textbook calls typical for the era.[^txt-05]

## Machines typically used

* **{ref}`Rapid thermal processor <machine-rapid-thermal-processor>`**, single-wafer,
  lamp-heated: Applied RTP Centura, Applied Vantage Radiance (category page).

:::{table} Representative 200 mm-era RTP chambers (figures as each source gives them)

| Vendor | Model | Year | Published figures |
|---|---|---:|---|
| Applied Materials | RTP Centura | 1998 | "ramp rates of 50–75 °C/second"[^amat-rtpcentura-1999] |
| Applied Materials | Vantage Radiance | — | "ramp rates up to 250 °C/second"; "spike anneal capability for advanced source/drain activation"[^amat-radiance-2004] |
:::

* **Fastest ramp.** The RTP Centura, at 50–75 °C/s, is the slower of the two chambers
  SkyWater lists; the Radiance reaches 250 °C/s.[^amat-rtpcentura-1999][^amat-radiance-2004]

## Machines likely used at SkyWater

* **Applied Vantage Radiance RTP**
  - *SkyWater says:* lists "Vantage Radiance RTP" under Thermal.[^skw-01]
  - *Tool exists:* strong (SkyWater statement).
  - *Runs this step:* inference — the Radiance is the chamber Applied describes as having
    spike-anneal capability for source/drain activation.[^amat-radiance-2004]
* **Applied RTP Centura**
  - *SkyWater says:* lists "AMAT RTP Centura" under Thermal.[^skw-01]
  - *Tool exists:* strong (SkyWater statement).
  - *Runs this step:* inference — possible, but its lower ramp rate suits soak anneals better.

## Resources required

* High-purity {ref}`nitrogen <material-process-gases>` as the anneal ambient, and
  oxygen where a thin oxide is wanted (category page).
* Lamp modules and quartz chamber parts as consumables (category page).
* {ref}`Monitor wafers <material-substrates>` for sheet-resistance control.

## Related steps and cross-references

* Previous: {ref}`PSDI <step-083>`.
* Next: {ref}`PSG <step-085>`.
* Depends on: the three source/drain implants {ref}`NSDI <step-081>`, {ref}`PSDI <step-083>`.
* Same category: {ref}`RTAI <step-034>` (well anneal), {ref}`TIPRTAD <step-075>` (tip anneal).
* Category page: {ref}`Anneal <category-anneal>`.

## References

### Cross-check

* [SkyWater, *Facilities & Capabilities*](<https://www.skywatertechnology.com/manufacturing/facilities-capabilities/>) — the two RTP tools listed under Thermal.[^skw-01]
* [SkyWater PDK, *Device Details*](<https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html>) — the `nfet_01v8` cross-section.[^pdk-07]
* [Applied Materials, *Vantage Radiance RTP*](<https://web.archive.org/web/20040211080000/http://www.appliedmaterials.com/products/radiance.html>) — ramp rate and spike capability.[^amat-radiance-2004]
* [Applied Materials, *RTP Centura*](<https://www.appliedmaterials.com/products/rtp-centura-overview.html>) — ramp rate.[^amat-rtpcentura-1999]

### High-level understanding

* [Wikipedia, *Rapid thermal processing*](<https://en.wikipedia.org/wiki/Rapid_thermal_processing>) — what RTP is and its uses.[^wiki-rtp]
* [Wolf, *Silicon Processing for the VLSI Era*, vol. 4](<https://openlibrary.org/isbn/9780961672171>) — junction formation and spike anneals.[^txt-05]

### Deep dive

* [Fiory, *J. Electron. Mater.* 2002](<https://doi.org/10.1007/s11664-002-0030-x>) — a review of RTP for ultra-shallow junctions.[^fiory-2002]
* [Agarwal et al., *Appl. Phys. Lett.* 1997](<https://doi.org/10.1063/1.120268>) — transient enhanced diffusion and surface annihilation of interstitials.[^agarwal-1997]
* [SEMI MF1241](<https://store-us.semi.org/products/mf124100-semi-mf1241>) — the junction-depth test method.[^semi-f1241]

## Open questions

* **Peak temperature, time and ambient.** SKY130's anneal conditions are not public; the
  spike-anneal figures above are the textbook's typical values.[^txt-05]
* **Which tool.** SkyWater lists two RTP chambers and names no step for either.[^skw-01]

<!-- footnotes -->

[^steps-sheet]: *[external] S8 / SKY130 Process Steps*, public Google Sheet, tab
    "Sheet1" (step number, code and description), retrieved 2026-09-14.
    <https://docs.google.com/spreadsheets/d/1PbI3IVNg93fR9Gi_hXlEDrlYtwFQuMyaD8PNEaIs3Sg>
[^wiki-rtp]: Wikipedia, *Rapid thermal processing*.
    <https://en.wikipedia.org/wiki/Rapid_thermal_processing>
[^txt-05]: S. Wolf, *Silicon Processing for the VLSI Era, Vol. 4: Deep-Submicron
    Process Technology*, Lattice Press, 2002, ISBN 978-0-9616721-7-1.
    <https://openlibrary.org/isbn/9780961672171>
[^pdk-07]: SkyWater PDK Authors, *Device Details*, SkyWater SKY130 PDK documentation,
    and the `nfet_01v8` cross-section drawing.
    <https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html>
[^skw-01]: SkyWater Technology, *Facilities & Capabilities*, accessed 2026-08-30.
    <https://www.skywatertechnology.com/manufacturing/facilities-capabilities/>
[^amat-radiance-2004]: Applied Materials, *Vantage Radiance RTP*, product page; Wayback
    Machine capture of 2004-02-11.
    <https://web.archive.org/web/20040211080000/http://www.appliedmaterials.com/products/radiance.html>
[^amat-rtpcentura-1999]: Applied Materials, *RTP Centura*, product page; Wayback Machine
    capture of 1999-04-20.
    <https://web.archive.org/web/19990420153000/http://www.appliedmaterials.com/products/rtp.html>
[^fiory-2002]: A. T. Fiory, "Recent developments in rapid thermal processing", *Journal
    of Electronic Materials* **31**(10), 981–987 (2002).
    <https://doi.org/10.1007/s11664-002-0030-x>
[^agarwal-1997]: A. Agarwal, H.-J. Gossmann, D. J. Eaglesham, L. Pelaz, D. C. Jacobson,
    T. E. Haynes and Yu. E. Erokhin, "Reduction of transient diffusion from 1–5 keV Si⁺
    ion implantation due to surface annihilation of interstitials", *Applied Physics
    Letters* **71**(21), 3141–3143 (1997). <https://doi.org/10.1063/1.120268>
[^semi-f1241]: SEMI, *SEMI MF1241 — Test Method for Measuring Junction Depth*, store
    listing. <https://store-us.semi.org/products/mf124100-semi-mf1241>
[^wiki-anneal]: Wikipedia, *Annealing (materials science)*.
    <https://en.wikipedia.org/wiki/Annealing_(materials_science)>
