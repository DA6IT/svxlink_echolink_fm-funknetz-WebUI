# EchoLink

## Local node

The WebUI displays:
- local EchoLink callsign
- Node ID
- directory status
- module state
- current connections

## EchoLink module

The EchoLink module can be activated and deactivated through the WebUI.

Current pre-release limitation: activation still uses module ID `2` in the control path. Before public release, this must be read dynamically from `ModuleEchoLink.conf`.

## Current connections

The UI distinguishes:
- incoming
- outgoing

Callsign and connection duration are displayed.

## Directory search

Search by:

```text
<CALLSIGN>
<NODE_ID>
```

The backend combines registered node information with currently logged-in EchoLink stations.

States:

### ONLINE
The node exists and is currently logged in.

### BUSY
The node is logged in but currently does not accept a normal new connection.

### OFFLINE
The node is registered but is not currently logged in.

OFFLINE does not mean “node does not exist”.

## Favourites

Stored data:
- display name
- callsign
- Node ID

Current ONLINE/BUSY/OFFLINE state is added when favourites are loaded.

## Connect/disconnect

Online nodes can be connected from search results or favourites. Existing connections can be disconnected from the WebUI.

## History

New EchoLink connections are stored persistently:
- callsign
- direction
- start time
- end time
- duration

Connections that were not recorded before history capture was installed are not reconstructed.

## Event bridge

Original remains untouched:

```text
/usr/share/svxlink/events.d/EchoLink.tcl
```

Local handler:

```text
/usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl
```

Handled events include:
- activating_module
- deactivating_module
- connecting_to
- remote_connected
- connected
- disconnected
- client_list_changed

Raw events:

```text
/var/lib/svxlink/echolink-webui/events.tsv
```

SQLite:

```text
/var/lib/svxlink-webui/echolink.sqlite3
```

## Directory provider

The current implementation uses public EchoLink web sources for Node Lookup and Current Logins. HTML parsing is isolated in the backend.

## Public examples

Do not permanently include third-party real callsigns or Node IDs in README files, documentation, screenshots, placeholders, or demo data.

Suitable examples:

```text
DA6IT-L
DB0XYZ-R
<CALLSIGN>
<NODE_ID>
```
