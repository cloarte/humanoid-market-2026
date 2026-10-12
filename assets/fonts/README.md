# Fonts

Bundled so that every chart renders identically on any machine.

| file | family | source | license |
|---|---|---|---|
| `Inter-Regular.ttf`, `Inter-SemiBold.ttf`, `Inter-Bold.ttf` | Inter | static instances (weights 400, 600, 700) of `Inter[opsz,wght].ttf` from [google/fonts](https://github.com/google/fonts/tree/main/ofl/inter) | SIL Open Font License 1.1 (`OFL-Inter.txt`) |
| `SourceSerif4-Italic.ttf` | Source Serif 4 | static instance (weight 400, optical size 20) of `SourceSerif4-Italic[opsz,wght].ttf` from [google/fonts](https://github.com/google/fonts/tree/main/ofl/sourceserif4) | SIL Open Font License 1.1 (`OFL-SourceSerif4.txt`) |

Static instances were generated with fontTools 4.66.1
(`fontTools.varLib.instancer.instantiateVariableFont`, `updateFontNames=True`) because
matplotlib does not select weights inside variable fonts.
