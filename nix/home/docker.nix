{ pkgs, lib, ... }:
# The docker-dmz remote context (over SSH as svc-ops, in its docker group): `skynet collect docker`
# reads through it (T1) and `skynet deploy` writes through it (T2). Declarative + idempotent so it
# survives a reprovision; created at home-manager activation — `docker context create` only writes
# ~/.docker, it doesn't contact the daemon. An existing context keeps its old description.
{
  home.activation.dockerDmzContext = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    if ! ${pkgs.docker}/bin/docker context inspect docker-dmz >/dev/null 2>&1; then
      ${pkgs.docker}/bin/docker context create docker-dmz \
        --docker host=ssh://svc-ops@10.10.100.15 \
        --description "Skynet docker-dmz (svc-ops)" || true
    fi
  '';
}
