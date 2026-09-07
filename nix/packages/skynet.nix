{ lib, python3Packages }:
let
  root = ../..;
  metadata = builtins.fromTOML (builtins.readFile (root + "/pyproject.toml"));
  source = lib.fileset.toSource {
    inherit root;
    fileset = lib.fileset.unions [
      (root + "/pyproject.toml")
      (root + "/src")
      (root + "/tests/test_cli.py")
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
    SKYNET_ENTRYPOINT=module pytest -q tests/test_cli.py
    ruff check src tests/test_cli.py
    mypy src/skynet
    runHook postCheck
  '';

  passthru.source = source;
}
