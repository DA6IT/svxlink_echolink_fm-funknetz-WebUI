# Sicherheit

Die SvxLink WebUI kann reale Steuerfunktionen ausführen.

Dazu gehören zum Beispiel Talkgroup-Wechsel und EchoLink-Verbindungen.

Deshalb sollte der Zugriff auf die WebUI geschützt werden.

## Anmeldung

Der Installer richtet standardmäßig einen Benutzernamen und ein Passwort für die komplette WebUI ein.

Ohne gültige Zugangsdaten ist kein Zugriff möglich.

## Lokales Netzwerk

In einem vertrauenswürdigen Heim- oder Funknetz kann die WebUI direkt über HTTP verwendet werden.

## Zugriff aus dem Internet

Die WebUI sollte nicht ungeschützt direkt aus dem Internet erreichbar sein.

Empfohlen werden zum Beispiel:

- VPN
- Firewall oder IP-Allowlist
- Reverse Proxy mit HTTPS
- vorgeschaltetes SSO

## Backend

Das eigentliche Backend lauscht nur lokal auf dem Server.

Externe Browser greifen über Apache auf die WebUI und die API zu.

## Updates

Updates werden von einem getrennten Updater-Prozess installiert.

Der WebUI-Prozess selbst erhält dafür keine Root- oder sudo-Rechte.

Vor der Aktivierung eines Updates werden Prüfungen durchgeführt.

Schlägt ein Update fehl, kann der vorherige Stand automatisch wiederhergestellt werden.

## Zugangsdaten

Passwörter, Auth Keys, API-Tokens und private Schlüssel gehören nicht in Git oder andere öffentlich zugängliche Dateien.

Die während der Installation gespeicherten Zugangsdaten werden nur lokal auf dem System abgelegt.
