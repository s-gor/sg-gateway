# sg-hostd

`sg-hostd` is the small host-side helper for SG-Gateway.

It must expose only explicit, allow-listed operations, for example:

- AmneziaWG status
- AmneziaWG apply
- AmneziaWG restart
- nftables apply
- sysctl apply
- certificate reload
- backup create
- diagnostics collect

It must never provide arbitrary shell execution to the web panel.
