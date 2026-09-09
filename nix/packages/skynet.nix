{ lib, python3Packages, cacert, openssl, jq, gawk, bash }:
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
      (root + "/tests/test_collection.py")
      (root + "/tests/test_pbs.py")
      (root + "/tests/test_docker.py")
      (root + "/tests/test_dns.py")
      (root + "/tests/fixtures/proxmox")
      (root + "/tests/fixtures/pbs")
      (root + "/tests/fixtures/dns")
      (root + "/bin/ops")
      (root + "/bin/skynet")
      (root + "/scripts/collect-all.sh")
      (root + "/scripts/collect-proxmox.sh")
      (root + "/scripts/collect-pbs.sh")
      (root + "/scripts/collect-docker.sh")
      (root + "/scripts/collect-dns.sh")
      (root + "/scripts/render-docs.sh")
    ];
  };
in
python3Packages.buildPythonApplication {
  pname = "skynet";
  inherit (metadata.project) version;
  pyproject = true;
  src = source;
  build-system = [ python3Packages.setuptools ];
  nativeCheckInputs = (with python3Packages; [ pytest ruff mypy ]) ++ [ openssl jq gawk bash ];
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
