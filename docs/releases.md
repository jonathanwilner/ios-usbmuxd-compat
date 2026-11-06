# Release process

1. Update `setup.cfg`, `packaging/debian/changelog` and `flake.nix` versions together. Review the MIT license,
   external-component notices and security policy contact before public hosting.
2. Run unit tests, lint and the five-distribution native package lifecycle matrix.
   Record exact images, architectures and results in `docs/compatibility.md`.
3. Complete the manual hardware plan before making a hardware compatibility claim.
   Otherwise label the release a reference implementation with hardware untested.
4. Commit the source and create a matching `v<version>` tag. Publishing the
   repository/tag/release is a separate maintainer action.
5. Run the manual release-candidate workflow for the tag. Download the artifact,
   `.buildinfo`, `.changes`, `SOURCE_COMMIT`, `BUILD_IMAGE` and checksums.
6. Verify `sha256sum -c SHA256SUMS` in the package artifact directory. Review
   dependency resolution and payloads. The Python `.deb` must have no Nix paths.
7. Publish reviewed assets through ordinary GitHub releases. Include the exact
   test matrix, hardware limitations, source commit and image digest. Sign the
   checksums with the maintainer's established signing key when available.

Actions are pinned to full commits. Python lint dependencies are version pinned.
Container tags track supported distro updates; the actual image digest is build
provenance, not a promise that a mutable tag is bit-reproducible. For a strictly
repeatable native rebuild, retain the image digest and use a pinned distribution
package snapshot with the recorded `.buildinfo` dependency versions. The Nix
input is locked. Optional daemon builds must also pin their source and patches.

No workflow publishes a release automatically. No credentials, pairing records
or private infrastructure are required to build this project.
