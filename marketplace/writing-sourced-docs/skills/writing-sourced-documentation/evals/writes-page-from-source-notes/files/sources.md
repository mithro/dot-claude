# Source notes for step 110 WDEP1 — tungsten plug deposition

TEST FIXTURE. These are a researcher's notes of what each fetched source says. The
excerpts are illustrative and are the ONLY material that may be cited for this page.
Nothing not recorded here may be stated as a fact about the process or about SkyWater.

## S1 — the step list (inventory key STEPS-SHEET, label `[^steps-sheet]`)

*S8 / SKY130 Process Steps*, public Google Sheet, tab "Sheet1", retrieved 2026-09-14.
<https://docs.google.com/spreadsheets/d/1PbI3IVNg93fR9Gi_hXlEDrlYtwFQuMyaD8PNEaIs3Sg>

Row 110: code `WDEP1`, description "W deposition 1". Row 109: `TIN2`, "IMP TiN
deposition". Row 111: `WCMP1`, "W CMP 1". The sheet records only the step number, code
and description — nothing about films, thicknesses, chemistries, tools or conditions.

## S2 — Wikipedia, *Tungsten hexafluoride* (label `[^wiki-wf6]`)

<https://en.wikipedia.org/wiki/Tungsten_hexafluoride>

Notes: WF₆ is "the main source of tungsten in the semiconductor industry" for CVD
tungsten. It is reduced by hydrogen: WF₆ + 3 H₂ → W + 6 HF. It is also reduced by
silane; the silane reduction is used to nucleate a thin film before the hydrogen
reduction. WF₆ "reacts with silicon", which is why a barrier is needed between the
tungsten and silicon or titanium. No numbers recorded.

## S3 — Wolf and Tauber, *Silicon Processing for the VLSI Era*, vol. 1, 2nd ed., Lattice Press, 2000, ISBN 978-0-9616721-6-4 (inventory key TXT-02, label `[^txt-02]`)

<https://openlibrary.org/isbn/9780961672164>

Notes from the CVD tungsten chapter (table of contents checked; chapter read in part):
typical blanket CVD tungsten for plug fill runs at substrate temperatures of about
400–450 °C and pressures of tens of Torr; the hydrogen reduction gives near-conformal
step coverage, which is what lets it fill holes from the walls inward; a seam or void can
remain on the axis of a hole when the walls close before the bottom fills; the usual
sequence is a silane-reduced nucleation layer, then the bulk hydrogen-reduced film. The
chapter calls tungsten's adhesion to silicon dioxide "poor", the reason for the
Ti/TiN adhesion and barrier layer underneath. Numbers are the textbook's typical values,
not any one fab's.

## S4 — SkyWater Technology, *Facilities & Capabilities* page, accessed 2026-08-30 (inventory key SKW-01, label `[^skw-01]`)

<https://www.skywatertechnology.com/manufacturing/facilities-capabilities/>

Under "Film Deposition" the page lists, verbatim: "AMAT W CVD" with the sub-entry
"Tungsten plug fill, blanket W". It also lists "AMAT PVD Metal" with sub-entries
including "Imp TiN" and "Collimated Ti". It does not name a platform, a model, a
chamber count, a recipe or a step.

## S5 — Applied Materials, *Centura WxZ* product page, Wayback Machine capture of 2001-03-02 (label `[^amat-wxz-2001]`)

Original URL `http://www.appliedmaterials.com/products/wxz.html` is dead (checked
2026-09-16 and 2026-09-18, HTTP 404). Archive copy:
<https://web.archive.org/web/20010302091200/http://www.appliedmaterials.com/products/wxz.html>

Notes: describes the WxZ chamber as a single-wafer CVD tungsten chamber on the Centura
platform "for plug fill and blanket tungsten"; says the chamber performs "nucleation and
bulk deposition in the same chamber"; quotes a film resistivity of "below 10 μΩ·cm" for
the bulk film. No date of introduction is given on the page.

## S6 — Novellus Systems, *Altus* product page, Wayback Machine capture of 2002-06-10 (label `[^novellus-altus-2002]`)

<https://web.archive.org/web/20020610142541/http://www.novellus.com/products/altus.asp>

Notes: the Altus is described as a multi-station sequential-deposition tungsten CVD
system for 200 mm wafers, "five stations" per module; claims "void-free fill of
contacts and vias at aspect ratios above 5:1"; names the process gases as "WF₆, SiH₄,
H₂, N₂ and Ar". No year of introduction recorded.

## S7 — SkyWater job listing, "Thin Films Process Engineer", retrieved 2026-09-02 from a job board (label `[^skw-job-tf]`)

<https://www.example-jobboard.com/skywater/thin-films-process-engineer-20260902>

Notes: the posting asks for experience with "CVD tungsten (Applied Materials Centura)
and PVD barrier films". This is the only public source naming the Centura platform at
SkyWater. Job postings change and expire; cite with the retrieval date. Evidence
strength on the inventory's scale: medium.

## S8 — SkyWater PDK Authors, *metal_stack.svg* process stack diagram (inventory key PDK-04, label `[^pdk-04]`)

<https://raw.githubusercontent.com/google/skywater-pdk/main/docs/_static/metal_stack.svg>

Notes: the drawing labels the contact level `mcon` and places it between the local
interconnect `li1` and `met1`; it carries the text "(Diagram not to scale!)". It gives a
`met1` bottom of 1.3761 µm and an `li1` top of 1.0361 µm above its zero line (our
reading of the drawing's labels; the drawing does not state the contact height as a
number of its own). It does not name the contact fill material.

## S9 — Wikipedia, *Chemical mechanical planarization* (label `[^wiki-cmp]`)

<https://en.wikipedia.org/wiki/Chemical_mechanical_planarization>

Notes: CMP removes the overburden of a blanket film and leaves the plugs flush with the
surrounding dielectric; this is the usual alternative to a plasma etch-back for tungsten
plugs.

## S10 — Broadbent and Ramiller, "Selective low pressure chemical vapor deposition of tungsten", *J. Electrochem. Soc.* 131, 1427 (1984) (label `[^broadbent-1984]`)

<https://doi.org/10.1149/1.2115868>

Notes: abstract only. Early paper on selective tungsten CVD from WF₆; reports selective
deposition on silicon and not on oxide. Nothing beyond the abstract was read.

## S11 — Lam Research press release, "Lam Research completes acquisition of Novellus Systems", 2012-06-04 (label `[^lam-novellus-2012]`)

<https://investor.lamresearch.com/news-releases/news-release-details/lam-research-completes-acquisition-novellus-systems>

Notes: Novellus became part of Lam Research in June 2012; the Altus product line
continued under Lam.
