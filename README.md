# HKG Community Catalog

A signed catalog of community [NEMESIS](https://github.com/xwtk/hmg_nemesis) packages for
Hyundai/Kia Gen5W head units, for [HKG Package Manager](https://github.com/loredous/hkg-package-manager)
1.1.0 or newer. The catalog only lists packages: every zip is downloaded from its own
project's GitHub release (or, for a project without releases, its committed file), pinned to
that exact version by its size and SHA-256. Nothing here is re-hosted.

Packages are written and maintained by their authors. Inclusion here isn't an endorsement or a
test result. Read each project's README before installing, and install at your own risk.

## Trusting this catalog

The catalog is signed. Before the manager or the mirror CLI uses it, check that its key has
this fingerprint:

    0e1b dd68 96e8 de2f 5c9b 6034 b80f 257b 48f9 6dd5 34a8 48d8 50df 3761 b33e 89ec

The manager shows the fingerprint when it first sees the catalog ("Untrusted catalog …,
key fingerprint …"); tap "Trust this key" only if it matches.

## Putting it on a USB stick

With the mirror CLI from hkg-package-manager (`cli/hkgpm_mirror.py`, Python 3, no extra
packages):

    python3 cli/hkgpm_mirror.py https://raw.githubusercontent.com/loredous/hkg-community-catalog/main/community /path/to/stick \
        --fingerprint 0e1bdd6896e8de2f5c9b6034b80f257b48f96dd534a848d850df3761b33e89ec

It checks the signature, downloads every zip, checks each one's size and SHA-256, and writes
`HKGPM/catalogs/community/` on the stick. Re-run it to update the stick. Add
`--only <package id> ...` to copy only some packages.

## Packages

| Package | Project | Compatibility given |
|---|---|---|
| SmartTube (`smarttube`) | [KramerTech/gen5-SmartTube](https://github.com/KramerTech/gen5-SmartTube) | none (needs `media.codecs` first) |
| Rear Dashcam (`dashcam`) | [KramerTech/gen5-RearDashcam](https://github.com/KramerTech/gen5-RearDashcam) | none (not for 360-degree camera cars) |
| Startup confirmation auto-dismiss (`local.hkmc.factory82`) | [armandodollia/nemesis-package-builds](https://github.com/armandodollia/nemesis-package-builds) | none (not yet tested on a car) |
| Track button swap (`hkmc.track-button-swap`) | [dibble9012/hkmc-track-button-swap](https://github.com/dibble9012/hkmc-track-button-swap) | none (made for the EV6) |
| CarPlay auto-display (`hkmc.carplay-auto-display`) | [dibble9012/hkmc-carplay-auto-display](https://github.com/dibble9012/hkmc-carplay-auto-display) | none (tested on an EV6) |
| Launchpad (`paytondev.launchpad`) | [paytondevs/gen5w-preconditioning](https://github.com/paytondevs/gen5w-preconditioning) | Ioniq 5 US 260507 and 260903, EV6 US 260507 |
| Cold-start Heat (`coldstart.heat`) | [eclipseempire/hkmc-coldstart-heat](https://github.com/eclipseempire/hkmc-coldstart-heat) | Ioniq 5 US 260507 |
| Battery Watchdog (`battery.watchdog`) | [zpoon/gen5w-BatteryWatchdog](https://github.com/zpoon/gen5w-BatteryWatchdog) | Ioniq 5 US 260507 and 260903 |
| HKG Climate Page (`hkg.climate.page`) | [loredous/hkg-climate-page](https://github.com/loredous/hkg-climate-page) | Ioniq 5 US 260507 |

"Compatibility given" turns into the manager's colours. A package is green ("Works on this
car") only where its author names the car and firmware, matched against the head unit's
`ro.build.product` (for example `NEEV.USA.0000.V015.012.260507`: the Ioniq 5 US prefix
`NEEV.USA.` or `NEEV23.USA.`, the EV6 US prefix `CVEV.USA.`, and the software version in the
last six digits). Everything else is yellow ("No compatibility information"), which means
"read the project's README", not "broken".

Not listed yet, because their releases have no plain package zip (only a USB-stick zip) or no
zip at all: HMG Leafia Plus, egmp-aa-ev-feat, hkmc-ptt-phone-assistant, KeyBORD-Gen5W,
gen5w-ambient-sound and hmg-aa-dpi. They can join as soon as their releases attach the
package zip itself (the zip with `NEMESIS.data` at its root).

## Adding or updating a package

Open a pull request that edits `sources.json`. Each package needs:

- `id`: the package id from its `NEMESIS.data`.
- `repo`: `owner/name` on GitHub.
- Either `asset`: a glob matching exactly one asset of the project's latest release (plus an
  optional `not` glob to exclude one, such as `*-usb.zip`), or `path`: the zip committed in
  the repo, for projects without releases.
- `description` and `author`.
- Optional `compatibility`, in the catalog format's `works_on` / `not_on` / `conflicts` form
  (see [the format](https://github.com/loredous/hkg-package-manager/blob/main/docs/catalog/format.md)).
  Only state a car and firmware the package's author has tested.

The release asset must be the package zip itself, with `NEMESIS.data` (holding `[nemesis]`
and `id=`) at its root, not a USB-stick zip.

The maintainer then rebuilds and re-signs the catalog:

    GITHUB_TOKEN=$(gh auth token) python3 tools/build.py --key <path to the catalog's private key>

`tools/build.py` picks up each project's latest release, checks that the zip's `NEMESIS.data`
names the expected id, and writes `community/index.json`, `community/index.json.sig` and
`community/key.pem`. Re-running it after an author publishes a new release updates that
package.

## License

GPL-3.0 (see `LICENSE`). This covers the catalog files and the build script. Each listed
package keeps its own project's license.
