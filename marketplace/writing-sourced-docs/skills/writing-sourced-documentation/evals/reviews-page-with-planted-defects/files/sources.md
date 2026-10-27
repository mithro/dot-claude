# Source notes for step 084 RTAD — source/drain activation anneal

TEST FIXTURE. A researcher's notes of what each fetched source says. These are the only
sources the page may cite, and the only record of what each says.

## S1 — the step list (label `[^steps-sheet]`)

*S8 / SKY130 Process Steps*, public Google Sheet, tab "Sheet1", retrieved 2026-09-14.
<https://docs.google.com/spreadsheets/d/1PbI3IVNg93fR9Gi_hXlEDrlYtwFQuMyaD8PNEaIs3Sg>

Row 84: code `RTAD`, description "RTA source/drain". Row 83: `PSDI`, "P+ S/D implant".
Row 85: `PSG`, "PSG deposition". The sheet records number, code and description only;
it says nothing about temperature, time, ramp rate, ambient or tool.

## S2 — Wikipedia, *Rapid thermal processing* (label `[^wiki-rtp]`)

<https://en.wikipedia.org/wiki/Rapid_thermal_processing>

Notes: RTP "heats silicon wafers to high temperatures (up to 1,200 °C or greater) on a
timescale of several seconds or less"; the wafer is heated by lamps; one use is dopant
activation after ion implantation. No activation temperature for any particular process
is given.

## S3 — Wolf, *Silicon Processing for the VLSI Era*, vol. 4, Lattice Press, 2002 (label `[^txt-05]`)

<https://openlibrary.org/isbn/9780961672171>

Notes (chapter on junction formation, read in part): for 130 nm-era source/drain
activation a "spike anneal" — a ramp to a peak with essentially no hold — is typical;
the chapter gives typical spike peaks "above 1050 °C" with ramp rates of "100–250 °C/s";
it explains that a short time at a high temperature activates dopant while limiting
diffusion, which keeps the junction shallow. The book's values are typical for the era,
not any fab's.

## S4 — SkyWater PDK Authors, *Device Details* and the `nfet_01v8` cross-section drawing (label `[^pdk-07]`)

<https://skywater-pdk.readthedocs.io/en/main/rules/device-details.html>

Notes: the cross-section drawing shows the source/drain regions as shaded boxes below the
spacers; it carries no depth dimension and no scale. The page text does not state a
junction depth. (A reading of the drawing's proportions against the drawn gate oxide
would be this reference's own estimate, not a stated PDK value.)

## S5 — SkyWater Technology, *Facilities & Capabilities*, accessed 2026-08-30 (label `[^skw-01]`)

<https://www.skywatertechnology.com/manufacturing/facilities-capabilities/>

Notes: under "Thermal" the page lists, verbatim, "AMAT RTP Centura" and "Vantage
Radiance RTP". It names no process, temperature or step.

## S6 — Applied Materials, *Vantage Radiance RTP* product page, Wayback Machine capture of 2004-02-11 (label `[^amat-radiance-2004]`)

<https://web.archive.org/web/20040211080000/http://www.appliedmaterials.com/products/radiance.html>

Notes: describes the Radiance as a single-wafer lamp-heated RTP chamber with "ramp rates
up to 250 °C/second" and "spike anneal capability for advanced source/drain activation".
The page does not give the year the product was introduced.

## S7 — Applied Materials, *RTP Centura* product page, Wayback Machine capture of 1999-04-20 (label `[^amat-rtpcentura-1999]`)

<https://web.archive.org/web/19990420153000/http://www.appliedmaterials.com/products/rtp.html>

Notes: describes the RTP Centura as a single-wafer RTP chamber on the Centura platform
with "ramp rates of 50–75 °C/second". No introduction year on the page.

## S8 — Fiory, "Recent developments in rapid thermal processing", *J. Electron. Mater.* 31, 981–987 (2002) (label `[^fiory-2002]`)

<https://doi.org/10.1007/s11664-002-0030-x>

Notes: abstract only — a review of RTP for ultra-shallow junctions and the trend to spike
anneals. Nothing beyond the abstract was read.

## S9 — Agarwal et al., "Reduction of transient diffusion from 1–5 keV Si⁺ ion implantation due to surface annihilation of interstitials", *Appl. Phys. Lett.* 71, 3141 (1997) (label `[^agarwal-1997]`)

<https://doi.org/10.1063/1.120268>

Notes: abstract only — transient enhanced diffusion during the anneal is reduced when the
implant is shallow enough for interstitials to reach the surface.

## S10 — SEMI standard listing, "SEMI MF1241 — Test method for measuring junction depth" (label `[^semi-f1241]`)

<https://store-us.semi.org/products/mf124100-semi-mf1241>

Notes: a store listing for the standard; the abstract names the method. Not read.
