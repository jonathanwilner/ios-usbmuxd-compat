# Contributing

Use Python 3.10 or later. Keep the runtime dependency set small and the public
API compatible within schema version 1. Include fixture tests for diagnostics
and negative tests for privileged operations. Run `python3 -m unittest discover
-s tests -v` and the native Debian build described in README.md.

Never add device identifiers, pairing records, certificates, private keys or
raw device journals to a pull request. Synthetic identifiers belong in tests.
Report physical test results with distribution, architecture, package versions,
iPhone model, iOS version and steps, without serial numbers.

Changes to repair selection need evidence of the failure and a bounded,
reversible response. Package version comparisons alone cannot authorize daemon
replacement. Changes to the helper need explicit threat-model review. Keep
system inspection, repair selection and privileged mutation separate.

Do not hand-edit distribution executables or system-wide shared libraries.
A new replacement daemon requires the validation procedure in
[daemon-validation.md](docs/daemon-validation.md). Preserve upstream licenses.
Contributions are licensed under MIT unless an explicitly attributed component
has another compatible license. Do not upload generated releases from forks.
