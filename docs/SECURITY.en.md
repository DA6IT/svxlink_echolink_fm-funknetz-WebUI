# Security

SvxLink WebUI can perform real control actions.

These include changing talkgroups and controlling EchoLink connections.

Access to the WebUI should therefore be protected.

## Login

The installer configures a username and password for the complete WebUI by default.

Access is not possible without valid credentials.

## Local network

On a trusted home or radio network, the WebUI can be used directly over HTTP.

## Internet access

Do not expose the WebUI directly to the internet without additional protection.

Recommended options include:

- VPN
- firewall or IP allowlist
- HTTPS reverse proxy
- SSO

## Backend

The backend itself only listens locally on the server.

External browsers access the WebUI and API through Apache.

## Updates

Updates are installed by a separate updater process.

The WebUI process itself does not receive root or sudo privileges.

Checks are performed before an update is activated.

If an update fails, the previous version can be restored automatically.

## Credentials

Passwords, authentication keys, API tokens, and private keys must not be stored in Git or other public files.

Credentials entered during installation are stored locally on the system.
