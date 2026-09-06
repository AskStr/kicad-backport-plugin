# Official KiCad schema snapshots

Unmodified official distribution files captured on **2026-09-06**:
PCM v1 from KiCad **6.0.11**, PCM v2 and API v1 from **10.0.4**.
The latter two also match installed **10.99.0-2335-g1899bad41c** byte-for-byte.

| File | SHA-256 |
|---|---|
| `pcm.v1.schema.json` | `c11de0c4432cb63c88c55a54f2b5830b54bdd81d86d5eeb84149fa475f886bcb` |
| `pcm.v2.schema.json` | `74bfb8fca2abdcf619afd152f57bcc768c855541587e21b81e2c6e8fd3b8abb2` |
| `api.v1.schema.json` | `a51ecc9cc4166fc857a0378b6361909c66a7957451146bd50123d52313fdea96` |

Schema IDs are recorded inside each file. Official upstream source locations:

- PCM: `https://gitlab.com/kicad/addons/metadata/-/blob/main/schema-v2.json`
- API: `https://github.com/KiCad/kicad-source-mirror/blob/10.0.4/api/schemas/api.v1.schema.json`
- KiCad licensing: `https://github.com/KiCad/kicad-source-mirror/blob/10.0.4/LICENSE`

These files retain their upstream licensing terms; they are not relicensed under this
plugin's MIT license. They are build/test inputs, not shipped in the runtime ZIP.
The CoilForge 0.2.8 distribution design informed this implementation; no CoilForge
GPL runtime or packaging source has been copied into this MIT plugin.

To update: obtain a specific official release, replace without editing, record release
and hashes, run `python -m unittest discover -s tests -v`, build the PCM ZIP, and
repeat native installation/update checks. Schema validation alone does not prove runtime
compatibility: safe relative resources, version consistency and archive layout are
checked separately by the release tools.
