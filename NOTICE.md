# Provenance and licensing

New Kaypro code is Copyright (c) 2026 Danila Sukharev, MIT licensed.
The platform loader, BIOS and build/media tools derive from
[ cpm-plus-1715 ](https://github.com/ddanila/cpm-plus-1715) commit
`86e787d1e98ce9ae6e0cc1c4acfa70b91aa5f70f` (MIT).
Its BIOS glue, regeneration script and tool recipes in turn derive from
cpm-plus-juku commit `61b2d5397589e794c0381aa836b7a0da2217e6c8`;
the BSD-2-Clause terms are retained in `third_party/JUKU-LICENSE`.

Shared serial console and NetDisk sources are included directly from the
juku-common submodule, pinned to `34a9b0f5842b2ae8162f37c6037a9cfbedf050ed`.
Their original notices and licenses remain in that submodule.
Digital Research CP/M, tools and derivatives retain the distribution grant
in `third_party/cpm3/LICENSE.md`; the root MIT license does not replace it.
Source and binary archives are pinned in `third_party/inputs.json`.
Zmac retains its original source notices (public-domain and GPL components).
ZXCC 0.5.7 retains the GPL notices in its unmodified source archive. These
are host build tools, not guest BIOS code.

No historical Kaypro ROM, character generator or keyboard firmware is
included. MAME (BSD-3-Clause) and published schematics were consulted as
independent references; no MAME source is copied into this project.
