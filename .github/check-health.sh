#!/usr/bin/env bash
# Every long-running service shows its health, so verify can see a bad update
# (docs/plans/autonomy.md → Verify and roll back): a healthcheck in its compose.yaml, or its image's
# own, read from the registry, so a Renovate bump is checked with the image it brings. A service
# with neither says why in `x-no-healthcheck: <why>` (compose ignores x- keys, and they leave its
# config hash alone). A job (a doco-cd job) needs none. Run from the repo's root, by CI and by hand,
# with skopeo on the PATH; it reads only the images it has to.
set -uo pipefail
fail=0
err() { echo "::error file=$1::$2"; fail=1; }
fix="add one, or say why there is none in x-no-healthcheck (stacks/README.md → The folder)"

for f in stacks/*/*/compose.yaml; do
  d=${f%/compose.yaml}
  c=$(yq -o=json 'explode(.)' "$f" 2>/dev/null) || continue # check-layout.sh reports it
  # Each service that needs a look: its name, then its image, or why there's none to read.
  while IFS=$'\t' read -r svc img; do
    case "$img" in
    built) err "$f" "$d: service $svc is built here, so its image has no check to read: $fix" ;;
    disabled) err "$f" "$d: service $svc turns its healthcheck off: $fix" ;;
    *)
      # skopeo takes a name with a digest, not a tag as well.
      ref=$(sed -E 's#:[^:/@]+@#@#' <<<"$img")
      if ! cfg=$(skopeo inspect --retry-times 3 --config --raw --override-os linux --override-arch amd64 "docker://$ref"); then
        err "$f" "$d: can't read $img's config from its registry"
      elif ! jq -e '(.config.Healthcheck.Test // []) | length > 0 and .[0] != "NONE"' <<<"$cfg" >/dev/null; then
        err "$f" "$d: service $svc has no healthcheck, in compose.yaml or in its image: $fix"
      fi
      ;;
    esac
  done < <(jq -r '
    def job: (.labels // {}) | if type == "array" then any(.[]; test("^cd\\.doco\\.job\\.enabled=\"?true"))
      else ((."cd.doco.job.enabled" // "") | tostring) == "true" end;
    # A test is a list, or a string for CMD-SHELL.
    def off: (.healthcheck.disable == true)
      or ((.healthcheck.test // []) | type == "array" and length > 0 and .[0] == "NONE");
    .services // {} | to_entries[] | .key as $n | .value
    | select((job | not) and ((."x-no-healthcheck" // "") | length == 0))
    | if off then [$n, "disabled"]
      elif (.healthcheck.test // []) | length > 0 then empty
      elif .build then [$n, "built"]
      else [$n, .image] end
    | @tsv' <<<"$c")
done

exit $fail
