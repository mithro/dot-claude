# Pictures and diagrams

For a reader holding hardware, the picture is the instruction and the words are labels. The only controlled
experiments on assembly instructions found that instructions built on seven diagram principles cut assembly
time by about 35 % and errors by about 50 %, and that a single exploded view reused across steps was rejected
outright: "several participants reported they never read the text". These rules come from that evidence and
from the practitioners who reach the same place (iFixit, IKEA, LEGO).

## Pictures

1. **Every physical thing named is pictured at first mention**: the whole board first (top and bottom), then
   each variant, connector and part. "Anything which is describing something should include pictures and
   diagrams of that something."
2. **The text beside a picture says the action and the check.** It never narrates the picture ("the blue wire
   runs to the third pin"). The step sentence states the action, which the picture also shows; that redundancy
   is wanted. Alt text (at most 150 characters) says what the picture shows for this step, for the reader who
   cannot see it, and does not start with "Image of".
3. **A render is matched to a photo of the same state before it ships.** A stylised render shows only the
   relevant area, clearer than a photo of a real setup; the photo proves the render is true. Always try to have
   both. Without a photo: an existing project photo, one from the web (with its source and licence recorded),
   or a line drawing, and the wanted photo goes on the list in the pull request.
4. **Find the facts in the pictures before asking anyone.** Where is pin 1, which way is up, which connector is
   which: the maker's photos, schematics and CAD sources show it. If a photo is too low-resolution, find a
   larger one; if none is good enough, render from the CAD source (`kicad-cli` for KiCad). Asking a person what
   a photo could show wastes their attention and leaves a page saying "not checked".
5. **The object is shown as it sits in that step.** The viewpoint changes at most once in a sequence, then
   holds. Pin 1 and the "this way up" cue are in frame.
6. **One colour per item across the page set.** Callout numbers equal the section numbers they point to. Wire
   colours are the real cable's. Labels sit on the pin ("GND"), not in a numbered key: coded labels force eye
   movements that are fatal to comprehension.
7. **Light and dark are one figure** that follows the viewer's theme; print gets the light one. Never offer both
   as links. A drawing made on white paper is a bright slab on a dark theme, so every generated drawing has a
   dark twin from the same palette; a photograph is the same in both.
8. **Terminal output is text, never an image.** A diagram carries one paragraph's worth of information; a
   diagram that needs more than five bullets to explain is two diagrams.
9. **Screenshots of software** only where a control is hard to find, cropped, light theme, no cursor, no
   personal data, and the body text carries every fact the picture shows.

## Step diagrams (assembly, wiring, fitting)

1. **One action diagram per step at a fixed viewpoint.** One diagram reused across steps is wrong. The sanctioned
   reuse is small multiples: the same base drawing re-rendered per step with only the new part and its arrow
   emphasised. Generate the views from one model (the object's geometry, its markers such as pin 1, the
   mating part, the wiring data) by id, so a fix to the model fixes every view.
2. **The part added in the step is at least half visible; earlier parts at least a tenth**, for context; the
   attachment point is unoccluded and the motion is arrowed. Arrows read as action; diagrams without arrows read
   as structure.
3. **A figure about one part highlights that part only.** A look-alike (the neighbouring connector of the same
   kind) appears muted, as the thing not to confuse it with, never highlighted as strongly as the subject.
4. **A crop carries a whole-object inset**, so the reader knows where on the board they are. Every zoomed shot
   gets a context view.
5. **Before and after** where the state changes: the socket empty, then the plug seated. A result picture after
   each major group of steps, not after every step (that becomes tedious).
6. **Small fasteners get an inset.** Repeated identical attachments are shown in full twice, then collapsed.
7. **Mappings are drawn, never tabulated.** Wire-to-cavity, pin-to-pin, which wire goes in which hole: a
   diagram of the housing with the wires drawn in. A table of numbers where a diagram belongs is the fault
   readers complain about first.
8. **Wires cross when everything is connected; that is unavoidable.** A **building** diagram is drawn for
   clarity and ease of making the cable, whatever the real cable does. A **debugging** diagram matches the real
   layout as clearly as that allows. The page says which it shows.
9. **The top-of-page figure's callouts are the page's sections.** An orientation page opens with the whole
   object, then the master picture, then one section per callout, each with its crop.

## The build-guide diagram set

A hardware build guide is a set of diagrams with different jobs, never one wiring sheet reused. At least:

| Slot | Shows |
|---|---|
| 1 | the finished cable or assembly in its installed position |
| 2 | the cable on its own, with its internals: wires, order, colours, connectors |
| 3 | the connectors and what every pin does |
| 4 | the assembly steps, one diagram each |
| 5 | the verification steps: what to measure where |
| 6 | the plugging-in steps |
| 7 | the result after each major group of steps |
| 8 | the wrong configurations and common mistakes (a connector one pin too high, TX and RX swapped): what you see, the likely cause, the fix |

Slot 8 is minimalism's "support error recognition and recovery", the one principle with a measured effect.
IKEA marks error-prone steps with a sad face; the common failure is "reaching step 14 and realising you used
the wrong screw in step 3".

## The figures every physical product gets

| Figure | Shows |
|---|---|
| Whole object | every side the reader will see, photo and render |
| Connectors and controls | each one, with its pin 1 or orientation marker |
| As-laid wiring | the cable as it lies when fitted (the debugging view) |
| How it is driven | the layers kept apart: the protocol, the connection, the tool |
| Variants | the comparison side by side, same orientation and scale, the tell marked |

## Placeholders

A reader page does not carry "figure to come" in normal work. If a site allows placeholders during a rebuild
(*house decision*), a placeholder names the issue tracking the figure, so the gap is visible and owned:

```markdown
:::{admonition} Figure to come
:class: placeholder

The variants side by side, same orientation and scale, the difference marked. Tracked in [issue #123](…).
:::
```

## Checks worth automating

- A bench step with no figure fails the build.
- Missing alt text fails.
- A light drawing without its dark twin, or a light/dark pair outside a theme-switched figure, fails.
- One figure used twice with the same view warns.
- A print of a bench page that splits a step from its picture fails: a paragraph that holds only a picture is
  kept on the sheet of the paragraph before it.
