# Python Conversion Port Status

This document tracks the Python plugin core against the reference implementation
in `E:\WORKS\MY\kicadProject\kicad-backport-cplus`.

## Implemented in this slice

- Target aliases now include raw development targets `20260521` / `20260603`
  plus `4.0`, `5.0`, `5.1`, `6.0`, `7.0`, `8.0`, `9.0`, `10.0`, and
  `10.99`. The raw development targets apply to PCB/footprint file formats;
  schematic, symbol-library, worksheet, and design-rule files use the matching
  KiCad 10.99 family format versions.
- The converter distinguishes downgrade, same-version copy, and upgrade flows.
- Basic upgrade rules are applied for S-expression PCB, footprint, schematic,
  and symbol-library documents instead of copying lower-version files unchanged.
- KiCad 5-family output routing now maps modern `.kicad_sch` to `.sch`,
  `.kicad_sym` to `.lib` plus `.dcm`, and `.kicad_pro` to `.pro`.
- The wx and tkinter plugin file pickers now expose legacy `.sch`, `.lib`,
  `.dcm`, and `.pro` files through the same shared KiCad input extension list
  used by automatic input detection.
- Symbol-library downgrade now writes legacy `.lib` symbol records with
  `DEF`, `ALIAS`, `F0`-`F3`, custom `F4+`, `DRAW`, and `X` pin records for supported
  primitives, and writes `.dcm` sidecars from `Description`, `ki_keywords`,
  and `Datasheet` properties. Top-level `pin_numbers` / `pin_names` hide
  nodes are preserved as legacy `DEF` `N` visibility fields, and common pin
  shapes, pin-level hide flags, and pin name/number text sizes are preserved in
  legacy `X` fields. Nested unit sub-symbols named with `_unit_convert`
  suffixes now drive legacy `DEF` unit counts and DRAW/X unit/convert fields.
  Symbol DRAW text font sizes and bold/italic font styles are preserved in
  legacy `T` records, and filled rectangle/polyline/circle/arc DRAW primitives
  preserve legacy fill flags.
- Schematic downgrade now writes legacy `.sch` page metadata, `LIBS` entries,
  wire/bus/bus-entry records, junction/no-connect records, labels/text,
  directive/netclass labels as visible Notes text, Notes polyline records,
  rectangle/circle/arc/bezier-to-Notes-line approximations,
  text-box-to-Notes-text/line approximations, `$Sheet` records, and `$Comp`
  symbol records for common S-expression schematic objects, including KiCad 5
  `$Comp` transform matrices for right-angle symbol rotations and `mirror x` /
  `mirror y` placements. Schematic text and label font sizes are preserved in
  legacy `Text` records, and placed-symbol property font sizes / hidden flags
  are preserved in legacy `$Comp` `F` records, including user custom `F4+`
  fields. Sheet name/file fields and sheet pin fields preserve their legacy
  font sizes. Multi-point schematic polylines are downgraded to one legacy
  Notes line per adjacent point pair instead of losing segments after the first
  pair.
- Legacy `.lib` plus paired `.dcm` upgrade now writes real `.kicad_sym`
  records for `DEF`, `F0`-`F3`, custom `F4+`, `ALIAS`, `DRAW`
  rectangle/polyline/circle/arc/text records, and `X` pins, including common pin
  shapes, pin-level hide flags, and pin name/number text sizes, plus merged
  description, keyword, and datasheet properties from `$CMP` documentation
  blocks. Legacy DRAW text sizes and bold/italic styles are mapped to modern
  text font effects, using KiCad 8+ boolean style lists for newer targets, and
  legacy DRAW fill flags round-trip through modern fill nodes.
  Standalone `.dcm` files can also be upgraded into documentation-only
  symbol-library shells.
- Legacy `.lib` text `T` DRAW records now preserve the legacy text angle value
  during upgrade, matching the C++ reference path for rotated symbol text.
- Legacy `.lib` reference prefix parsing now preserves `#...` power-style
  prefixes such as `#PWR`, matching the C++ reference instead of falling back to
  an alphabetic prefix from the symbol name.
- Legacy `.lib` DEF pin-number and pin-name visibility flags now upgrade to
  `(pin_numbers hide)` / `(pin_names hide)` nodes when the legacy fields are
  disabled.
- Legacy `.lib`, standalone `.dcm`, and legacy `.sch` upgrade writers now emit
  `(generator kicad-backport)` with the same unquoted generator atom used by the
  C++ reference implementation.
- Legacy `.sch` upgrade now writes common `.kicad_sch` records for page
  metadata, title blocks, wires, buses, bus entries, junctions, no-connects,
  labels/text, Notes line polylines, hierarchical sheets and sheet pins,
  components, symbol properties, AR instance paths, `sheet_instances`, and
  `symbol_instances`. Legacy schematic `Text` record font sizes are mapped to
  modern text/label effects, and GLabel/HLabel shape parsing now reads the
  post-size shape field instead of mistaking the size field for the shape.
  Legacy `$Comp` `F` record font sizes and hidden flags are also mapped to
  placed-symbol property effects, including user custom `F4+` fields. Legacy
  `$Sheet` field and sheet-pin font sizes are mapped to modern effects, and
  sheet-pin `R/L/U/D` directions now upgrade through the pin-orientation
  mapping.
- Legacy `.sch` upgrade now also reads `LIBS:`-referenced local `.lib` /
  `<schematic>-cache.lib` symbol caches to restore library-qualified `lib_id`
  values for KiCad 5-era schematics whose `L` records omit the library
  nickname. V6 schematic targets additionally receive placed-symbol pin UUID
  blocks; V7 targets omit those blocks to preserve KiCad 7 CLI load/export
  compatibility while relying on generated project-local symbol libraries for
  pin definitions.
- Legacy `.sch` upgrade now matches the C++ reference normalization for hidden
  power references by using the cache/library symbol reference prefix when
  converting `#U...` records such as power symbols to `#PWR...` or `#FLG...`.
- Legacy `.sch` upgrade now also treats any component reference containing `?`
  as unannotated, matching the C++ parser, so AR instance `Ref=` values can
  replace forms such as `U?A` during upgrade.
- Legacy `.pro` upgrade now writes minimal KiCad 6+ `.kicad_pro` JSON while
  preserving legacy `project_settings` and `LibName*` symbol-library names.
  Modern `.kicad_pro` downgrade now writes `.pro` settings and restores library
  names from JSON, `sym-lib-table`, or local `.kicad_sym` stems.
- Project conversion now normalizes local `sym-lib-table` and `fp-lib-table`
  files for legacy targets, including removing table `version` nodes, mapping
  V5 symbol tables to `Legacy` `.lib` entries, and adding project-local
  footprint aliases for `Library.pretty` references.
- Project conversion for V6+ targets now writes project-local `sym-lib-table`
  entries for generated `.kicad_sym` libraries and embeds matching generated
  symbols into schematic `lib_symbols` so converted schematics can be opened as
  standalone project files.
- V6+ project conversion now rebuilds root schematic `sheet_instances` and
  `symbol_instances` across hierarchical child `.kicad_sch` files, preserving
  existing sheet pages and uniquifying repeated symbol instance references.
- PCB downgrade to KiCad 5 now converts modern board headers to legacy
  `host/page` syntax, maps modern `User.*` layer names to fixed KiCad 5 user
  layers, removes unsupported keepout zones and setup stackup blocks, and
  renames PCB `footprint` nodes to KiCad 5 `module` nodes.
- PCB/footprint graphical stroke blocks now downgrade to legacy `width` fields
  for KiCad 7/5-era parsers.
- KiCad 5 PCB downgrade now converts `gr_rect` and `fp_rect` into legacy
  `gr_line` / `fp_line` segment outlines, preserving layer, width, and tstamp
  where available.
- KiCad 5 PCB downgrade now preserves solid filled copper `gr_rect` items with
  net connectivity by converting them into legacy `zone` records with matching
  polygon and cached fill geometry, rather than losing the fill as line
  segments.
- KiCad 5 PCB downgrade now converts modern midpoint `gr_arc` / `fp_arc`
  geometry into legacy center-start-end plus `angle` syntax.
- KiCad 5 PCB downgrade now approximates modern track `(arc ...)` routing
  items with legacy `(segment ...)` records, preserving width, layer, and net.
- KiCad 5 PCB downgrade now splits multilayer zones into single-layer legacy
  zones and removes cached `filled_polygon` layer selectors after filtering
  layer-specific fills. It preserves legacy zone `net_name` fields while
  converting named net references to numeric netcodes, and removes
  `filled_areas_thickness` fields for KiCad 5 compatibility.
- KiCad 4 PCB/footprint downgrade now converts 3D model
  `(offset (xyz ...))` millimeter values to legacy `(at (xyz ...))` inch
  values.
- Legacy PCB downgrade now unquotes `uuid` / `tstamp` / `id` atom values for
  older PCB parsers, matching the C++ rewriter behavior.
- KiCad 5 PCB downgrade now removes remaining footprint/module
  `property` / `attr` / `group` / embedded footprint `zone` metadata, footprint
  text IDs, footprint net-tie/unit grouping fields, legacy-incompatible attr
  flags, layer `knockout` flags, and pad/zone thermal bridge angle fields.
  Footprint `Reference` / `Value` properties are downgraded to legacy
  `fp_text` records, including effects-based hidden state as top-level legacy
  `hide` atoms.
- KiCad 4 PCB/footprint downgrade now simplifies custom and rounded pads to
  rectangular pads and removes custom pad `primitives`, `options`, and
  `roundrect_rratio` data.
- Legacy PCB/footprint upgrade now converts legacy `gr_arc` / `fp_arc`
  center/start plus `angle` syntax into modern start/mid/end arcs, and removes
  legacy `angle` fields from graphic lines.
- Board downgrade now removes legacy-incompatible
  `setup/allow_soldermask_bridges_in_footprints` fields for targets before
  KiCad 8-era PCB syntax; this was verified against the real DAT2USBEXP V7
  fixture during Python smoke validation.
- KiCad 5 PCB downgrade now removes additional C++-matched parser-incompatible
  fields: graphic shape `fill` on circle/poly shapes, via `free`, 3D model
  `opacity`, older pad metadata (`pinfunction`, `pintype`, pad `property`,
  pad IDs, chamfer fields, simulation electrical type), and KiCad 4 netclass /
  zone keepout leftovers at their corresponding legacy cutoffs.
- Pad/zone `thermal_bridge_width` is now renamed to legacy `thermal_width` for
  KiCad 7-and-older PCB syntax, matching the C++ downgrade rule and the KiCad 5
  parser expectation seen in the DAT2USBEXP fixture.
- Zone downgrade now removes legacy-incompatible zone `attr` and KiCad 5
  unsupported fill `island_removal_mode` / `island_area_min` fields.
- Legacy PCB downgrade now removes bare `locked` atoms from board item records
  before KiCad 7-and-older output; this was required by the real V6
  Bob_Graphics -> V5 loader smoke.
- KiCad 8-era PCB downgrade now maps teardrop `curved_edges` booleans to
  legacy numeric `curve_points` and removes pre-8 `legacy_teardrops` flags,
  matching the C++ rules for older targets.
- PCB downgrade now removes C++-matched text render caches, table-cell
  `knockout` flags, and KiCad 5 zone `name` fields.
- KiCad 7-and-older PCB dimension downgrade now matches the C++ graphics
  fallback for aligned, orthogonal, radial, and leader-style modern dimensions:
  dimensions are replaced with legacy `gr_text` plus generated `gr_line`
  annotations. `scripts/compat_smoke.py` covers orthogonal and leader cases,
  and `scripts/kicad5_board_load_smoke.py` verifies a converted leader
  dimension board with KiCad 5 `pcbnew.LoadBoard()`.
- KiCad 6 schematic/symbol downgrade now matches the C++ compatibility cleanup
  for text `hyperlink`, placed-symbol `dnp`, `directive_label` to
  `netclass_flag`, pin `hide` / `alternate`, UUID atom unquoting, standard
  property IDs, sheet property name/id normalization, and single-file
  `symbol_instances` regeneration.
- Modern schematic downgrade now removes placed-symbol `(pin ... (uuid ...))`
  blocks for KiCad 7 targets while retaining them for KiCad 6 targets. This
  matches the existing KiCad 7 CLI compatibility strategy used by the legacy
  `.sch` upgrade path.
- The Python downgrade rule warning set now matches the current C++ rules for
  the compared downgrade/upgrade branches, including symbol-library
  `exclude_from_sim`, V7-era `gr_rect` / `fp_rect` net cleanup, KiCad 5 zone
  `filled_areas_thickness`, and generated dimension stroke cleanup.
- V6/V7/V8 `.kicad_prl` compatibility files now use legacy numeric visible
  item IDs, normalized visible-layer masks, and meta version `3`.
- Core Python sources parse as Python 3.6 syntax so KiCad 5-era Python 3
  runtimes do not fail on modern type-hint syntax at import time.
- The legacy ActionPlugin entrypoint now imports under the local KiCad 5.0
  bundled Python 2.7 runtime and delegates the Python 3 GUI/core to an external
  Python 3 interpreter (`KICAD_BACKPORT_PYTHON`, `py -3`, `python3`, then
  `python`).
- `scripts/compat_smoke.py` covers single-file conversion, upgrade routing,
  V5 legacy file-family output, legacy schematic `.sch` contents, legacy symbol
  `.lib/.dcm` downgrade contents, legacy `.lib/.dcm` upgrade contents,
  standalone `.dcm` upgrade contents, legacy `.sch` upgrade contents,
  legacy `.pro` upgrade/downgrade contents, project-level legacy
  project/symbol/schematic upgrade, V6+ project-local symbol-library table
  generation, schematic `lib_symbols` embedding, KiCad 6+ hierarchy instance
  rebuild, KiCad 6 hidden power reference normalization in generated
  `symbol_instances`, KiCad 5 schematic symbol rotation/mirror transform matrices,
  KiCad 5 PCB header/layer/module/track-arc/multilayer-zone compatibility,
  project library table normalization, project local footprint aliases, and
  V7 `.kicad_prl` generation.
- `scripts/kicad5_python_smoke.py` runs under
  `D:\KiCad\5.0\KiCad\bin\python.exe` on this machine, imports the legacy
  action entrypoint, and verifies the external Python 3 handoff by executing
  `plugin.py --list-targets`.
- `scripts/kicad5_board_load_smoke.py` generates a modern board, converts it to
  target `5.0`, and verifies the resulting `.kicad_pcb` with the local KiCad 5
  `pcbnew.LoadBoard()` runtime.
- `scripts/real_fixture_smoke.py` converts real fixtures from
  `E:\WORKS\MY\kicadProject\kicad-bridge\files\kicad`, verifies converted
  PCBs with KiCad 5/7 `pcbnew.LoadBoard()`, and exports the converted V7
  Bob_Graphics schematic to SVG with KiCad 7 CLI.
- `scripts/reference_parity_smoke.py` compares the Python rule warning surface
  with `E:\WORKS\MY\kicadProject\kicad-backport-cplus\src\kicad_backport_rules.cpp`.
  The current Python core covers all 120 C++ downgrade/upgrade rule warning
  messages, so rule-level parity gaps fail as an explicit smoke check instead
  of relying on manual inspection.

## Remaining lossy compatibility boundaries

- The Python rule set now matches the current C++ downgrade/upgrade rule warning
  surface. If future C++ rule additions are not ported, `reference_parity_smoke`
  reports the exact missing message.
- Legacy schematic and symbol conversions are intentionally lossy in the same
  family as the C++ reference implementation: both sides still warn that
  advanced drawing primitives, documentation-only data, and some legacy record
  edge cases are not fully reconstructable across KiCad file families.
- Full confidence for manufacturing-critical projects still requires opening or
  exporting the generated copy in the target KiCad version. The automated gates
  now cover synthetic conversion stress cases, KiCad 5.0 Python entry loading,
  KiCad 5 board loading, real fixture PCB loading, and KiCad 7 schematic export.
