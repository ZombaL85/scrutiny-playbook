# scrutiny-playbook

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

Supported operating systems (both roles):

* Debian 11 or above
* Ubuntu 22.04 or above
* RHEL / Rocky Linux / AlmaLinux 8 or above

## Getting Started

* Check out a copy of this repository.

```
git clone https://github.com/Zorlin/scrutiny-playbook.git
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

* Create and encrypt the secrets file (InfluxDB token and initial admin password):

```
cp group_vars/all/vault.yml.example group_vars/all/vault.yml
$EDITOR group_vars/all/vault.yml        # e.g. token from: openssl rand -hex 32
ansible-vault encrypt group_vars/all/vault.yml
```

* Optionally preview the changes, then run the playbook:

```
ansible-playbook site.yml --ask-vault-pass --check --diff
ansible-playbook site.yml --ask-vault-pass
```

  Add `--ask-become-pass` if your user needs a sudo password.

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

### Upgrading Scrutiny

Set `scrutiny_version` and add the SHA256 digests of the new release assets to `scrutiny_checksums` (they are listed next to each asset on the GitHub release page), then re-run the playbook. Changed binaries are re-downloaded and the services restarted.

### Upgrading from an older version of this playbook

* Binaries now live in `/usr/local/bin` (SELinux-friendly); the old ones in `/opt/scrutiny/bin` are removed.
* The collector cron entry is replaced by a systemd timer.
* The Galaxy roles (`zorlin.influxdb2`, `zorlin.smartmontools`, `geerlingguy.*`) are no longer used.
* Older deployments onboarded InfluxDB with Scrutiny's built-in default token, so set `scrutiny_influxdb_token: "scrutiny-default-admin-token"` in your vault (or rotate the token in InfluxDB first) - otherwise Scrutiny can't connect to the existing database.

## Demo
[![asciicast](https://asciinema.org/a/493531.svg)](https://asciinema.org/a/493531)

## Credits
scrutiny-playbook was created in 2020 by [Benjamin Arntzen](https://github.com/Zorlin).
