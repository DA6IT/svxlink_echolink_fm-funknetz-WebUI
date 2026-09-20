# Privacy and public examples

## Principle

The WebUI processes amateur-radio live data such as callsigns, Node IDs, timestamps, and connection information.

This data may be displayed during real operation. Static public examples should follow stricter rules.

## Do not permanently embed

Avoid fixed public examples containing:
- randomly observed third-party callsigns
- third-party EchoLink Node IDs
- third-party last-heard data
- third-party connection history
- unnecessary personal live data in screenshots

## Suitable examples

Own project/operator data may be used:

```text
DA6IT
DA6IT-L
```

Generic examples:

```text
DB0XYZ-R
YOURCALL-L
<CALLSIGN>
<NODE_ID>
<TALKGROUP>
```

## UI placeholders

Do not hard-code random real third-party callsigns in source placeholders.

Prefer:

```text
Callsign or Node ID
```

or, if an example is useful:

```text
e.g. DA6IT-L or 123456
```

## Screenshots

Before publishing, check for:
- third-party callsigns
- third-party Node IDs
- history/last-heard data
- internal hostnames/IP addresses
- credentials

Anonymize unnecessary data.

## Repository

Live data should not be copied into tests, demo data, or documentation merely because it was visible during development.
