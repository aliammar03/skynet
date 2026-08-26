{ pkgs, lib, ... }:
# The docker-dmz remote context (read-only, over SSH as svc-ops) that collect-docker.sh uses for its
# T1 snapshots. Declarative + idempotent so it survives a reprovision; created at home-manager
# activation — `docker context create` only writes ~/.docker, it doesn't contact the daemon. The
# other docker-dmz paths (envsync.sh, gitops-deploy.sh) go straight over SSH with the agent key and
# need no context. Endpoint is the docker-dmz host (svc-ops is in its docker group).
{
  home.activation.dockerDmzContext = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    if ! ${pkgs.docker}/bin/docker context inspect docker-dmz >/dev/null 2>&1; then
      ${pkgs.docker}/bin/docker context create docker-dmz \
        --docker host=ssh://svc-ops@10.10.100.15 \
        --description "Skynet docker-dmz (read-only, svc-ops)" || true
    fi
  '';
}
