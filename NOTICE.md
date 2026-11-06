# Attribution and external components

The Python framework, example, packaging and documentation are original MIT
licensed code. No upstream daemon or client-library source is vendored.

The example invokes tools from the libimobiledevice project. Distribution
packages retain their upstream licenses. A separately distributed usbmuxd build
must include its own license and corresponding source obligations; the MIT
license of this framework does not relicense that daemon.

Research references:
- https://github.com/libimobiledevice/usbmuxd/issues/281
- https://github.com/libimobiledevice/usbmuxd/blob/master/src/preflight.c
- https://github.com/libimobiledevice/usbmuxd/blob/master/src/main.c
- https://github.com/libimobiledevice/usbmuxd/blob/master/systemd/usbmuxd.service.in

Upstream research informed the design. No patch is represented as validated.
