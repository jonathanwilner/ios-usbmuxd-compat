#!/usr/bin/env python3
"""Copy the structure; replace the probe with your application's real protocol."""
import json
from ios_usbmuxd_compat import ProbeResult
from ios_usbmuxd_compat.remediation import diagnose_selected


class ProductTypeProbe:
    name = "example-product-type"

    def run(self, device_id, runner, tools):
        # This is an additional real, read-only lockdown query. An integrating
        # application should query its own required service here, with a timeout.
        result = runner([tools["ideviceinfo"], "-u", device_id, "-k", "ProductType"], timeout=5)
        value = result.stdout.strip()
        if result.code == 0 and value.startswith(("iPhone", "iPad", "iPod")):
            return ProbeResult("working", "Product type query succeeded.")
        return ProbeResult("application_protocol_failure", "Product type query failed.")


def startup():
    report = diagnose_selected(probes=[ProductTypeProbe()])
    # Keep the rest of the application usable while hardware is absent.
    return report


if __name__ == "__main__":
    print(json.dumps(startup(), indent=2))
