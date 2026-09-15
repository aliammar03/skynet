{ lib, python3Packages, docker, gitMinimal, gnugrep, makeWrapper, openssh, sops }:
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
      (root + "/bin/ops")
      (root + "/bin/skynet")
      (root + "/scripts/collect-all.sh")
      (root + "/scripts/collect-proxmox.sh")
      (root + "/scripts/collect-pbs.sh")
      (root + "/scripts/collect-docker.sh")
      (root + "/scripts/collect-dns.sh")
      (root + "/scripts/collect-opnsense.sh")
      (root + "/scripts/collect-network-gear.sh")
      (root + "/scripts/collect-certs.sh")
      (root + "/scripts/collect-routes.sh")
      (root + "/scripts/recon.sh")
      (root + "/scripts/build-db.sh")
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
    wrapProgram "$out/bin/skynet" --prefix PATH : ${lib.makeBinPath [ docker gitMinimal gnugrep openssh sops ]}
  '';

  passthru.source = source;
}
