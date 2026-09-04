{ config, lib, pkgs, ... }:
# SKY-021 P3 — adguard-core (CT 731) as a git-reconstructable NixOS LXC. First real pool CT off the
# Debian community-script path: the AdGuard config now lives in Nix (the new surface vs the ops VM,
# where Arcane owned service config). Day-2 = in-place deploy-rs magic-rollback (P2). Secrets via
# Option C (per-CT age key, injected at provision — scripts/ct-age-identity.sh + docs/design/secrets.md).
#
# The AdGuard config is rendered VERBATIM from the live 731 config through a sops template, so there
# is no nix→yaml translation drift — only the admin password line is a sops placeholder (the hash is
# a dual-recipient secret, never in the store or git plaintext). AdGuard rewrites its own config at
# runtime (filter updates), so the nix-owned rendered file is COPIED into the writable state dir at
# each start: nix is the source of truth, runtime mutations reset on restart (mutableSettings=false
# semantics), and the box rebuilds from git alone.
let
  workDir = "/var/lib/AdGuardHome";
  configFile = "${workDir}/AdGuardHome.yaml";
  # /run/secrets/rendered/AdGuardHome.yaml — the sops-rendered config (hash filled in) copied in below.
  renderedConfig = config.sops.templates."AdGuardHome.yaml".path;
in
{
  imports = [ ../../nix/modules/lxc-base.nix ];

  networking.hostName = "lxc-adguard-core";
  # Unprivileged CT: the local nftables firewall needs caps it doesn't cleanly have, and VLAN 70 is
  # already governed by OPNsense — so no host-local firewall here (the DNS/HTTP ports are reachable
  # by design). AdGuard binds :53 and :80 via CAP_NET_BIND_SERVICE on the service below.
  networking.firewall.enable = false;

  # AdGuard IS the resolver on this box, so systemd-resolved must not hold :53 — its stub listeners
  # (127.0.0.53/54:53) otherwise collide with AdGuard's 0.0.0.0:53 and it can't start. Disable it and
  # give the CT its own upstreams for its OWN outbound lookups (nix, filter-list fetches).
  services.resolved.enable = false;
  networking.nameservers = [ "9.9.9.9" "1.1.1.1" ];

  # Option C: this CT's age identity, injected to keyFile at provision (before the first deploy).
  sops.age.keyFile = "/var/lib/sops-nix/age.key";

  # The admin password hash (bcrypt) — dual-recipient (lab + this CT), substituted into the rendered
  # config by the sops placeholder below. "password stays a sops secret" (lab convention).
  sops.secrets."adguard-admin-hash" = {
    sopsFile = ../../secrets/lxc-adguard-core/admin-password-hash.sops;
    format = "binary";
    owner = "adguardhome";
  };

  # The full AdGuardHome.yaml, rendered at activation to /run/secrets/rendered/ with the hash filled
  # in. Verbatim from live 731 except users[].password → the sops placeholder.
  sops.templates."AdGuardHome.yaml" = {
    owner = "adguardhome";
    content = ''
      http:
        pprof:
          port: 6060
          enabled: false
        doh:
          routes:
            - GET /dns-query
            - POST /dns-query
            - GET /dns-query/{ClientID}
            - POST /dns-query/{ClientID}
          insecure_enabled: false
        address: 0.0.0.0:80
        session_ttl: 30d
      users:
        - name: aliammar
          password: ${config.sops.placeholder."adguard-admin-hash"}
      auth_attempts: 5
      block_auth_min: 15
      http_proxy: ""
      language: ""
      theme: auto
      dns:
        bind_hosts:
          - 0.0.0.0
        port: 53
        anonymize_client_ip: false
        ratelimit: 0
        ratelimit_subnet_len_ipv4: 24
        ratelimit_subnet_len_ipv6: 56
        ratelimit_whitelist: []
        refuse_any: true
        upstream_dns:
          - 1.1.1.1
          - 8.8.8.8
          - 9.9.9.9
          - '[/home.aliammar.net/]10.10.70.1:53053'
        upstream_dns_file: ""
        bootstrap_dns:
          - 9.9.9.10
          - 149.112.112.10
          - 2620:fe::10
          - 2620:fe::fe:10
        fallback_dns: []
        upstream_mode: parallel
        fastest_timeout: 1s
        allowed_clients: []
        disallowed_clients: []
        blocked_hosts:
          - version.bind
          - id.server
          - hostname.bind
        trusted_proxies:
          - 127.0.0.0/8
          - ::1/128
        cache_enabled: true
        cache_size: 33554432
        cache_ttl_min: 0
        cache_ttl_max: 0
        cache_optimistic: true
        cache_optimistic_answer_ttl: 30s
        cache_optimistic_max_age: 12h
        bogus_nxdomain: []
        aaaa_disabled: false
        enable_dnssec: true
        edns_client_subnet:
          custom_ip: ""
          enabled: false
          use_custom: false
        max_goroutines: 300
        handle_ddr: true
        ipset: []
        ipset_file: ""
        bootstrap_prefer_ipv6: false
        upstream_timeout: 1s
        private_networks: []
        use_private_ptr_resolvers: true
        local_ptr_upstreams:
          - 10.10.70.1:53053
        use_dns64: false
        dns64_prefixes: []
        serve_http3: false
        use_http3_upstreams: false
        serve_plain_dns: true
        hostsfile_enabled: true
        pending_requests:
          enabled: true
      tls:
        enabled: false
        server_name: ""
        force_https: false
        port_https: 443
        port_dns_over_tls: 853
        port_dns_over_quic: 853
        port_dnscrypt: 0
        dnscrypt_config_file: ""
        certificate_chain: ""
        private_key: ""
        certificate_path: ""
        private_key_path: ""
        strict_sni_check: false
      querylog:
        dir_path: ""
        ignored: []
        interval: 90d
        size_memory: 1000
        enabled: true
        ignored_enabled: false
        file_enabled: true
      statistics:
        dir_path: ""
        ignored: []
        interval: 1d
        enabled: true
        ignored_enabled: false
      filters:
        - enabled: true
          url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt
          name: AdGuard DNS filter
          id: 1
        - enabled: false
          url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt
          name: AdAway Default Blocklist
          id: 2
        - enabled: true
          url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_27.txt
          name: OISD Blocklist Big
          id: 1784236171
      whitelist_filters: []
      user_rules: []
      dhcp:
        enabled: false
        interface_name: ""
        local_domain_name: lan
        dhcpv4:
          gateway_ip: ""
          subnet_mask: ""
          range_start: ""
          range_end: ""
          lease_duration: 86400
          icmp_timeout_msec: 1000
          options: []
        dhcpv6:
          range_start: ""
          lease_duration: 86400
          ra_slaac_only: false
          ra_allow_slaac: false
      filtering:
        blocking_ipv4: ""
        blocking_ipv6: ""
        blocked_services:
          schedule:
            time_zone: Local
          ids: []
        protection_disabled_until: null
        safe_search:
          enabled: false
          bing: true
          duckduckgo: true
          ecosia: true
          google: true
          pixabay: true
          yandex: true
          youtube: true
        blocking_mode: default
        parental_block_host: family-block.dns.adguard.com
        safebrowsing_block_host: standard-block.dns.adguard.com
        rewrites:
          - domain: '*.aliammar.net'
            answer: 10.10.100.35
            enabled: true
          - domain: opnsense.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: proxmox-network.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: proxmox-core.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: adguard-network.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: adguard-core.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: arcane.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: unraid.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: omada.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: caddy.aliammar.net
            answer: 10.10.60.35
            enabled: true
          - domain: pbs.aliammar.net
            answer: 10.10.60.35
            enabled: true
        safe_fs_patterns:
          - /opt/AdGuardHome/userfilters/*
        max_http_size: 256MB
        safebrowsing_cache_size: 1048576
        safesearch_cache_size: 1048576
        parental_cache_size: 1048576
        cache_time: 30
        filters_update_interval: 24
        blocked_response_ttl: 10
        filtering_enabled: true
        rewrites_enabled: true
        parental_enabled: false
        safebrowsing_enabled: false
        protection_enabled: true
      clients:
        runtime_sources:
          whois: true
          arp: true
          rdns: true
          dhcp: true
          hosts: true
        persistent:
          - safe_search:
              enabled: false
              bing: false
              duckduckgo: false
              ecosia: false
              google: false
              pixabay: false
              yandex: false
              youtube: false
            blocked_services:
              schedule:
                time_zone: Local
              ids: []
            name: Ali's Workstation
            ids:
              - 10.10.10.50
            tags:
              - device_pc
            upstreams: []
            uid: 019f6ccf-c65b-790f-a6ea-ac0b8929515a
            upstreams_cache_size: 0
            upstreams_cache_enabled: false
            use_global_settings: true
            filtering_enabled: false
            parental_enabled: false
            safebrowsing_enabled: false
            use_global_blocked_services: true
            ignore_querylog: false
            ignore_statistics: false
          - safe_search:
              enabled: false
              bing: true
              duckduckgo: true
              ecosia: true
              google: true
              pixabay: true
              yandex: true
              youtube: true
            blocked_services:
              schedule:
                time_zone: Local
              ids: []
            name: Proxmox Core
            ids:
              - 10.10.50.11
            tags: []
            upstreams: []
            uid: 019f772c-05bb-778e-b50a-8edda44fd636
            upstreams_cache_size: 0
            upstreams_cache_enabled: false
            use_global_settings: true
            filtering_enabled: false
            parental_enabled: false
            safebrowsing_enabled: false
            use_global_blocked_services: true
            ignore_querylog: false
            ignore_statistics: false
          - safe_search:
              enabled: false
              bing: true
              duckduckgo: true
              ecosia: true
              google: true
              pixabay: true
              yandex: true
              youtube: true
            blocked_services:
              schedule:
                time_zone: Local
              ids: []
            name: Proxmox Network
            ids:
              - 10.10.50.10
            tags: []
            upstreams: []
            uid: 019f772c-05ef-7525-b826-2e09ef5fbb6e
            upstreams_cache_size: 0
            upstreams_cache_enabled: false
            use_global_settings: true
            filtering_enabled: false
            parental_enabled: false
            safebrowsing_enabled: false
            use_global_blocked_services: true
            ignore_querylog: false
            ignore_statistics: false
      log:
        enabled: true
        file: ""
        max_backups: 0
        max_size: 100
        max_age: 3
        compress: false
        local_time: false
        verbose: false
      os:
        group: ""
        user: ""
        rlimit_nofile: 0
      schema_version: 34
    '';
  };

  users.users.adguardhome = {
    isSystemUser = true;
    group = "adguardhome";
    home = workDir;
  };
  users.groups.adguardhome = { };

  # Plain service (not services.adguardhome): the module writes `settings` into the store and runs as
  # a DynamicUser, neither of which lets the admin hash come from a runtime sops secret. So we own the
  # unit: copy the nix-rendered config into the writable state at each start, then run AdGuard on it.
  systemd.services.adguardhome = {
    description = "AdGuard Home (Skynet-managed; config from sops template)";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    serviceConfig = {
      User = "adguardhome";
      Group = "adguardhome";
      StateDirectory = "AdGuardHome";
      StateDirectoryMode = "0700"; # AdGuard warns if the work dir is group/world-readable
      WorkingDirectory = workDir;
      # nix is the source of truth: re-seed the writable config from the rendered template each start.
      ExecStartPre = "${pkgs.coreutils}/bin/install -m 0600 ${renderedConfig} ${configFile}";
      ExecStart = "${lib.getExe pkgs.adguardhome} --no-check-update --work-dir ${workDir} --config ${configFile}";
      AmbientCapabilities = [ "CAP_NET_BIND_SERVICE" ]; # bind :53 and :80
      CapabilityBoundingSet = [ "CAP_NET_BIND_SERVICE" ];
      Restart = "always";
      RestartSec = 10;
    };
  };

  system.stateVersion = "26.05";
}
