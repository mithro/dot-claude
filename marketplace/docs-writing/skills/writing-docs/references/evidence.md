# Evidence: where the rules come from

Every tradition that has thought about documentation says the same thing in its own words: a page serves one
need, opens with its scope, acts before it explains, verifies as it goes, puts each picture beside its action,
and is owned, versioned and tested like code. The quotes below are from the sources themselves (fetched October
2026); the citations are the pages to read.

## Page types

- **Diátaxis** (Daniele Procida), [diataxis.fr](https://diataxis.fr/start-here/): "there isn't one thing called
  documentation, there are four". "Crossing or blurring the boundaries described in the map is at the heart of a
  vast number of problems in documentation." A how-to "must be written from the perspective of the user, not of
  the machinery"; "action and only action; no digression, explanation, teaching". Titles: "good: How to
  integrate application performance monitoring; bad: Integrating application performance monitoring … very bad:
  Application performance monitoring". Reference "should be austere. One hardly reads reference material; one
  consults it." On structure: "It certainly does not mean that you should create empty structures … Don't do
  that. It's horrible." The talk behind it: ["What nobody tells you about documentation", PyCon AU
  2017](https://pyvideo.org/pycon-au-2017/what-nobody-tells-you-about-documentation.html).
- **Red Hat modular documentation**, [redhat-documentation.github.io/modular-docs](https://redhat-documentation.github.io/modular-docs/):
  procedure modules may contain only Prerequisites / Verification / Troubleshooting / Next steps / Additional
  resources; "Do not change or embellish these subheadings. Do not create additional subheadings." Concept
  modules "Avoid including instructions to perform an action"; "Explain only things that are visible to users."
  "Do not list obvious prerequisites." "Do not use Next steps to provide a second list of instructions."
- **DITA task topic**, [OASIS DITA 1.3](https://docs.oasis-open.org/dita/dita/v1.3/os/part3-all-inclusive/archSpec/technicalContent/dita-task-topic.html):
  prereq, context, steps, result, example, postreq "in the following order"; a step's command "should not be
  more than one sentence"; a step result "should not be used for every step as this quickly becomes tedious".
- **Every Page is Page One** (Mark Baker), [everypageispageone.com](https://everypageispageone.com/the-book/):
  "Because a reader can arrive at an Every Page is Page One topic from anywhere, the topic must establish its
  context." Topics "must link richly along lines of subject affinity."
- **Kubernetes**, [page content types](https://kubernetes.io/docs/contribute/style/page-content-types/): Concept,
  Task, Tutorial, Reference; a task page "has minimal explanation"; "whatsnext" "(5 maximum)".
- **GitLab**, [topic types](https://docs.gitlab.com/development/documentation/topic_types/): no "Pages that are
  exclusively links to other pages", no "Topics that have one or two sentences only"; "If you need more than
  five heading levels, move the topics to a new page"; "try not to use more than 15 links".
- **Hillel Wayne**, [My Problem With the Four-Document Model](https://www.hillelwayne.com/post/problems-with-the-4doc-model/):
  the kinds Diátaxis leaves out (overviews before the tutorial, examples, troubleshooting, best practices),
  each of which needs an explicit home.

## Minimalism

- **Carroll and van der Meij**, [Ten misconceptions about minimalism](https://ris.utwente.nl/ws/files/249663536/Caroll1996ten.pdf):
  "even learners who declare that they are the type of person who reads everything before trying to do
  anything, quickly and spontaneously begin interacting with the system as they read". "Brevity is a key element
  of minimalism, but only because it can facilitate task-oriented activity … not as a self-sufficient end in
  itself."
- **Ginns et al.**, [meta-analysis](https://files.eric.ed.gov/fulltext/ED491708.pdf): the four principles (act,
  anchor in the task, support error recognition and recovery, support reading to do); emphasising error
  recovery gave a weighted mean effect of d = 0.59. Error information is "a characterization of the system state
  to detect and identify the error; conceptual information about its likely cause; and action statements for
  its correction".

## Style and limits

- **GOV.UK**, [writing guidelines](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/):
  "Your title should be 65 characters or less"; "Try to split up sentences that are over 25 words long";
  "Paragraphs should have no more than 5 sentences each"; most people "only read 20 to 28% of text on a
  webpage", "in an 'F' shape pattern"; "Do not use footnotes"; "Do not use FAQs"; "Use numbered steps instead
  of bullet points to guide a user through a process"; "There's usually no need to say 'please' or 'please
  note'". [Why HTML not PDF](https://gds.blog.gov.uk/2018/07/16/why-gov-uk-content-should-be-published-in-html-and-not-pdf/).
- **Google developer documentation style guide**, [developers.google.com/style](https://developers.google.com/style/procedures):
  "use one step for each action"; "State the action first and the result second. Keep the result in the same
  paragraph as the action"; "Don't use notes to tell the reader about prerequisites"; "Don't make a full
  procedural step into a note"; "Avoid tables in the middle of a numbered procedure"; "Don't use directional
  language … above, below, or right-hand side"; the word list bans "easy", "just", "click here", "e.g.",
  "etc.", "currently", "in order to"; [timeless documentation](https://developers.google.com/style/timeless-documentation)
  lists "as of this writing", "currently", "does not yet", "latest", "new", "now", "soon"; "Avoid documenting
  future features or products, even in innocuous ways"; images: "Don't use images of text, code samples, or
  terminal output"; alt text "155 characters or less"; "don't put more than one paragraph's worth of information
  in a single diagram". [Technical writing course](https://developers.google.com/tech-writing/one/documents): "A
  good document begins by defining its scope", "A better document additionally defines its non-scope";
  "Readers generally welcome paragraphs containing three to five sentences"; self-editing: read aloud, set it
  aside, "delete any sections that don't help satisfy the scope statement".
- **Microsoft style guide**, [learn.microsoft.com/style-guide](https://learn.microsoft.com/en-us/style-guide/scannable-content/lists):
  a list "at least two items but … no more than seven"; "Make sure that customers know where the action should
  take place before you describe the action"; "Avoid notes, tips, and important boxes. Readers tend to skip over
  them … limit them to one or two per article"; tables: "Don't leave a cell blank"; alt text "Limit the length
  to 150 characters".
- **Write the Docs**, [documentation principles](https://www.writethedocs.org/guide/writing/docs-principles/):
  "Consider incorrect documentation to be worse than missing documentation"; "Store sources as close as possible
  to the code which they document"; "Eliminate content overlap between separate sources"; link text "should
  surround words that describe the link itself (and never phrases like 'click here')".
- **Django**, [writing documentation](https://docs.djangoproject.com/en/stable/internals/contributing/writing-documentation/):
  "avoid using words that minimize the difficulty involved in a task … 'easily', 'simply', 'just', 'merely',
  'straightforward'"; versionadded/versionchanged blocks instead of version talk in prose.
- **Raspberry Pi style guide**, [style-guide-for-resources](https://github.com/raspberrypilearning/style-guide/blob/master/style-guide-for-resources.md):
  "GPIO 4 (not 'GPIO pin 4', 'pin 4' …)"; bold for "Words printed on a board".

## Pictures and assembly instructions

- **Heiser, Phan, Agrawala, Tversky, Hanrahan**, [Identification and validation of cognitive design principles
  for automated generation of assembly instructions](https://www.tc.columbia.edu/faculty/bt2158/faculty-profile/files/esforautomatedgenerationofassemblyinstructions.pdf)
  (AVI 2004): instructions built on the principles "significantly reduce assembly time an average of 35% and
  error by 50%". The principles: one diagram per major step; explicit order; parts added visible; mode of
  attachment visible; action diagrams rather than structural; arrows for attachment; avoid changing viewpoints;
  stable orientations. On the single exploded view: "Several participants reported they never read the text
  explanations." Low-spatial-ability builders need "more realistic mappings of the diagrams in the instructions
  to the actual pieces (color, 3-D, shading)".
- **Agrawala et al.**, [Designing effective step-by-step assembly instructions](https://www.tc.columbia.edu/faculty/bt2158/faculty-profile/files/signingeffectivestepbystepassemblyinstructions.pdf)
  (SIGGRAPH 2003): "50% for minimum current part visibility, 10% for previous part visibility"; "If the object
  is reoriented, we maintain the reorientation for all subsequent diagrams"; "By default only the first two
  such attachments are shown in detail"; insets for fasteners "much smaller than the other parts".
- **Mayer**, [multimedia principles](https://ugc.futurelearn.com/uploads/files/7d/d6/7dd6188d-c343-4311-b064-ac98d2c95abc/Multimedia_Principles._R._E._Mayer__2020.pdf):
  "People learn better when corresponding words and pictures are presented near rather than far from each other
  on the page or screen"; coherence: "when extraneous material is excluded".
- **iFixit**, [Tech Writing](https://about.ifixit.com/Tech_Writing/chapter/6): "Zoom in to get detailed shots of
  specific actions … provide an intermediate view in addition to the über-zoomed shot"; "Only add markup where
  it is necessary"; "List all screw lengths"; "Reuse prerequisite tasks instead of rewriting them".
- **IKEA**, [Wordless Instructions](https://justinzhuang.com/posts/wordless-instructions/): success is when "a test
  person manages to assemble the product without any written text in the manual"; the booklet opens with "an
  image of what the product looks like when put together successfully". [Desirability Lab](https://desirabilitylab.com/backfill/backfill-2022-03-ikea-assembly-instructions):
  "A sad-face icon on steps where you might make a common error".
- **LEGO**, [BrickNerd](https://bricknerd.com/home/how-lego-instructions-have-changed-over-time-a-forest-of-discovery-10-17-22):
  one viewing angle since 1964; new parts highlighted against de-emphasised earlier ones.
- **Tufte** (via [Boxes and Arrows](https://boxesandarrows.com/three-lessons-from-tufte-special-deliverable-6)):
  "Muting … secondary elements will often reduce visual clutter"; direct labels, not coded keys.

## Keeping docs true

- **Google, Software Engineering at Google, ch. 10**, [abseil.io](https://abseil.io/resources/swe-book/html/ch10.html):
  documentation "should, as much as possible, be treated as code"; "Documents without owners become stale";
  freshness dates; "If something on a landing page is doing more than being a traffic cop, it is not doing its
  job"; "If you want to 'test' whether your documentation works, you should generally have someone else review
  it".
- **Google docguide**, [best practices](https://google.github.io/styleguide/docguide/best_practices.html): "Change
  your documentation in the same CL as the code change"; "Dead docs are bad."
- **GitLab**, [workflow](https://docs.gitlab.com/development/documentation/workflow/): "Documentation forms part of
  the GitLab definition of done"; "Do not promise to deliver features in a future release"; "If a feature slips
  to the next release, the documentation slips too"; [testing](https://docs.gitlab.com/development/documentation/testing/):
  link lint, redirect lint ("deleted or renamed documentation files without redirects"), stale generated
  reference fails.
- **Kubernetes**, [style guide](https://kubernetes.io/docs/contribute/style/style-guide/): "Avoid making promises
  or giving hints about the future"; "Avoid words like 'currently' and 'new'"; [reviewing](https://kubernetes.io/docs/contribute/review/reviewing-prs/):
  review in the rendered preview, "Focus on … the parts of the page that the author is changing"; [content
  guide](https://kubernetes.io/docs/contribute/style/content-guide/): "link to canonical sources instead of
  hosting dual-sourced content".
- **Home Assistant**, [standards](https://developers.home-assistant.io/docs/documenting/standards): "If a feature
  is deprecated, remove the related section … Do not add a deprecation notice."
- **Procida**, [Twelve principles of documentation](https://vurt.eu/articles/principles-documentation/):
  "Duplicated content loses authority. There can be only one source of truth"; "No documentation should be
  created that will not be maintained."
