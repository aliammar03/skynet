{ lib, python3Packages, cacert }:
let
  root = ../..;
  metadata = builtins.fromTOML (builtins.readFile (root + "/pyproject.toml"));
  source = lib.fileset.toSource {
    inherit root;
    fileset = lib.fileset.unions [
      (root + "/pyproject.toml")
      (root + "/src")
      (root + "/tests/test_cli.py")
      (root + "/tests/test_proxmox.py")
      (root + "/tests/fixtures/proxmox")
    ];
  };
in
python3Packages.buildPythonApplication {
  pname = "skynet";
  inherit (metadata.project) version;
  pyproject = true;
  src = source;
  build-system = [ python3Packages.setuptools ];
  nativeCheckInputs = with python3Packages; [ pytest ruff mypy ];
  doCheck = true;

  checkPhase = ''
    runHook preCheck
    export SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt
    SKYNET_ENTRYPOINT=module pytest -q tests
    ruff check src tests/test_*.py
    mypy src/skynet
    runHook postCheck
  '';

  passthru.source = source;
}
