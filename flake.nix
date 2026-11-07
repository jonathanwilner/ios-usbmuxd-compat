{
  description = "Reusable iPhone USB diagnostics and Debian integration reference";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      eachSystem = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
      mkFramework = pkgs: pkgs.python3Packages.buildPythonPackage {
        pname = "ios-usbmuxd-compat";
        version = "0.1.0";
        pyproject = true;
        src = self;
        build-system = [ pkgs.python3Packages.setuptools ];
        makeWrapperArgs = [ "--prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.libimobiledevice ]}" ];
        nativeCheckInputs = [ pkgs.python3Packages.jsonschema ];
        checkPhase = ''
          runHook preCheck
          PYTHONPATH="src:$PYTHONPATH" ${pkgs.python3.interpreter} -m unittest discover -s tests/unit -v
          runHook postCheck
        '';
        pythonImportsCheck = [ "ios_usbmuxd_compat" "iphone_connectivity_demo" ];
        postInstall = ''
          mkdir -p $out/share/ios-usbmuxd-compat/schemas
          cp schemas/*.json $out/share/ios-usbmuxd-compat/schemas/
        '';
        # Nix installs the rootless CLI only. Debian installs privilege integrations.
        meta = {
          license = pkgs.lib.licenses.mit;
          platforms = systems;
          mainProgram = "iphone-connectivity-demo";
        };
      };
    in {
      packages = eachSystem (pkgs: let framework = mkFramework pkgs; in {
        default = framework;
        ios-usbmuxd-compat = framework;
        iphone-connectivity-demo = framework;
        usbmuxd-candidate = let
          lock = builtins.fromJSON (builtins.readFile ./packaging/daemon/candidate-sources.json);
          source = builtins.elemAt lock.sources 5;
        in pkgs.usbmuxd.overrideAttrs (old: {
          pname = "usbmuxd-unvalidated-candidate";
          version = source.version;
          src = pkgs.fetchurl { inherit (source) url sha256; name = "usbmuxd-${source.commit}.tar.gz"; };
          patches = [];
          postPatch = ''
            echo '${source.version}' > .tarball-version
          '';
          postInstall = (old.postInstall or "") + ''
            mkdir -p $out/share/doc/usbmuxd
            cp ${./packaging/daemon/candidate-sources.json} $out/share/doc/usbmuxd/source-lock.json
            echo 'Unvalidated candidate; no automatic activation.' > $out/share/doc/usbmuxd/VALIDATION
          '';
        });
        usbmuxd-reference = pkgs.stdenv.mkDerivation {
          pname = "usbmuxd-unvalidated-reference";
          version = "1.1.1";
          src = pkgs.fetchurl {
            url = "https://github.com/libimobiledevice/usbmuxd/archive/79c8b38d1488a6b07e1e68f39d8caec3f1a45622.tar.gz";
            sha256 = "a4312626468a2c65850fda68191d461873a47bff79f05d82bea7c17e73e535eb";
          };
          nativeBuildInputs = [ pkgs.autoreconfHook pkgs.pkg-config ];
          buildInputs = [ pkgs.libusb1 pkgs.libplist pkgs.libimobiledevice ];
          configureFlags = [ "--without-systemd" ];
          # Build-only namespace fix: modern libplist defines these same enum names.
          # Rename all upstream uses together; no preflight/pairing behavior changes.
          postPatch = ''
            for file in src/*.c src/*.h; do
              substituteInPlace "$file" --replace-warn PLIST_FORMAT_ USBMUXD_PLIST_FORMAT_
            done
          '';
          installPhase = ''
            runHook preInstall
            install -Dm755 src/usbmuxd $out/bin/usbmuxd
            mkdir -p $out/share/doc/usbmuxd
            cp COPYING.GPLv* $out/share/doc/usbmuxd/
            printf '%s\n' 'Baseline with build-only enum namespace adjustment; no hardware validation; never an automatic repair.' > $out/share/doc/usbmuxd/VALIDATION
            runHook postInstall
          '';
          meta.license = [ pkgs.lib.licenses.gpl2Only pkgs.lib.licenses.gpl3Only ];
          meta.platforms = systems;
        };
      });
      checks = eachSystem (pkgs: { unit-tests = mkFramework pkgs; });
      devShells = eachSystem (pkgs: {
        default = pkgs.mkShell {
          packages = [ (pkgs.python3.withPackages (p: [ p.setuptools p.build p.jsonschema p.ruff ])) pkgs.git pkgs.libimobiledevice pkgs.usbmuxd ];
          shellHook = ''export PYTHONPATH="$PWD/src"'';
        };
      });
    };
}
