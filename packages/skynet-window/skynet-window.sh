# skynet-window: the night's merge window (docs/plans/autonomy.md → Merges), run at 05:00 on ops by
# modules/window.nix. Every open PR goes through skynet-merge, oldest first, the backup jobs' stacks
# last, then skynet-verify all says how every stack and host is. A dry run until step 6: skynet-merge
# merges nothing, so the window looks at every PR and logs what would have merged; the morning
# digest reads the log. modules/window.nix sets STATE (the window's state and logs) and GH_ENV (the
# bot's token, for gh alone).

[ "$#" = 0 ] || {
  echo "usage: skynet-window   (the night's window; by hand too, as skynet)" >&2
  exit 2
}
# Paused by hand: `touch $STATE/paused` (the agent or Ali); `rm` resumes.
if [ -e "$STATE/paused" ]; then
  echo "skynet-window: paused ($STATE/paused)"
  exit 0
fi
mkdir -p "$STATE/log"
find "$STATE/log" -mindepth 1 -mtime +30 -delete
log=$STATE/log/$(date +%F).txt
exec > >(tee -a "$log") 2>&1

ghx() { (
  set -a
  # shellcheck disable=SC1090 # rendered by sops-nix
  [ -z "${GH_ENV:-}" ] || . "$GH_ENV"
  gh "$@"
); }

echo "# The window, $(date '+%F %H:%M') (a dry run: nothing merges)"
# Oldest first; a PR touching backup or pbs-offsite last, since their verify runs the job.
mapfile -t prs < <(ghx pr list --repo aliammar03/skynet --state open --limit 100 --json number,createdAt,files \
  --jq 'sort_by([any(.files[].path; test("^stacks/[a-z]+/(backup|pbs-offsite)/")), .createdAt]) | .[].number')
would=
for n in "${prs[@]}"; do
  if skynet-merge "$n"; then would="$would #$n"; fi
done
echo
echo "## Would merge:${would:- nothing}"
echo
echo "## Every stack and host, $(date +%H:%M)"
verified=0
skynet-verify all || verified=$?
echo
echo "# Done $(date +%H:%M): would merge${would:- nothing}; skynet-verify all exit $verified"
