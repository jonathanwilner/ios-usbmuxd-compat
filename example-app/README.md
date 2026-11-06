# Example application

The installed example package is implemented in
[`src/iphone_connectivity_demo`](../src/iphone_connectivity_demo/). It delegates
to the same library CLI API available to integrating applications. Its Python
package and Debian binary package are separate from the compatibility library.

Run `iphone-connectivity-demo` to check on startup, or choose an explicit command
listed in the top-level README. The demo needs no GUI or proprietary application.
For an application with its own service-specific probe, start with
[`examples/integration/startup.py`](../examples/integration/startup.py).
