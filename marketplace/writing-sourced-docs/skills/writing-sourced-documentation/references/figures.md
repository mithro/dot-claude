# Figures

## Generated, never drawn

Every diagram is generated from a short declarative spec (YAML) by one generator in one
style; no SVG is written or edited by hand, and the reader-facing "Figure conventions" page
is generated from the same token file, so the legend cannot drift from the drawings. Colours,
type scale, spacing and stroke widths live in one tokens file; no value of that kind appears
in the generator. Each figure is written three times — one file following the operating
system's light/dark setting and two forced files a small script swaps in when the reader
uses the page's theme switch — and paints its own ground.

Why: hand-drawn figures accumulate inconsistencies, cannot be linted, and say things the
page does not. A spec can be checked against the page.

## A figure may never say more than its page does

This is the main risk: pages hedge, drawings do not unless the style supplies the hedge.

* Every label carries `basis: public | reading | inferred | typical`; anything other than
  public prints its tag in the hedge colour, and the caption repeats the same hedge in words.
* Every label note containing a number carries `cite:`, and that footnote key must already be
  defined on the target page; the lint opens the page to check.
* A dimension that is not public is never drawn to scale, and its label says "not public"
  first and the reading second.
* Nothing taken from restricted content (in the worked example, a patent shown as in force)
  appears in a figure, in any form, because a figure cannot sit inside a collapsed note. A
  checker hook screens every figure's text.
* A figure may show a value the page gives as its own reading, always tagged "our reading",
  the hedge repeated in the caption.
* The figure is additive: no sentence is deleted because a drawing now shows it. A figure
  never replaces text or a table and is always followed by prose.

## Cross-sections

* Two panels, before and after, cut at the same place for every figure of one module, so a
  feature keeps its position from page to page. One panel for a step with nothing before it or
  one that changes nothing the drawing can show (titled "State at this step (no drawn
  change)", the step's effect in the caption). Three panels only for a deposit → pattern →
  etch summary on a category page.
* **One accent colour marks the one thing the step did and nothing else**: the arrow between
  the panels, the ion arrows of an implant, a thin trace just clear of the surface the step
  made.
* **Not to scale**, printed in the figure's corner and again in the caption: thin films are
  drawn far thicker than they are or they would be invisible. A chart that is to scale says
  "To scale" and carries an axis with units.
* Colour is never the only channel: each material also carries an outline, a pattern and a
  label. A palette report checks colour-vision contrast.
* Layers the step does not touch may be drawn faded (dashed outline, no fill at full scale;
  their own fill inside the outline in a close-up, where an empty film reads as a void); the
  caption names every faded layer.

## Text, labels and leaders

Text never sits on top of a drawing. Material labels stand in a column to the right, in layer
order, joined to their layer by a thin leader ending in a dot on the layer itself; each leader
runs down a track of its own. Open-at-the-top features (a trench, a hole, a polished surface,
an ion beam) are labelled from a band above the drawing, at most two per panel. A leader never
crosses another, never crosses text, never runs alongside a film edge where it could be read
as one; where it must cross a material it gets a halo in the page colour. Budgets are numbers
and lint rules: label title ≤ 30 characters, note ≤ 90, arrow note ≤ 130, panel title ≤ 110,
labels carrying a note ≤ 3 per panel, labelled layers ≤ 6 per panel, whole figure ≤ 800 units
tall. Split the figure when the step changes more than one thing, or use a stack chart when
there are more films than the label budget allows. The generator never shortens a note (a
truncated note could drop a hedge); an over-long note is an error you fix in the spec.

## Alt text and captions

* Alt text: 60–450 characters describing the **geometry** — what a reader who cannot see the
  picture needs — with no citations, no codes to look up, no interpretation.
* Caption: what is shown · the page's hedges repeated · the citations · "Not to scale." A
  close-up says "close-up of …" and how much it is enlarged; a cut slice says where the drawing
  starts and that the lower part is cut off.

## Authoring procedure

1. Read the target page in full, noting which statements are fact, reading, inference or
   typical practice, which numbers it gives with which footnote key, and where it says
   something is not public.
2. Copy the nearest existing spec; set the page, series, the two state values, panel titles,
   arrow text, alt text and caption, using only wording already on the page.
3. Run the generator, fix every `LINT:` line, then **look at the rendered result** on the
   harness pages at desktop and phone width before pasting anything.
4. Paste the generated block after the first paragraph of the section the page type names.
   Any new H3 goes after the caption, never between the lead and the figure.
5. Run the generator's `--check` (every committed SVG, paste block and the conventions page
   match the specs) before committing; commit the spec and the regenerated outputs separately.

## Other figure kinds

* **Flow strip**: modules to scale by step count, bracketed by phase, fanning out to one row
  per module; placed directly above the module table and repeating only its facts.
* **Block chain** (a machine's subsystems): only the blocks the cited text names, in its order;
  no pictorial tool drawings, which would assert geometry no source supports.
* **Derivation chain** (an artefact such as a mask or a generated schema): source data →
  intermediate records → the steps that use it, with inferred links tagged.
* **Stack chart**, to scale, with an axis, where every number already cites the stack drawing.
