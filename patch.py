#!/usr/bin/env python3
"""
Applies patches from python-validity PR #256 to support
Validity Sensors 138a:00ab (HP EliteBook G5).
"""
import sys, os

BASE = '/usr/lib/python3/dist-packages/validitysensor'
UDEV = '/usr/lib/udev/rules.d/60-python3-validity.rules'
FW_SCRIPT = '/usr/bin/validity-sensors-firmware'

def patch_file(path, description, fn):
    with open(path, 'r') as f:
        original = f.read()
    patched = fn(original)
    if patched == original:
        print(f'  [SKIP] {description} — already applied or text not found')
        return False
    with open(path, 'w') as f:
        f.write(patched)
    print(f'  [OK]   {description}')
    return True

errors = []

# ─────────────────────────────────────────────────────────────
# 1. usb.py — add DEV_AB, DEV_B7 and defensive USB reset
# ─────────────────────────────────────────────────────────────
def patch_usb(src):
    src = src.replace(
        'import errno\nimport logging\nimport typing',
        'import errno\nimport logging\nimport time\nimport typing'
    )
    src = src.replace(
        "    DEV_9a = (0x06cb, 0x009a)\n\n    @classmethod",
        "    DEV_9a = (0x06cb, 0x009a)\n"
        "    DEV_AB = (0x138a, 0x00ab)  # HP EliteBook 840 G5 — sensor type 0xd51\n"
        "    DEV_B7 = (0x06cb, 0x00b7)  # HP G6 series — sensor type 0xd51\n"
        "\n    @classmethod"
    )
    OLD_OPEN = (
        "    def open_dev(self, dev: ucore.Device):\n"
        "        if dev is None:\n"
        "            raise Exception('No matching devices found')\n"
        "\n"
        "        self.dev = dev\n"
        "        self.dev.default_timeout = 15000\n"
        "        dev.set_configuration()"
    )
    NEW_OPEN = (
        "    def open_dev(self, dev: ucore.Device):\n"
        "        if dev is None:\n"
        "            raise Exception('No matching devices found')\n"
        "\n"
        "        # Defensive USB reset: 0xd51 chips (138a:00ab, 06cb:00b7) can get\n"
        "        # stuck in a locked state after suspend or reboot.\n"
        "        try:\n"
        "            vid, pid = dev.idVendor, dev.idProduct\n"
        "            dev.reset()\n"
        "            time.sleep(0.5)\n"
        "            dev = ucore.find(idVendor=vid, idProduct=pid)\n"
        "            if dev is None:\n"
        "                raise Exception('Device disappeared after USB reset')\n"
        "        except USBError as e:\n"
        "            logging.warning('open_dev: USB reset failed (often non-fatal): %s', e)\n"
        "\n"
        "        self.dev = dev\n"
        "        self.dev.default_timeout = 15000\n"
        "        dev.set_configuration()"
    )
    src = src.replace(OLD_OPEN, NEW_OPEN)
    return src

try:
    patch_file(f'{BASE}/usb.py', 'usb.py — DEV_AB/DEV_B7 + USB reset', patch_usb)
except Exception as e:
    errors.append(f'usb.py: {e}')

# ─────────────────────────────────────────────────────────────
# 2. blobs.py — map 00ab → blobs_97, 00b7 → blobs_9a
# ─────────────────────────────────────────────────────────────
def patch_blobs(src):
    src = src.replace(
        "        elif usb.usb_dev().idProduct == 0x009d:\n"
        "            from . import blobs_9d as blobs\n"
        "    elif usb.usb_dev().idVendor == 0x06cb:",
        "        elif usb.usb_dev().idProduct == 0x009d:\n"
        "            from . import blobs_9d as blobs\n"
        "        elif usb.usb_dev().idProduct == 0x00ab:\n"
        "            from . import blobs_97 as blobs   # HP EliteBook 840 G5\n"
        "    elif usb.usb_dev().idVendor == 0x06cb:"
    )
    src = src.replace(
        "        if usb.usb_dev().idProduct == 0x009a:\n"
        "            from . import blobs_9a as blobs\n"
        "\n"
        "    globals()[blob]",
        "        if usb.usb_dev().idProduct == 0x009a:\n"
        "            from . import blobs_9a as blobs\n"
        "        elif usb.usb_dev().idProduct == 0x00b7:\n"
        "            from . import blobs_9a as blobs   # HP G6 series\n"
        "\n"
        "    globals()[blob]"
    )
    return src

try:
    patch_file(f'{BASE}/blobs.py', 'blobs.py — mapping 00ab/00b7', patch_blobs)
except Exception as e:
    errors.append(f'blobs.py: {e}')

# ─────────────────────────────────────────────────────────────
# 3. firmware_tables.py — add firmware URI and name for DEV_AB/DEV_B7
# ─────────────────────────────────────────────────────────────
def patch_fw_tables(src):
    src = src.replace(
        "    SupportedDevices.DEV_9d: {\n"
        "        'driver': 'https://download.lenovo.com/pccbbs/mobiles/nz3gf07w.exe',\n"
        "        'referral': 'https://download.lenovo.com/pccbbs/mobiles/nz3gf07w.exe',\n"
        "        'sha512': 'a4a4e6058b1ea8ab721953d2cfd775a1e7bc589863d160e5ebbb90344858f147d695103677a8df0b2de0c95345df108bda97196245b067f45630038fb7c807cd'\n"
        "    }\n"
        "}",
        "    SupportedDevices.DEV_9d: {\n"
        "        'driver': 'https://download.lenovo.com/pccbbs/mobiles/nz3gf07w.exe',\n"
        "        'referral': 'https://download.lenovo.com/pccbbs/mobiles/nz3gf07w.exe',\n"
        "        'sha512': 'a4a4e6058b1ea8ab721953d2cfd775a1e7bc589863d160e5ebbb90344858f147d695103677a8df0b2de0c95345df108bda97196245b067f45630038fb7c807cd'\n"
        "    },\n"
        "    SupportedDevices.DEV_AB: {\n"
        "        'driver': 'https://ftp.hp.com/pub/softpaq/sp135501-136000/sp135736.exe',\n"
        "        'referral': 'https://support.hp.com/us-en/drivers',\n"
        "        'sha512': 'f9a91e2796a5070f1f40099e2318aa9716e2e6a31b9ba6a93986c450eedbfb0b323dff55c5e4536466946da3e01985f367b1db27bbd7b65f4c333ce0cd47b78c'\n"
        "    },\n"
        "    SupportedDevices.DEV_B7: {\n"
        "        'driver': 'https://ftp.hp.com/pub/softpaq/sp135501-136000/sp135736.exe',\n"
        "        'referral': 'https://support.hp.com/us-en/drivers',\n"
        "        'sha512': 'f9a91e2796a5070f1f40099e2318aa9716e2e6a31b9ba6a93986c450eedbfb0b323dff55c5e4536466946da3e01985f367b1db27bbd7b65f4c333ce0cd47b78c'\n"
        "    }\n"
        "}"
    )
    src = src.replace(
        "    SupportedDevices.DEV_9d: '6_07f_lenovo_mis_qm.xpfwext'\n}",
        "    SupportedDevices.DEV_9d: '6_07f_lenovo_mis_qm.xpfwext',\n"
        "    SupportedDevices.DEV_AB: '6_07f_hp_cmit_mis_qm.xpfwext',\n"
        "    SupportedDevices.DEV_B7: '6_07f_hp_cmit_mis_qm.xpfwext',\n"
        "}"
    )
    return src

try:
    patch_file(f'{BASE}/firmware_tables.py', 'firmware_tables.py — firmware URI/name for DEV_AB', patch_fw_tables)
except Exception as e:
    errors.append(f'firmware_tables.py: {e}')

# ─────────────────────────────────────────────────────────────
# 4. sensor.py — 0xD51 in line_update_type1_devices,
#                aliasing 0xd51→0x199, fix interrupt, fix enroll
# ─────────────────────────────────────────────────────────────
def patch_sensor(src):
    src = src.replace(
        "    0xB5, 0x885, 0xB3, 0x143B, 0x1055, 0xE1, 0x8B1, 0xEA, 0xE4, 0xED, 0x1825, 0x1FF5, 0x199\n]",
        "    0xB5, 0x885, 0xB3, 0x143B, 0x1055, 0xE1, 0x8B1, 0xEA, 0xE4, 0xED, 0x1825, 0x1FF5, 0x199,\n"
        "    0xD51,  # HP EliteBook 840 G5 (138a:00ab) / HP G6 series (06cb:00b7)\n]"
    )
    src = src.replace(
        "    def open(self):\n"
        "        self.device_info = identify_sensor()\n"
        "\n"
        "        logging.info('Opening sensor: %s' % self.device_info.name)",
        "    def open(self):\n"
        "        self.device_info = identify_sensor()\n"
        "        self.real_device_type = self.device_info.type\n"
        "\n"
        "        # Sensor 0xd51 (138a:00ab, 06cb:00b7) has no native profile.\n"
        "        # Profile 0x199 produces images accepted by the on-chip matcher.\n"
        "        if self.device_info.type == 0xd51:\n"
        "            logging.info('Sensor type 0xd51 — aliasing to profile 0x199')\n"
        "            self.device_info.type = 0x199\n"
        "\n"
        "        logging.info('Opening sensor: %s' % self.device_info.name)"
    )
    OLD_CAPTURE = (
        "            # wait for finger\n"
        "            while True:\n"
        "                b = usb.wait_int()\n"
        "                if b[0] == 2:\n"
        "                    break\n"
        "\n"
        "            # wait capture complete\n"
        "            while True:\n"
        "                b = usb.wait_int()\n"
        "                if b[0] != 3:"
    )
    NEW_CAPTURE = (
        "            # wait for finger\n"
        "            # The 0xd51 chip (138a:00ab) skips b[0]=2 and jumps directly to b[0]=3\n"
        "            saved_b = None\n"
        "            while True:\n"
        "                b = usb.wait_int()\n"
        "                if b[0] == 2:\n"
        "                    break\n"
        "                if b[0] == 3 and getattr(self, 'real_device_type', None) == 0xd51:\n"
        "                    saved_b = b\n"
        "                    break\n"
        "\n"
        "            # wait capture complete\n"
        "            while True:\n"
        "                b = saved_b if saved_b is not None else usb.wait_int()\n"
        "                saved_b = None\n"
        "                if b[0] != 3:"
    )
    src = src.replace(OLD_CAPTURE, NEW_CAPTURE)
    OLD_ENROLL = (
        "            usr = db.lookup_user(identity)\n"
        "            if usr is None:\n"
        "                usr = db.new_user(identity)\n"
        "            else:\n"
        "                usr = usr.dbid\n"
        "\n"
        "            recid = db.new_finger(usr, tinfo)"
    )
    NEW_ENROLL = (
        "            existing = db.lookup_user(identity)\n"
        "            if existing is None:\n"
        "                usr = db.new_user(identity)\n"
        "            else:\n"
        "                # Replace existing fingerprint for the same slot (chip rejects duplicates).\n"
        "                for f in existing.fingers:\n"
        "                    if f['subtype'] == subtype:\n"
        "                        db.del_record(f['dbid'])\n"
        "                usr = existing.dbid\n"
        "\n"
        "            recid = db.new_finger(usr, tinfo)"
    )
    src = src.replace(OLD_ENROLL, NEW_ENROLL)
    return src

try:
    patch_file(f'{BASE}/sensor.py', 'sensor.py — full 0xD51 support', patch_sensor)
except Exception as e:
    errors.append(f'sensor.py: {e}')

# ─────────────────────────────────────────────────────────────
# 5. udev rules — add 00ab and 00b7
# ─────────────────────────────────────────────────────────────
def patch_udev(src):
    src = src.replace(
        'ATTRS{idVendor}=="06cb", ATTRS{idProduct}=="009a", GOTO="python_validity_match"\n\nGOTO',
        'ATTRS{idVendor}=="06cb", ATTRS{idProduct}=="009a", GOTO="python_validity_match"\n'
        'ATTRS{idVendor}=="138a", ATTRS{idProduct}=="00ab", GOTO="python_validity_match"\n'
        'ATTRS{idVendor}=="06cb", ATTRS{idProduct}=="00b7", GOTO="python_validity_match"\n\nGOTO'
    )
    return src

try:
    patch_file(UDEV, 'udev rules — 138a:00ab and 06cb:00b7', patch_udev)
    alt_udev = '/lib/udev/rules.d/60-python3-validity.rules'
    if os.path.isfile(alt_udev) and not os.path.islink(alt_udev):
        with open(UDEV, 'r') as f:
            content = f.read()
        with open(alt_udev, 'w') as f:
            f.write(content)
        print('  [OK]   udev rules (copy in /lib/udev)')
except Exception as e:
    errors.append(f'udev: {e}')

# ─────────────────────────────────────────────────────────────
# 6. validity-sensors-firmware — cabextract fallback
# ─────────────────────────────────────────────────────────────
def patch_fw_script(src):
    OLD_CHECK = (
        "    try:\n"
        "        subprocess.check_call(['innoextract', '--version'], stdout=subprocess.DEVNULL)\n"
        "    except Exception as e:\n"
        "        print('Impossible to run innoextract: {}'.format(e))\n"
        "        sys.exit(1)"
    )
    NEW_CHECK = (
        "    have_extractor = False\n"
        "    for tool in ('innoextract', 'cabextract'):\n"
        "        try:\n"
        "            subprocess.check_call([tool, '--version'], stdout=subprocess.DEVNULL)\n"
        "            have_extractor = True\n"
        "            break\n"
        "        except (subprocess.CalledProcessError, FileNotFoundError):\n"
        "            continue\n"
        "    if not have_extractor:\n"
        "        print('Need at least one of innoextract or cabextract installed.')\n"
        "        sys.exit(1)"
    )
    src = src.replace(OLD_CHECK, NEW_CHECK)
    OLD_EXTRACT = (
        "    subprocess.check_call([\n"
        "        'innoextract', '--output-dir', fwdir, '--include', fwname, '--collisions', 'overwrite',\n"
        "        fwarchive\n"
        "    ])"
    )
    NEW_EXTRACT = (
        "    try:\n"
        "        subprocess.check_call([\n"
        "            'innoextract', '--output-dir', fwdir, '--include', fwname,\n"
        "            '--collisions', 'overwrite', fwarchive\n"
        "        ], stderr=subprocess.DEVNULL)\n"
        "    except (subprocess.CalledProcessError, FileNotFoundError):\n"
        "        try:\n"
        "            subprocess.check_call(['cabextract', '-q', '-d', fwdir, fwarchive])\n"
        "        except (subprocess.CalledProcessError, FileNotFoundError) as e:\n"
        "            raise Exception(\n"
        "                'Failed to extract {} from {}: no extractor available ({}).'.format(\n"
        "                    fwname, fwarchive, e))"
    )
    src = src.replace(OLD_EXTRACT, NEW_EXTRACT)
    return src

try:
    patch_file(FW_SCRIPT, 'validity-sensors-firmware — cabextract fallback', patch_fw_script)
except Exception as e:
    errors.append(f'validity-sensors-firmware: {e}')


# ─────────────────────────────────────────────────────────────
# 7. dbus-service — fix VerifyStart for 0xd51 chip (138a:00ab)
#    - silent update_cb (chip fires it during normal scanning, not just failures)
#    - MAX_TRIES=1: one identify() per session, retries handled by pam_fprintd
# ─────────────────────────────────────────────────────────────
def patch_dbus_service(src):
    OLD = (
        "        self.VerifyFingerSelected('any')\n"
        "\n"
        "        def update_cb(e):\n"
        "            self.VerifyStatus('verify-retry-scan', False)\n"
        "\n"
        "        def run():\n"
        "            try:\n"
        "                # TODO: pass down the user db record id and implement a proper Sensor.verify() method\n"
        "                usrid, subtype, hsh = sensor.identify(update_cb)\n"
        "                if usr.dbid == usrid:\n"
        "                    self.VerifyStatus('verify-match', True)\n"
        "                else:\n"
        "                    self.VerifyStatus('verify-no-match', True)\n"
        "            except usb_core.USBError as e:\n"
        "                logging.exception(e)\n"
        "                self.VerifyStatus('verify-no-match', True)\n"
        "                loop.quit()\n"
        "            except Exception as e:\n"
        "                logging.exception(e)\n"
        "                self.VerifyStatus('verify-no-match', True)"
    )
    NEW = (
        "        self.VerifyFingerSelected('any')\n"
        "\n"
        "        retry_count = [0]\n"
        "\n"
        "        def update_cb(e):\n"
        "            # The 0xd51 chip calls update_cb during normal scanning,\n"
        "            # not only on failure: do not emit verify-retry-scan here.\n"
        "            retry_count[0] += 1\n"
        "            logging.info('retry-scan #%d', retry_count[0])\n"
        "\n"
        "        MAX_TRIES = 1\n"
        "\n"
        "        def run():\n"
        "            try:\n"
        "                for attempt in range(MAX_TRIES):\n"
        "                    usrid, subtype, hsh = sensor.identify(update_cb)\n"
        "                    if usr.dbid == usrid:\n"
        "                        self.VerifyStatus('verify-match', True)\n"
        "                        return\n"
        "                    last = (attempt == MAX_TRIES - 1)\n"
        "                    self.VerifyStatus('verify-no-match', last)\n"
        "                    if last:\n"
        "                        return\n"
        "            except usb_core.USBError as e:\n"
        "                logging.exception(e)\n"
        "                self.VerifyStatus('verify-no-match', True)\n"
        "                loop.quit()\n"
        "            except Exception as e:\n"
        "                logging.exception(e)\n"
        "                self.VerifyStatus('verify-no-match', True)"
    )
    src = src.replace(OLD, NEW)
    return src

try:
    patch_file("/usr/lib/python-validity/dbus-service", "dbus-service — fix VerifyStart 0xd51", patch_dbus_service)
except Exception as e:
    errors.append(f"dbus-service: {e}")

# ─────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────
print()
if errors:
    print('ERRORS during patching:')
    for e in errors:
        print(f'  x {e}')
    sys.exit(1)
else:
    print('All patches applied successfully.')
    print()
    print('Next steps:')
    print('  1. sudo apt install -y cabextract')
    print('  2. sudo udevadm control --reload-rules && sudo udevadm trigger')
    print('  3. sudo systemctl restart python3-validity')
    print('  4. sudo validity-sensors-firmware')
    print('  5. fprintd-enroll  (to enroll your fingerprint)')
