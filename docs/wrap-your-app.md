# Wrap your application with managed usbmuxd compatibility

## The product you deliver

Your customer installs your app's Debian package once. Your app depends on this
toolkit and your validated usbmuxd component package. When your app starts, the
wrapper checks connectivity, requests an approved repair if needed, and launches
your executable. The app keeps using the normal `/run/usbmuxd` socket.

This is an application integration toolkit. The demo is a test harness; your
customers do not need the demo package.

## 1. Add the toolkit dependency

Build this repository with `./scripts/build-deb.sh`. Distribute the resulting
`ios-usbmuxd-compat` package through your normal package channel alongside your
app. Merge [the dependency fragment](../examples/app-wrapper/control.fragment)
into your app's `debian/control`.

## 2. Supply your updated daemon

Your updated daemon is a separate Debian package. Start with the
[source/package recipe](../packaging/daemon/README.md), pin your source and patch,
and follow [component validation](daemon-validation.md). Install the binary and
manifest under `/usr/lib/ios-usbmuxd-compat/daemon/`. Include the recipe's rollback
removal hook. Do not overwrite the distribution executable or add a competing
service. Do not copy the unvalidated reference manifest and mark it approved
without performing validation.

The toolkit supplies service inspection, authorization, activation, health
checks, state and rollback. You supply the daemon binary, runtime dependencies,
license/source obligations, supported target matrix and evidence that it fixes
the recognized failure. There is currently no ready-to-deploy updated daemon in
this repository. A working stock daemon remains in use even when the optional
component is installed.

usbmuxd owns a system-wide socket. The replacement is isolated on disk, but its
activation affects every app using that socket. This toolkit has one shared
fallback slot, not a separate daemon instance per app. Coordinate component
ownership if multiple applications ship it. Private client libraries require
separate application linking/RUNPATH integration; the wrapper does not change
your app's ABI or inject loader paths.

## 3. Wrap your existing executable

No Python changes are required for a normal executable:

```sh
ios-usbmuxd-wrap --repair -- /usr/bin/my-app --your-option
```

Use this as the command in your launcher. Adapt the
[desktop entry](../examples/app-wrapper/my-app.desktop). The terminal is enabled
in this example so a blocked launch shows the diagnostic message. A production
GUI should use the API below to display Trust, lock and repair messages itself.

The wrapper launches only after a real lockdown check succeeds. It never sends
your app path or arguments to the privileged helper and never launches your app
as root. `--repair` permits a fixed repair request; PolicyKit can still require
administrator approval. Omitting it performs checks only.

For an app that can open without a phone:

```sh
ios-usbmuxd-wrap --repair --allow-pending-device -- /usr/bin/my-app
```

The child receives `IOS_USBMUXD_COMPAT_STATUS=ready` or `pending_device`.
The latter is not connectivity success. Recheck in your app when enabling its
phone feature. The installed device-event service also runs deferred diagnostics;
it does not launch your app or silently authorize repairs.

## 4. Optional native app integration

A Python app can call the same adapter and keep its own UI open:

```python
from ios_usbmuxd_compat.wrapper import prepare

report = prepare()  # On startup, no privilege prompt.
# Display report["status"] in your UI.
# On an explicit "Repair connection" button:
report = prepare(allow_repair=True)
# Enable phone operations only when report["status"] == "ready".
```

Pass `probes=[YourApplicationProbe()]` to test your actual iOS service in addition
to lockdown. See the [probe interface](integration-guide.md). Non-Python apps can
use `ios-usbmuxd-compat check --json` and the fixed `repair` CLI operation.

## 5. Validate and ship

Run the package lifecycle suite and [hardware plan](hardware-test-plan.md) with
your app and daemon on each supported distribution. Ship your app, framework and
validated daemon packages together. Installation never waits for a connected
phone. Test the launcher with no phone, Trust pending, locked phone, a working
stock stack, a recognized failure, denied authorization and failed activation.

To disable fallback, run `ios-usbmuxd-compat rollback`, verify stock recovery,
then remove your optional daemon component. Pairing records remain intact.

Wrapper exit codes: 75 connectivity not ready, 77 root invocation refused,
70 inspection/authorization error, 69 executable unavailable, 2 invalid arguments.
After successful exec, your application's own exit status is returned normally.
