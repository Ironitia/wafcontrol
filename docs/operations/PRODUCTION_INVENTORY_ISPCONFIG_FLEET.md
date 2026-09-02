# ISPConfig WAFControl production fleet

Last validated: 2026-09-02 (Europe/Paris)

## Scope

| Node | Public address | Operating system | Web server | WAFControl URL |
| --- | --- | --- | --- | --- |
| ISPConfig 1 | `46.28.168.135` | Ubuntu 24.04 | Apache 2.4.58 | `https://ispconfig.w3tel.net:7000/` |
| ISPConfig 2 | `46.28.168.136` | Ubuntu 24.04 | Apache 2.4.58 | `https://ispconfig2.w3tel.net:7000/` |
| ISPConfig 3 | `46.28.168.155` | Ubuntu 22.04 | Apache 2.4.52 | `https://ispconfig3.w3tel.net:7000/` |

The deployed application revision is `5967848088c589b26dcf50fb0d1de35d8bb0db48`.
Administrative HTTPS access to TCP/7000 is allowed only from `2.136.9.164`.
This restriction exists both in Apache (`Require ip`) and an nftables input chain.

## Protection mode and event path

- ModSecurity is enabled globally for Apache virtual hosts.
- CRS 4.29.0 is active in `DetectionOnly` during the observation period.
- The ISPConfig interface on TCP/8080 is explicitly `DetectionOnly`.
- The WAFControl administration virtual host on TCP/7000 has ModSecurity disabled
  to avoid ingesting the dashboard's own traffic.
- WAFControl parses Apache audit and error logs every 10 seconds.
- Newly persisted alerts are written to `/run/wafcontrol-rsyslog/syslog.sock`.
- Rsyslog forwards only the WAFControl ruleset to `46.28.168.76:514/TCP`, using
  an on-disk retry queue and RFC3164 framing.
- MapAttack receives the sensor address, rule, classification, priority, protocol,
  source address/port and destination address/port.

## Installed components

- Application: `/opt/WafControl`
- Environment: `/opt/WafControl/.env` (mode 0600)
- Local administrator hand-off: `/root/.wafcontrol_credentials` (mode 0600)
- PostgreSQL database and role: `wafcontrol`
- Redis: local system service
- Gunicorn socket: `/run/wafcontrol/gunicorn.sock`
- WAF policy: `/etc/modsecurity/wafcontrol/`
- CRS: `/etc/modsecurity/crs/coreruleset-4.29.0/`
- Audit log: `/var/log/apache2/modsec_audit.log`
- Rsyslog input: `/etc/rsyslog.d/60-wafcontrol-mapattack.conf`
- Rsyslog runtime creation: `/etc/tmpfiles.d/wafcontrol-rsyslog.conf`
- Rsyslog AppArmor rule (Ubuntu 24.04): `/etc/apparmor.d/rsyslog.d/wafcontrol`
- Port restriction: `/etc/nftables.d/wafcontrol-admin.nft`
- Application backups: `/var/backups/wafcontrol/`
- Celery Beat state: `/var/lib/wafcontrol/celerybeat-schedule`

The enabled services are `wafcontrol`, `wafcontrol-celery-worker`,
`wafcontrol-celery-beat`, `wafcontrol-backup.timer`, and
`wafcontrol-firewall`, in addition to Apache, PostgreSQL, Redis, and rsyslog.
ISPConfig 2 uses Celery worker concurrency 2 because it has 4 GiB RAM.

## Ubuntu 22.04 engine exception

Ubuntu 22.04 provides ModSecurity 2.9.5, which cannot load CRS 4.29 because it
lacks `MULTIPART_PART_HEADERS`. ISPConfig 3 therefore runs ModSecurity 2.9.14,
built from the upstream `v2.9.14` tag with its libinjection submodule.
The source tree is `/usr/local/src/ModSecurity-2.9.14-git`. The distribution
module was preserved as:

`/usr/lib/apache2/modules/mod_security2.so.pre-wafcontrol-2.9.5-20260902`

Do not let a package reinstall silently replace the 2.9.14 module. After Apache
or ModSecurity package maintenance, check the producer version and run the CRS
probe below before returning traffic to service.

## Validation checklist

Run on every node:

```bash
apache2ctl configtest
systemctl is-active apache2 postgresql redis-server rsyslog \
  wafcontrol wafcontrol-celery-worker wafcontrol-celery-beat \
  wafcontrol-backup.timer wafcontrol-firewall.service
test -S /run/wafcontrol-rsyslog/syslog.sock
test "$(systemctl show -p Result --value wafcontrol-backup.service)" = success
```

From `2.136.9.164`, the WAFControl URL must return a login redirect. From any
other address, TCP/7000 must time out. A safe non-blocking local probe is:

```bash
curl -ksS -A Nikto -o /dev/null https://PUBLIC_IP:8080/.env
sleep 12
journalctl -u wafcontrol-celery-worker --since '-1 minute' --no-pager \
  | grep 'WAF ingestion apache'
```

Expected: HTTP 404 or the application's normal response, `created` alerts,
`errors=0`, then `created=0` on the next cycle. Confirm matching RFC3164 records
under `/var/log/network/PUBLIC_IP/` on MapAttack.

## Backups and rollback

Before deployment, each VM received a crash-consistent vSphere snapshot named
`pre-wafcontrol-20260902`. Each node also has a verified configuration archive
under `/root/pre-wafcontrol-20260902/`.

Prefer configuration rollback before reverting the whole VM:

1. Stop and disable the five `wafcontrol*` units.
2. Disable `wafcontrol-admin` and `wafcontrol-listen`, then validate Apache.
3. Restore the configuration archive from `/root/pre-wafcontrol-20260902/`.
4. Validate and reload Apache, rsyslog and nftables.
5. If the node cannot be recovered safely, revert the corresponding vSphere
   snapshot and verify ISPConfig, hosted sites, mail/DNS roles, and monitoring.

Do not remove the snapshots until the 7-to-14-day observation and exclusion
period has completed and a restore rehearsal has succeeded.

## Observation period

Keep all nodes in `DetectionOnly` through at least 2026-09-16. Review events by
application, URI, rule and source; create narrow application-specific exclusions;
then promote selected virtual hosts to blocking only after their false-positive
rate and rollback procedure are accepted.
