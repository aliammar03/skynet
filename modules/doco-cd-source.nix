# What doco-cd deploys from, in a file of its own so that it's code-owned (.github/CODEOWNERS), as
# comin's branch is in base.nix: a branch the agent can push never reaches a host.
{
  url = "https://github.com/aliammar03/skynet.git";
  reference = "main";
}
