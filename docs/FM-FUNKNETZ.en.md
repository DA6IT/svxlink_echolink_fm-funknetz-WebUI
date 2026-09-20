# FM-Funknetz

## Live activity

The WebUI processes current voice activity through MQTT.

Typical data:
- talkgroup
- callsign
- start/stop
- server
- timestamp

## Active talkgroups

Active talkgroups automatically appear with:
- TG number
- TG name
- current callsign
- activity state

## Favourites

Talkgroups can be saved as favourites and remain visible even without current activity.

## Control

Talkgroup selection is performed through the SvxLink DTMF Control PTY.

A talkgroup is only shown as locally connected after SvxLink confirms the state.

## Leaving a talkgroup

The active talkgroup can be left. SvxLink then returns to its configured default state.

## Top Talkgroups

Ranges:

```text
24 hours
7 days
30 days
```

Displayed data includes:
- talkgroup
- talkgroup name
- callsign count
- session count
- voice duration

## Buddy/node data

Additional FM-Funknetz node information can be evaluated. Buddy searches use base callsigns so technical suffixes can be handled.

## Public examples

Do not permanently include randomly observed third-party callsigns in screenshots, README files, or demo data.

Suitable examples:

```text
DA6IT
<CALLSIGN>
<TALKGROUP>
```
