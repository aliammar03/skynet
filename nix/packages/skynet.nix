{ lib, python3Packages, gnugrep, makeWrapper }:
let
  root = ../..;
  metadata = builtins.fromTOML (builtins.readFile (root + "/pyproject.toml"));
  source = lib.fileset.toSource {
    inherit root;
    fileset = lib.fileset.unions [
      (root + "/pyproject.toml")
      (root + "/src")
      (root + "/lab.json")
      (root + "/invariants.json")
      (root + "/scripts/sql/host-map.sql")
      (root + "/scripts/sql/vhosts.sql")
    ];
  };
in
python3Packages.buildPythonApplication {
  pname = "skynet";
  inherit (metadata.project) version;
  pyproject = true;
  src = source;
  build-system = [ python3Packages.setuptools ];
  nativeBuildInputs = [ makeWrapper ];
  doCheck = false;

  postFixup = ''
    wrapProgram "$out/bin/skynet" --prefix PATH : ${lib.makeBinPath [ gnugrep ]}
  '';

  passthru.source = source;
}
