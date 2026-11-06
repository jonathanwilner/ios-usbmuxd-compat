# Import with specialArgs.validatedUsbmuxd set to an independently reviewed
# derivation. This example does not declare any upstream version compatible.
{ lib, validatedUsbmuxd, ... }:
{
  services.usbmuxd.enable = true;
  services.usbmuxd.package = validatedUsbmuxd;
  assertions = [{
    assertion = lib.isDerivation validatedUsbmuxd;
    message = "Supply an independently validated usbmuxd derivation.";
  }];
}
