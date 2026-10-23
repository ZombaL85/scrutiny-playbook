# scrutiny-playbook

[![CI](https://github.com/ZombaL85/scrutiny-playbook/actions/workflows/ci.yml/badge.svg)](https://github.com/ZombaL85/scrutiny-playbook/actions/workflows/ci.yml)

This is an Ansible-based installer for [Scrutiny](https://github.com/AnalogJ/scrutiny), allowing you to monitor SMART data for a fleet of machines, large or small, and have some idea of when drives are experiencing issues.

It supports both all-in-one and hub-and-spoke deployments, and most popular architectures (amd64, arm64, armv7, armv6).

## What it deploys

* **Hub** (`scrutiny_web`): InfluxDB 2.x from the official InfluxData repository (bound to `127.0.0.1` by default) and the Scrutiny web UI/API as the `scrutiny-web` systemd service.
* **Collectors** (`scrutiny_collector`): `smartmontools` and the Scrutiny collector, run by the `scrutiny-collector.timer` systemd timer (daily at 01:00 by default).

All release downloads are verified against pinned SHA256 digests.

## Requirements

* `ansible-core` 2.15 or newer on the control machine. No Galaxy roles or collections are needed.
* One machine to act in the "hub"/"web" role.
* One or many machines to monitor.
* systemd on all managed hosts.

Supported operating systems (both roles). CI tests every push on Debian, Ubuntu and Rocky Linux images
(the other EL distributions are covered as binary-compatible with Rocky):

| Distribution | Versions |
|---|---|
| Debian (incl. Raspberry Pi OS, Proxmox VE) | 12 (bookworm), 13 (trixie) |
| Ubuntu LTS | 22.04, 24.04, 26.04 |
| RHEL / Rocky Linux / AlmaLinux / Oracle Linux | 10 |
| CentOS Stream | 10 |

Other Debian- or Red Hat-family systems (e.g. EL8/EL9, Debian 11, non-LTS Ubuntu, Fedora) are not tested and only trigger a warning;
set `scrutiny_allow_untested_platforms: false` to make them fail instead. The list lives in
`scrutiny_tested_platforms` in `group_vars/all/main.yml`.

## Getting Started

* Check out a copy of this repository.

```
git clone https://github.com/ZombaL85/scrutiny-playbook.git
cd scrutiny-playbook
```

* Edit the `inventory` file. Place one machine in the "scrutiny_web" section, then list all the machines you wish to run collectors on in the "scrutiny_collector" section. For a single machine, simply put the same machine into both sections.

```
[scrutiny_web]
blinky.windowpa.in

[scrutiny_collector]
blinky.windowpa.in
pinky.windowpa.in
inky.windowpa.in
```

* Create and encrypt the secrets file (InfluxDB token, Healthchecks ping key):

```
cp group_vars/all/vault.yml.example group_vars/all/vault.yml
$EDITOR group_vars/all/vault.yml        # e.g. token from: openssl rand -hex 32
ansible-vault encrypt group_vars/all/vault.yml
```

  Later edits: `ansible-vault edit group_vars/all/vault.yml`. To avoid typing the password on every run,
  keep it in a file outside the repo and point Ansible at it:

```
mkdir -p ~/.ansible && install -m 600 /dev/null ~/.ansible/scrutiny.vault-pass && $EDITOR ~/.ansible/scrutiny.vault-pass
export ANSIBLE_VAULT_PASSWORD_FILE=~/.ansible/scrutiny.vault-pass
```

  `group_vars/all/vault.yml` is git-ignored because this repository is public. Enable the pre-commit hook
  that blocks unencrypted vault files with `git config core.hooksPath .githooks`.

* Optionally preview the changes, then run the playbook:

```
ansible-playbook site.yml --ask-vault-pass --check --diff
ansible-playbook site.yml --ask-vault-pass
```

  Drop `--ask-vault-pass` when `ANSIBLE_VAULT_PASSWORD_FILE` is set. Add `--ask-become-pass` if your user needs a sudo password.

* Visit `http://<hub>:8080`. Collectors must be able to reach the hub on TCP 8080 - open that port in your firewall if needed.

## Configuration

Common variables (see `group_vars/all/main.yml` and `roles/*/defaults/main.yml` for all of them):

| Variable | Default | Description |
|---|---|---|
| `scrutiny_version` | `v0.9.5` | Scrutiny release to install |
| `scrutiny_web_port` | `8080` | Web UI/API port |
| `scrutiny_influxdb_install` | `false` | `true` = install InfluxDB on the hub; `false` = use an existing InfluxDB 2.x (`scrutiny_influxdb_host`, `_port`, `_org`, `_bucket` + token in the vault) |
| `scrutiny_collector_schedule` | `*-*-* 01:00:00` | systemd `OnCalendar` for the collector |
| `scrutiny_collector_host_id` | inventory hostname | Label used to group drives per host in the dashboard |
| `scrutiny_notify_urls` | `[]` | [Shoutrrr](https://shoutrrr.nickfedor.com/services/overview/) notification URLs |

### Healthchecks monitoring

Collector runs can report to [Healthchecks](https://healthchecks.io) (hosted or self-hosted). Every run pings
`<base_url>/<ping_key>/<slug>/start`, then `/<exit status>` with the run's log as the body, so a failed run
shows the error and a missed run raises an alert.

```yaml
# group_vars/all/main.yml
scrutiny_healthchecks_enabled: true
scrutiny_healthchecks_base_url: "http://healthchecks.example.lan:8000/ping"
# group_vars/all/vault.yml
scrutiny_healthchecks_ping_key: "<project ping key>"
```

The slug defaults to `scrutiny_<hostname>` (override per host with `scrutiny_healthchecks_slug` in `host_vars`).
Missing checks are created on the first ping (`scrutiny_healthchecks_auto_create`). Each check's schedule must
match `scrutiny_collector_schedule` - for the default daily run at 01:00 that is cron `0 1 * * *` with a grace time
above the 15 minute randomized delay, e.g. 30 minutes.

To let the playbook set this up, add a read-write project API key (Project Settings -> API Access) to the vault.
The check is then created or updated from the control node whenever its schedule, grace or time zone differ:

```yaml
# group_vars/all/main.yml
scrutiny_healthchecks_api_url: "http://healthchecks.example.lan:8000/api/v3"
# group_vars/all/vault.yml
scrutiny_healthchecks_api_key: "<read-write API key>"
# host_vars/<host>.yml - e.g. an hourly collector
scrutiny_collector_schedule: hourly
scrutiny_healthchecks_schedule: "0 * * * *"
```

| Variable | Default | Description |
|---|---|---|
| `scrutiny_healthchecks_api_url` | `https://healthchecks.io/api/v3` | Management API base URL |
| `scrutiny_healthchecks_schedule` | `0 1 * * *` | Check's cron schedule |
| `scrutiny_healthchecks_grace` | `1800` | Grace time in seconds |
| `scrutiny_healthchecks_tz` | `""` (host's time zone) | IANA time zone of the schedule |

### Upgrading Scrutiny

Set `scrutiny_version` (e.g. `-e scrutiny_version=v0.9.6`) and re-run the playbook. Changed binaries are re-downloaded and the services restarted.

Downloads are always checked against SHA256 digests. Digests pinned in `scrutiny_checksums` are used first; for any other
version they are taken from the GitHub release (`scrutiny_checksums_from_github`, default `true` - GitHub computes them
for every uploaded asset). To allow only reviewed versions, set it to `false` and pin the digests of each new release in
`scrutiny_checksums` (they are listed next to each asset on the GitHub release page).

### Upgrading from an older version of this playbook

* Binaries now live in `/usr/local/bin` (SELinux-friendly); the old ones in `/opt/scrutiny/bin` are removed.
* The collector cron entry is replaced by a systemd timer.
* The Galaxy roles (`zorlin.influxdb2`, `zorlin.smartmontools`, `geerlingguy.*`) are no longer used.
* Older deployments onboarded InfluxDB with Scrutiny's built-in default token, so set `scrutiny_influxdb_token: "scrutiny-default-admin-token"` in your vault (or rotate the token in InfluxDB first) - otherwise Scrutiny can't connect to the existing database.

## Demo
[![asciicast](https://asciinema.org/a/493531.svg)](https://asciinema.org/a/493531)

## Credits
scrutiny-playbook was created in 2020 by [Benjamin Arntzen](https://github.com/Zorlin).
