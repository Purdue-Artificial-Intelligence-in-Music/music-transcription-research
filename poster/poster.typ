#import "@preview/peace-of-posters:0.6.0" as pop
#import "@preview/grayness:0.6.0": image-crop
#import "@preview/cetz:0.3.4"

// ==========================================
// 1. PAGE SETUP & TYPOGRAPHY
// ==========================================
#set page(width: 48in, height: 40in, margin: 1in, fill: white)
#set text(font: "New Computer Modern", size: 28pt, fill: black)

#let box-spacing = 1.2em
#set block(spacing: box-spacing)

// ==========================================
// 2. PURDUE "PRINT-FRIENDLY" COLOR PALETTE
// ==========================================
#let purdue-gold = rgb("#CEB888")
#let purdue-black = rgb("#000000")
#let box-bg = rgb("#FFFFFF")
#let text-dark = rgb("#1E1E1E")
#let stroke-gray = rgb("#D1D1D1")

// ==========================================
// 3. MODERN HEADER-BAND BOX COMPONENT
// ==========================================
#let section-box(title: "", body) = {
  block(
    width: 100%,
    fill: box-bg,
    radius: 12pt,
    stroke: 1.5pt + stroke-gray,
    clip: true,
    stack(
      spacing: 0pt,
      // Header Band
      block(
        width: 100%,
        fill: purdue-gold,
        inset: (x: 30pt, y: 18pt),
        text(size: 34pt, weight: "bold", fill: purdue-black)[#title],
      ),
      // Body
      block(
        width: 100%,
        inset: 30pt,
        [
          #set text(fill: text-dark, size: 31pt)
          #body
        ],
      ),
    ),
  )
}

// ==========================================
// 4. HEADER: TITLE & AUTHORS
// ==========================================
#align(center)[
  #block(width: 100%, inset: (bottom: 0.5in))[
    #grid(
      columns: (1fr, 7fr, 1fr),
      align: (left + horizon, center + horizon, right + horizon),
      align(left + horizon)[#image("figures/Purdue-University-Logo.jpg", width: 100%)],
      stack(
        spacing: 0.8em,
        text(weight: "black", size: 64pt, fill: purdue-black)[
          Addressing Polyphonic Accuracy: Performance Optimizations in Automatic Music Transcription
        ],
        text(size: 34pt, weight: "bold", fill: rgb("#666666"))[
          Ojas Chaturvedi, Kayshav Bhardwaj, Ritwik Jayaraman, Emily Li,
          Shreeya Sarurkar, Sean Su, Elliott Soderberg, Richard Li
        ],
        text(size: 28pt, fill: purdue-black)[
          *Advisors:* Yung-hsiang Lu & Yeon Ji Yun
        ],
      ),
      align(right + horizon)[#image("figures/nsf-logo.jpeg", width: 60%)],
    )
  ]
]

// ==========================================
// 5. MAIN CONTENT (3-COLUMN LAYOUT)
// ==========================================
#grid(
  columns: (1fr, 1.1fr, 1.1fr),
  gutter: 1in,

  // ------------------------------------------
  // COLUMN 1: Context & Problem
  // ------------------------------------------
  stack(
    spacing: box-spacing,

    section-box(title: "What is AMT?")[
      Automatic Music Transcription (AMT) is the computational process of converting raw audio signals into symbolic musical representations like MIDI or digital sheet music.
      #align(center)[
        #image("figures/fourier.png", width: 100%)
      ]
    ],

    v(1fr),

    section-box(title: "Existing Model Outputs")[
      #stack(
        spacing: 1.5em,
        align(center)[#image("figures/issue-complex.png", width: 100%)],

        text(size: 28pt, style: "italic", fill: rgb("#444444"))[
          Although transcriptions differ visually from the original, the audio remains highly accurate despite minor localized errors.
        ],

        v(0.5em),

        grid(
          columns: (auto, 1fr, auto),
          gutter: 1.5em,
          align: horizon,
          stack(
            spacing: 1.5em,
            stack(
              spacing: 0.5em,
              image("figures/original.png", width: 100%),
              align(center)[#text(size: 20pt, weight: "bold")[Original Ode to Joy]],
            ),
            // COOL BACKGROUND for Leakage Text
            block(
              fill: purdue-gold.lighten(90%),
              stroke: 1pt + purdue-gold,
              inset: 15pt,
              radius: 8pt,
              text(size: 30pt)[
                MT3 processes audio in isolated 2s segments. This lack of temporal memory causes *instrument leakage*—the incorrect addition of extraneous instruments or ensembles.
              ],
            ),
          ),
          align(center)[#text(weight: "bold", size: 23pt, fill: purdue-gold)[$arrow.r$ \ MT3 \ Leakage \ $arrow.r$]],
          image("figures/issue-leakage.png", width: 100%),
        ),
      )
    ],

    v(1fr),

    section-box(title: "Acknowledgements")[
      #grid(
        columns: (1fr, 0.25fr),
        gutter: 1.5em,
        align: horizon,
        [
          This research was supported by the Purdue Vertically Integrated Projects (VIP) program and the National Science Foundation (NSF).
        ],
        [
          #set align(center)
          #figure(
            image("figures/qr-code.png", width: 60%),
            caption: [Sources],
            supplement: none,
            numbering: none,
          )
        ],
      )
    ],
  ),

  // ------------------------------------------
  // COLUMN 2: Model Metrics & Evaluation
  // ------------------------------------------
  stack(
    spacing: box-spacing,
    section-box(title: "Model Metrics & Evaluation")[
      #v(0.3em)
      *Comprehensive Performance Benchmarking*
      #v(0.4em)

      #align(center)[
        #table(
          columns: (1.5fr, 1fr, 1fr, 1fr, 1fr),
          inset: 8pt,
          fill: (x, y) => if y == 0 { purdue-gold.lighten(40%) } else { white },
          stroke: 0.5pt + gray,
          [*Model*], [*Mean F*], [*Std Dev*], [*Onset F*], [*Runtime*],
          [Transkun], [*0.636*], [0.181], [*0.985*], [47.0s],
          [Bytedance], [0.570], [0.308], [0.954], [47.6s],
          [Madmom], [0.480], [0.312], [0.846], [152.0s],
          [MT3], [0.303], [0.184], [0.836], [37.7s],
          [Omnizart], [0.265], [0.125], [0.726], [31.1s],
          [Jointist], [0.175], [0.107], [0.755], [37.8s],
          [Basic Pitch], [0.173], [0.119], [0.621], [27.2s],
          [ReconVAT], [0.094], [0.087], [0.455], [*7.8s*],
          [CREPE], [0.008], [0.017], [0.198], [34.0s],
          [MR-MT3], [0.003], [*0.005*], [0.032], [177.6s],
        )
      ]

      #v(0.5em)
      #align(center)[
        #image("figures/f_measure_boxplot.png", width: 100%)
        #text(size: 26pt, style: "italic")[Overall accuracy distribution.]
      ]

      #v(0.8em)

      #v(1fr)

      #v(0.5em)
      #align(center)[
        #image("figures/onset_offset_comparison.png", width: 85%)
        #text(size: 26pt, style: "italic")[Note Detection Error Gap]
      ]

      #v(1fr)

      #grid(
        columns: (1.2fr, 2fr),
        gutter: 1.5em,
        align: horizon,
        block(
          fill: stroke-gray.lighten(80%),
          inset: 12pt,
          radius: 4pt,
          width: 100%,
          text(size: 28pt)[
            *Analysis:* While Onset detection (Fig 3) is robust across top models, the dramatic drop in Offset accuracy and performance in Polyphonic scenarios (Fig 2) highlights the current limitations in temporal modeling.
          ],
        ),
        stack(
          spacing: 0.5em,
          align(center)[
            #image("figures/polyphony_slope.png", width: 100%)
            #text(size: 26pt, style: "italic")[Polyphony Penalty]
          ],
        ),
      )
    ],
  ),

  // ------------------------------------------
  // COLUMN 3: Complexity & Interpretability
  // ------------------------------------------
  stack(
    spacing: box-spacing,

    section-box(title: "The Complexity Bottleneck")[
      In reference to the evaluation framework for music transcription models and in order to further improve raw performance, it is relevant to objectively measure the complexity of a piece.

      - These "black-boxed" models make it difficult to interpret how results are derived.
      - We focus on a subdivision known as *polyphony* and its metric: measure of the average number of notes played simultaneously.
        - We propose that the more complex a piece is, the more difficult it is for models to transcribe.
        - Correlation between specific metrics and accuracy gives insights into features impacting model performance.

      #let plot-box(img-path, title, corr) = [
        #align(center)[
          #stack(
            spacing: 0.5em,
            text(weight: "bold", size: 24pt)[#title],
            image-crop(read(img-path, encoding: none), crop-width: 800, crop-height: 800, width: 110%),
            text(size: 23pt)[Spearman \ #corr],
          )
        ]
      ]

      #v(1em)
      #align(center)[
        #grid(
          columns: (auto, 1fr, 1fr, 1fr),
          gutter: 0.5in,
          rotate(-90deg, reflow: true)[*Multi-instrument*],
          plot-box("figures/hexbin_AAM_BP.png", "Basic Pitch", "-0.2259**"),
          plot-box("figures/hexbin_AAM_MT3.png", "MT3", "-0.0813**"),
          plot-box("figures/hexbin_AAM_ReconVAT.png", "ReconVAT", "-0.1581**"),

          rotate(-90deg, reflow: true)[*Piano only*],
          plot-box("figures/hexbin_POP909_CREPE.png", "CREPE", "-0.2283**"),
          plot-box("figures/hexbin_POP909_MT3.png", "MT3", "-0.1346**"),
          plot-box("figures/hexbin_POP909_Transkun.png", "Transkun", "-0.1881**"),
        )
      ]
      #align(right)[* \*\*p < 0.001*]
    ],

    v(1fr),

    section-box(title: "Mechanistic Interpretability")[
      #stack(
        spacing: 1.2em,
        grid(
          columns: (auto, 1fr),
          gutter: 1.5em,
          align: horizon,
          align(center)[
            #cetz.canvas(length: 1cm, {
              import cetz.draw: *
              let w = 5.7
              let gap = 1.0
              let bw = 3.5
              let h = 4.2
              rect((0, 0), (w, h), name: "input", stroke: 1.5pt + text-dark, fill: white)
              content("input.center", stack(spacing: 0.2em, align(center)[*INPUT*], align(center)[#text(
                size: 36pt,
              )[🎙️]]))
              line((w + 0.1, h / 2), (w + gap - 0.1, h / 2), mark: (end: ">", fill: text-dark), stroke: 3pt + text-dark)
              let bx = w + gap
              rect((bx, 0), (bx + bw, h), name: "bbox", fill: purdue-black, stroke: none, radius: 0.3)
              let cx = bx + bw / 2
              let cy = h / 2
              content((cx - 0.2, cy + 0.2), text(fill: white, size: 40pt, weight: "bold")[?])
              circle((cx - 0.2, cy + 0.2), radius: 0.8, stroke: 3pt + white)
              line((cx + 0.3, cy - 0.3), (cx + 1.1, cy - 1.1), stroke: (paint: white, thickness: 6pt, cap: "round"))
              line(
                (bx + bw + 0.1, h / 2),
                (bx + bw + gap - 0.1, h / 2),
                mark: (end: ">", fill: text-dark),
                stroke: 3pt + text-dark,
              )
              let ox = bx + bw + gap
              rect((ox, 0), (ox + w, h), name: "output", stroke: 1.5pt + text-dark, fill: white)
              content("output.center", stack(spacing: 0.2em, align(center)[*OUTPUT*], align(center)[#text(
                size: 36pt,
              )[🎵]]))
            })
          ],
          [
            *What is interpretability?*
            - Current models are "black boxes"
            - We don't know what they "learn"
            - Errors are difficult to isolate and fix
            - The "overfitting" problem
          ],
        ),
        v(1.5em),
        block(
          width: 100%,
          fill: purdue-gold.lighten(85%),
          inset: 1em,
          radius: 0.5em,
          [*Our goal:* Build an interpretable AMT model approaching SoTA accuracy with higher transparency. Look inside to see why it does what it does.],
        ),
        v(1.5em),
        grid(
          columns: (auto, 1fr),
          gutter: 1.5em,
          align: horizon,
          align(center)[
            #cetz.canvas(length: 1cm, {
              import cetz.draw: *
              let w = 8.0
              let h = 4
              let gap = 1.0
              let vgap = 0.5
              let top_y = h + vgap
              rect(
                (0, top_y),
                (w, top_y + h),
                name: "V",
                radius: 0.2,
                stroke: 2pt + purdue-gold,
                fill: purdue-gold.lighten(80%),
              )
              content("V.center", [*V* \ (Spectrogram)])
              content((w + gap / 2, top_y + h / 2), text(size: 40pt, weight: "bold")[$=$])
              rect(
                (0, 0),
                (w, h),
                name: "W",
                radius: 0.2,
                stroke: 2pt + rgb("#4A90E2"),
                fill: rgb("#4A90E2").lighten(85%),
              )
              content("W.center", [*W* \ (Dictionary)])
              content((w + gap / 2, h / 2), text(size: 40pt, weight: "bold")[$times$])
              rect(
                (w + gap, 0),
                (w * 2 + gap, h),
                name: "H",
                radius: 0.2,
                stroke: 2pt + rgb("#50E3C2"),
                fill: rgb("#50E3C2").lighten(85%),
              )
              content("H.center", [*H* \ (Activations)])
            })
          ],
          [
            *Planned DDS architecture*
            - Differentiable Dictionary Search
            - Dictionary of possible "notes"
            - Predicted linear sum of bases
          ],
        ),
      )
    ],
  ),
)
