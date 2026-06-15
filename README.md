# fingerprint-hp-g5

Fingerprint reader support for **Validity Sensors 138a:00ab** (chip 0xd51)
on HP EliteBook G5 with KDE Neon / Ubuntu 24.04.

## Problem

The reader is supported neither by upstream `libfprint` nor by the
`python3-validity` driver in the official PPA. There is
[PR #256](https://github.com/uunicorn/python-validity/pull/256) that adds
support, but it has not been merged yet. This repo contains the PR patches
plus additional fixes discovered during integration.

## How it works

The system uses **python3-validity** + **open-fprintd** (PPA
`uunicorn/open-fprintd`) instead of the standard `fprintd` daemon, which
they conflict with. The client tools (`fprintd-enroll`, `pam_fprintd.so`,
etc.) are extracted from the official `fprintd` package and installed as a
separate local package (`fprintd-tools`) to avoid the conflict.

## Repo structure

```
patch.py                   # Patches python3-validity for the 0xd51 chip
install.sh                 # Full installation script
apt-hook/
  99validity-patch         # Apt hook: re-applies patches after upgrades
sleep-hook/
  python3-validity         # systemd-sleep hook: restarts driver after standby
fprintd-tools/
  build.sh                 # Builds the local fprintd-tools package
```

## Quick install

```bash
git clone <this-repo>
cd fingerprint-hp-g5
sudo bash install.sh
fprintd-enroll
```

## Patch details (`patch.py`)

Modifies the following `python3-validity` files after each install/upgrade:

| File | Change |
|------|--------|
| `validitysensor/usb.py` | Adds `DEV_AB`/`DEV_B7`; defensive USB reset at startup (chip gets stuck after reboot/resume if not reset) |
| `validitysensor/blobs.py` | Maps `0x00ab` → `blobs_97`, `0x00b7` → `blobs_9a` |
| `validitysensor/firmware_tables.py` | HP firmware URI and name for `DEV_AB`/`DEV_B7` |
| `validitysensor/sensor.py` | Type aliasing `0xd51` → `0x199`; `capture()` interrupt fix (chip skips `b[0]=2`); `enroll()` fix (replaces existing fingerprint instead of failing) |
| `udev rules` | Adds `138a:00ab` and `06cb:00b7` |
| `validity-sensors-firmware` | `cabextract` fallback for HP softpaqs (not Inno Setup format) |
| `dbus-service` | Silent `update_cb` (chip fires retries during normal scanning — emitting them caused timeouts in `pam_fprintd`); `MAX_TRIES=1` (one `identify()` per session, retries handled by `pam_fprintd` with `max-tries=3`) |

## Apt hook (`apt-hook/99validity-patch`)

Automatically re-applies `patch.py` after every `apt upgrade` that updates
`python3-validity`. Output visible in the terminal:

```
[validity-patch] Re-applying patches for fingerprint sensor 138a:00ab (HP EliteBook G5)...
  [OK]   usb.py — DEV_AB/DEV_B7 + USB reset
  ...
[validity-patch] OK
```

## Resume hook (`sleep-hook/python3-validity`)

After suspend, the 0xd51 chip gets stuck: it accepts outgoing USB commands
but never responds to incoming ones. A simple D-Bus `Resume()` call is not
enough — a full driver restart is required.

The hook runs **synchronously** during resume (via `/lib/systemd/system-sleep/`),
before the system becomes operational and before the lock screen starts PAM
authentication. It waits for the service to become active (max 10s) before
yielding control.

## PAM configuration

`pam_fprintd.so` is configured with `max-tries=3 timeout=8`:

- **max-tries=3**: up to 3 finger attempts before password fallback
- **timeout=8**: after 8s without a read, the password field becomes active
  (prevents the SDDM greeter from blocking password input for 30+ seconds)

## Updates

After an `apt upgrade` the patches are automatically re-applied by the hook.
The `fprintd-tools` package (client tools + PAM) is never overwritten by
upgrades because it is not part of any official package.

## Reinstall from scratch

```bash
git clone https://github.com/bitblaster/fingerprint-hp-g5.git
cd fingerprint-hp-g5
sudo bash install.sh
fprintd-enroll
```

## Diagnostics

```bash
systemctl status python3-validity open-fprintd   # service status
journalctl -u python3-validity -f                 # driver log (live)
journalctl -t python3-validity-sleep              # resume log
fprintd-verify                                    # fingerprint read test
fprintd-list $USER                                # enrolled fingerprints
```
