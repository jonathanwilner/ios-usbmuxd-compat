# Manual hardware acceptance

No iPhone hardware compatibility is claimed by fixture or container tests.
Run these checks in a disposable VM with USB passthrough or a dedicated Debian
or Ubuntu host. Keep a recovery console available for replacement testing.

Record the OS release, architecture, systemd version, package versions, daemon
source/build hashes, iPhone model and iOS version. Exclude device serial numbers,
UDIDs and pairing data from the published report.

1. Install the example with no phone attached. Installation must finish. Check
   returns `pending_device`. Confirm the stock daemon executable is unchanged.
2. Attach an unlocked phone with existing Trust. Confirm the event service runs,
   usbmuxd enumerates the phone, pairing validates and lockdown reads
   `ProductVersion`. Only this protocol success permits `ready`.
3. Reconnect twice. Confirm event activation on each attachment. Inspect the
   bounded service journal. Confirm no test runs within the udev worker.
4. Use a phone that has not trusted this host. Check before tapping Trust, while
   the dialog is open, after denial, and after explicit `pair` and acceptance.
   Do not delete existing host pairing records to manufacture this test.
5. Lock and unlock the phone. Check how the particular iOS release behaves.
   Some already-trusted devices allow limited lockdown access while locked.
   The tool must report observed protocol results, not infer lock state.
6. Unplug during initialization and during a repair verification. Missing
   hardware must remain pending, without a claim of daemon failure.
7. Connect two phones. One ready phone must not conceal a failure on the other.
8. Test a USB permission failure using a disposable unprivileged account and
   controlled test permissions. Restore permissions afterward. Do not weaken
   USB access globally to make the test pass.
9. Run dry-run and repair on a working stock stack. Confirm no service restart,
   drop-in, executable replacement or pairing-record change.
10. If an independently validated private client package exists, reproduce the
    old client's failure and the private client's successful protocol operation.
    Confirm system library packages and loader configuration remain unchanged.
11. Only with an independently validated daemon package, reproduce its targeted
    daemon failure. Inspect the recorded original unit, activate fallback, check
    effective arguments, service account, socket, USB ownership and protocol.
12. In the VM, exercise a deliberately broken fixture daemon and interrupted
    activation. Confirm automatic recovery removes only the owned override and
    restores the original daemon. Do not put a fixture binary in a real package
    or mark it validated for production.
13. Upgrade the distribution usbmuxd package. Recheck the effective unit and
    compatibility authorization. Existing administrator overrides must block
    fallback activation until reviewed.
14. Remove and purge the example/framework packages. Verify the original daemon
    can run, only package-owned configuration was removed, and `/var/lib/lockdown`
    records are preserved. Install twice and repeat attachment tests.

Mark each result PASS, FAIL or NOT RUN with a reason. Publish compatibility
claims only for the exact hardware/OS combination that passed. A socket-health
pass with an unplugged phone is pending hardware validation.

## Current upstream candidate and Vysor

Before approving the current candidate, record the stock stack's actual failure
and compare it with pinned upstream `3ded00c` on the same host and iPhone.
Use a dedicated test host for manual candidate evaluation before producing any
validated manifest. Preserve the original service arguments and account; stop
the stock daemon before starting the candidate. Never run both against the USB
device. Retain original pairing records and return the host to stock afterward.
A healthy socket with a preflight/Trust failure currently requires manual
investigation: the automatic daemon strategy accepts only the narrowly defined
socket-failure signatures in `docs/daemon-validation.md`.

After lockdown succeeds, launch Vysor through `vysor-usb`. Verify discovery,
actual screen mirroring, input, disconnect/reconnect, and a second app launch.
Record Vysor version and whether its embedded client uses the system socket.
A successful `ideviceinfo` call alone does not establish Vysor acceptance.
