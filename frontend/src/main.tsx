import { useRef } from 'react';
import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import UpdateCenter from './components/UpdateCenter';

type Event = {
  event: string;
  callsign: string;
  timestamp: string;
};

type RfEvent = {
  kind: 'tx' | 'rx';
  state: boolean | boolean[] | null;
  sql_open?: boolean | boolean[];
  active?: boolean | boolean[];
  siglev?: number | number[];
  timestamp?: string;
};

type LocalLog = {
  available: boolean;
  source: string;
  rx: {
    squelch: 'open' | 'closed' | null;
    level: number | null;
    timestamp: string | null;
  };
  talkgroup: {
    tg: string;
    timestamp: string;
  } | null;
  talker: {
    tg: string;
    callsign: string;
    timestamp: string;
  } | null;
  updated_at: string | null;
};

type Status = {
  node: Record<string, string | number>;
  svxlink: {
    status: string;
    pid: number | null;
    substate: string;
  };
  reflector: {
    events: Event[];
    count: number;
    last_heard: Event | null;
    available: boolean;
  };
  rf: {
    available: boolean;
    tx: RfEvent | null;
    rx: RfEvent | null;
    reason: string;
  };
  local_log: LocalLog;
  events: {
    enabled: boolean;
    available: boolean;
    reason: string;
  };
  config: Record<string, Record<string, string>>;
  demo: boolean;
  updated_at: string;
};

type LiveEntry = {
  call: string;
  tg: string;
  server?: string;
  time?: string;
};

type TalkgroupsResponse = {
  active: string | null;
  confirmed: boolean;
  external: {
    available: boolean;
    source?: string;
    active?: {
      call: string;
      tg: string;
    } | null;
    client_count?: number | null;
    live?: LiveEntry[];
    last_heard?: {
      call: string;
      tg: string;
    }[];
    reason: string;
  };
  control: {
    enabled: boolean;
    reason: string;
  };
  using_default?: boolean | null;

};

type ShariHardware = {
  available: boolean;
  read_only: boolean;
  port: string;
  baudrate: number;
  module?: string;
  firmware?: string;
  firmware_raw?: string;
  tx_frequency_mhz?: string;
  rx_frequency_mhz?: string;
  bandwidth_khz?: number | null;
  bandwidth_raw?: string;
  tx_cxcss_code?: string;
  tx_cxcss_label?: string;
  rx_cxcss_code?: string;
  rx_cxcss_label?: string;
  squelch?: number;
  source?: string;
  updated_at?: string;
  reason?: string;
};

type View =
  | 'overview'
  | 'fm'
  | 'echolink'
  | 'shari'
  | 'svxlink-config'
  | 'system';

type TgView =
  | 'all'
  | 'favorites';

type TalkgroupItem = {
  tg: string;
  calls: string[];
  server?: string;
  time?: string;
  connected: boolean;
  active: boolean;
};


type NodeVariant = {
  call: string;
  online: boolean;
  online_servers?: string[];
  known_servers?: string[];
  tg?: string;
  talk_active?: boolean;
  talk_tg?: string;
  location?: string;
  sysop?: string;
  node_last_seen?: string | number | null;
  last_activity?: {
    call?: string;
    tg?: string;
    last_seen?: string | null;
    last_seen_epoch?: number | null;
  } | null;
};

type ActivityRecord = {
  found: boolean;
  active: boolean;
  online?: boolean;
  call?: string;
  base_call?: string;
  active_call?: string | null;
  last_call?: string | null;
  last_tg?: string | null;
  online_calls?: string[];
  variants?: NodeVariant[];
  tg?: string;
  talk?: string;
  server?: string;
  source_time?: string;
  last_seen?: string | null;
  last_seen_epoch?: number | null;
};

const relativeAge = (
  epoch?: number | null
) => {
  if (!epoch) {
    return 'noch nie';
  }

  const seconds = Math.max(
    0,
    Math.floor(
      Date.now() / 1000 - epoch
    )
  );

  if (seconds < 15) {
    return 'gerade eben';
  }

  if (seconds < 60) {
    return `vor ${seconds} Sek.`;
  }

  const minutes =
    Math.floor(
      seconds / 60
    );

  if (minutes < 60) {
    return `vor ${minutes} Min.`;
  }

  const hours =
    Math.floor(
      minutes / 60
    );

  if (hours < 24) {
    return `vor ${hours} Std.`;
  }

  const days =
    Math.floor(
      hours / 24
    );

  return `vor ${days} Tag${
    days === 1 ? '' : 'en'
  }`;
};

const callMatchesBuddy = (
  value: string,
  baseValue: string
) => {
  const call =
    String(value || '')
      .trim()
      .toUpperCase();

  const base =
    String(baseValue || '')
      .trim()
      .toUpperCase();

  if (!call || !base) {
    return false;
  }

  return (
    call === base ||
    call.startsWith(
      `${base}-`
    ) ||
    call.startsWith(
      `${base}/`
    ) ||
    call.endsWith(
      `/${base}`
    ) ||
    call.includes(
      `/${base}-`
    ) ||
    call.includes(
      `/${base}/`
    )
  );
};

const api = '/api';

const value = (
  obj: Record<string, unknown>,
  ...keys: string[]
) =>
  keys
    .map((key) => obj[key])
    .find(
      (entry) =>
        entry !== undefined &&
        entry !== null &&
        entry !== ''
    ) as string | number | undefined;

const boolActive = (
  state: RfEvent['state'] | undefined
) =>
  Array.isArray(state)
    ? state.some(Boolean)
    : state === true;

function StatusDot({
  active,
}: {
  active: boolean;
}) {
  return (
    <span
      className={`status-dot ${
        active ? 'is-active' : ''
      }`}
    />
  );
}

function Tag({
  children,
  type = 'neutral',
}: {
  children: React.ReactNode;
  type?:
    | 'neutral'
    | 'green'
    | 'cyan';
}) {
  return (
    <span className={`tag tag-${type}`}>
      {children}
    </span>
  );
}

function EmptyValue({
  children = 'Nicht verfügbar',
}: {
  children?: React.ReactNode;
}) {
  return (
    <span className="empty-value">
      {children}
    </span>
  );
}

function App() {

  const [tgNames, setTgNames] =
    useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;

    fetch(
      '/api/talkgroups/names',
      {
        cache: 'no-store',
      }
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            'TG-Namen konnten nicht geladen werden'
          );
        }

        return response.json();
      })
      .then((data) => {
        if (
          cancelled ||
          !data ||
          typeof data.names !== 'object'
        ) {
          return;
        }

        setTgNames(
          data.names
        );
      })
      .catch(() => {
        /*
         * Bei einem Fehler bleibt die WebUI
         * vollständig benutzbar und zeigt
         * lediglich die TG-Nummer.
         */
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const tgLabel = (
    value:
      | string
      | number
      | null
      | undefined
  ) => {
    const raw =
      String(value ?? '')
        .trim();

    if (!raw) {
      return 'TG —';
    }

    const key =
      /^\d+$/.test(raw)
        ? String(
            Number(raw)
          )
        : raw;

    const name =
      tgNames[key];

    return name
      ? `TG ${raw} · ${name}`
      : `TG ${raw}`;
  };


  const [status, setStatus] =
    useState<Status | null>(null);

  const [talkgroups, setTalkgroups] =
    useState<TalkgroupsResponse | null>(
      null
    );

  const [view, setView] =
    useState<View>('overview');

  // --- SHARI HARDWARE READ-ONLY V1 ---

  const [
    shariHardware,
    setShariHardware,
  ] = useState<ShariHardware | null>(
    null
  );

  const [
    shariHardwareBusy,
    setShariHardwareBusy,
  ] = useState(false);

  const [
    shariHardwareError,
    setShariHardwareError,
  ] = useState('');

  const loadShariHardware =
    async () => {

      setShariHardwareBusy(
        true
      );

      setShariHardwareError(
        ''
      );

      try {

        const response =
          await fetch(
            `${api}/shari/hardware`,
            {
              cache:
                'no-store',
            }
          );

        const data:
          ShariHardware =
            await response.json();

        if (
          !response.ok ||
          !data.available
        ) {
          throw new Error(
            data.reason ||
            'SHARI-Funkmodul nicht erreichbar.'
          );
        }

        setShariHardware(
          data
        );

      } catch (error) {

        setShariHardware(
          null
        );

        setShariHardwareError(
          error instanceof Error
            ? error.message
            : 'SHARI-Funkmodul konnte nicht ausgelesen werden.'
        );

      } finally {

        setShariHardwareBusy(
          false
        );

      }
    };

  useEffect(() => {

    if (
      view !== 'shari'
    ) {
      return;
    }

    void loadShariHardware();

  }, [view]);

  // --- TOP TALKGROUPS STATE ---

  const [
    topTalkgroupsByRange,
    setTopTalkgroupsByRange,
  ] = useState<
    Record<
      '24h' | '7d' | '30d',
      any[]
    >
  >({
    '24h': [],
    '7d': [],
    '30d': [],
  });

  const [
    topTalkgroupsLoading,
    setTopTalkgroupsLoading,
  ] = useState(
    false
  );

  const [
    topTalkgroupsError,
    setTopTalkgroupsError,
  ] = useState<string | null>(
    null
  );



  // --- ECHOLINK WEBUI STATE V1 ---

  const [echoLink, setEchoLink] =
    useState<any>({
      callsign: '',
      node_id: '',
      module_id: '',
      directory_status: '?',
      directory_online: false,
      module_active: false,
      pending_outgoing: null,
      client_count: 0,
      clients: [],
      nodes: [],
      history: [],
      control: {
        enabled: false,
        reason: '',
      },
    });

  const [echoBusy, setEchoBusy] =
    useState<string | null>(
      null
    );

  const [echoError, setEchoError] =
    useState<string | null>(
      null
    );

  const [
    echoNodeDraft,
    setEchoNodeDraft,
  ] = useState({
    label: '',
    callsign: '',
    node_id: '',
  });


  const echoDuration =
    (secondsValue: number) => {

      const seconds =
        Math.max(
          0,
          Number(
            secondsValue || 0
          )
        );

      const hours =
        Math.floor(
          seconds / 3600
        );

      const minutes =
        Math.floor(
          (
            seconds % 3600
          ) / 60
        );

      const secondsRest =
        Math.floor(
          seconds % 60
        );

      if (hours > 0) {
        return `${hours}h ${minutes}m`;
      }

      if (minutes > 0) {
        return `${minutes}m ${secondsRest}s`;
      }

      return `${secondsRest}s`;
    };


  const echoDate =
    (stamp: number) => {

      return new Date(
        Number(stamp) * 1000
      ).toLocaleDateString(
        'de-DE'
      );
    };


  const echoTime =
    (stamp: number) => {

      return new Date(
        Number(stamp) * 1000
      ).toLocaleTimeString(
        'de-DE',
        {
          hour: '2-digit',
          minute: '2-digit',
        }
      );
    };


  const loadEchoLink =
    async () => {

      try {

        const response =
          await fetch(
            '/api/echolink-webui/status',
            {
              cache: 'no-store',
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'EchoLink-Status konnte nicht geladen werden.'
          );
        }

        setEchoLink(
          body
        );

        setEchoError(
          null
        );

      } catch (error) {

        setEchoError(
          error instanceof Error
            ? error.message
            : 'EchoLink-Status konnte nicht geladen werden.'
        );
      }
    };


  useEffect(() => {

    let active = true;

    const refresh =
      async () => {

        if (!active) {
          return;
        }

        await loadEchoLink();
      };

    refresh();

    const timer =
      window.setInterval(
        refresh,
        2000
      );

    return () => {

      active = false;

      window.clearInterval(
        timer
      );
    };

  }, []);


  const echoControl =
    async (
      action: string
    ) => {

      setEchoBusy(
        action
      );

      setEchoError(
        null
      );

      try {

        const response =
          await fetch(
            `/api/echolink-webui/control/${action}`,
            {
              method: 'POST',
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'EchoLink-Steuerung fehlgeschlagen.'
          );
        }

        window.setTimeout(
          loadEchoLink,
          400
        );

        window.setTimeout(
          loadEchoLink,
          1200
        );

        window.setTimeout(
          loadEchoLink,
          2800
        );

      } catch (error) {

        setEchoError(
          error instanceof Error
            ? error.message
            : 'EchoLink-Steuerung fehlgeschlagen.'
        );

      } finally {

        window.setTimeout(
          () => {
            setEchoBusy(
              null
            );
          },
          800
        );
      }
    };


  const echoConnect =
    async (
      nodeId: string
    ) => {

      const id =
        String(
          nodeId
        ).trim();

      if (
        !/^\d+$/.test(
          id
        )
      ) {
        return;
      }

      setEchoBusy(
        `connect:${id}`
      );

      setEchoError(
        null
      );

      try {

        const response =
          await fetch(
            `/api/echolink-webui/control/connect/${encodeURIComponent(id)}`,
            {
              method: 'POST',
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'EchoLink-Verbindung konnte nicht gestartet werden.'
          );
        }

        window.setTimeout(
          loadEchoLink,
          500
        );

        window.setTimeout(
          loadEchoLink,
          1500
        );

        window.setTimeout(
          loadEchoLink,
          3500
        );

      } catch (error) {

        setEchoError(
          error instanceof Error
            ? error.message
            : 'EchoLink-Verbindung konnte nicht gestartet werden.'
        );

      } finally {

        window.setTimeout(
          () => {
            setEchoBusy(
              null
            );
          },
          1000
        );
      }
    };


  const echoSaveNode =
    async () => {

      setEchoBusy(
        'save-node'
      );

      setEchoError(
        null
      );

      try {

        const response =
          await fetch(
            '/api/echolink-webui/nodes',
            {
              method: 'POST',

              headers: {
                'Content-Type':
                  'application/json',
              },

              body:
                JSON.stringify(
                  echoNodeDraft
                ),
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'EchoLink-Node konnte nicht gespeichert werden.'
          );
        }

        setEchoNodeDraft({
          label: '',
          callsign: '',
          node_id: '',
        });

        await loadEchoLink();

      } catch (error) {

        setEchoError(
          error instanceof Error
            ? error.message
            : 'EchoLink-Node konnte nicht gespeichert werden.'
        );

      } finally {

        setEchoBusy(
          null
        );
      }
    };


  const echoDeleteNode =
    async (
      nodeId: string
    ) => {

      setEchoBusy(
        `delete:${nodeId}`
      );

      setEchoError(
        null
      );

      try {

        const response =
          await fetch(
            `/api/echolink-webui/nodes/${encodeURIComponent(nodeId)}`,
            {
              method: 'DELETE',
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'EchoLink-Node konnte nicht gelöscht werden.'
          );
        }

        await loadEchoLink();

      } catch (error) {

        setEchoError(
          error instanceof Error
            ? error.message
            : 'EchoLink-Node konnte nicht gelöscht werden.'
        );

      } finally {

        setEchoBusy(
          null
        );
      }
    };



    // --- DIRECT CONNECT UI V2 ---

    const [
      directTg,
      setDirectTg,
    ] = useState('');


// --- ECHOLINK SEARCH UI V2 ---

  const [
    echoSearchQuery,
    setEchoSearchQuery,
  ] = useState('');

  const [
    echoSearchResults,
    setEchoSearchResults,
  ] = useState<any[]>([]);

  const [
    echoSearchBusy,
    setEchoSearchBusy,
  ] = useState(false);

  const [
    echoSearchDone,
    setEchoSearchDone,
  ] = useState(false);

  const [
    echoSearchError,
    setEchoSearchError,
  ] = useState<string | null>(
    null
  );


  const echoSearch =
    async () => {

      const query =
        echoSearchQuery
          .trim()
          .toUpperCase();

      if (!query) {
        return;
      }

      setEchoSearchBusy(
        true
      );

      setEchoSearchDone(
        false
      );

      setEchoSearchError(
        null
      );

      try {

        const response =
          await fetch(
            `/api/echolink-webui/search?q=${encodeURIComponent(query)}`,
            {
              cache: 'no-store',
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'EchoLink-Suche fehlgeschlagen.'
          );
        }

        setEchoSearchResults(
          Array.isArray(
            body.results
          )
            ? body.results
            : []
        );

        setEchoSearchDone(
          true
        );

      } catch (error) {

        setEchoSearchResults(
          []
        );

        setEchoSearchDone(
          true
        );

        setEchoSearchError(
          error instanceof Error
            ? error.message
            : 'EchoLink-Suche fehlgeschlagen.'
        );

      } finally {

        setEchoSearchBusy(
          false
        );
      }
    };


  const echoSaveSearchResult =
    async (
      result: any
    ) => {

      setEchoBusy(
        `save-search:${result.node_id}`
      );

      setEchoError(
        null
      );

      try {

        const response =
          await fetch(
            '/api/echolink-webui/nodes',
            {
              method: 'POST',

              headers: {
                'Content-Type':
                  'application/json',
              },

              body:
                JSON.stringify({
                  label:
                    result.callsign,

                  callsign:
                    result.callsign,

                  node_id:
                    result.node_id,
                }),
            }
          );

        const body =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {

          throw new Error(
            body.detail ||
            'Node konnte nicht gespeichert werden.'
          );
        }

        await loadEchoLink();

      } catch (error) {

        setEchoError(
          error instanceof Error
            ? error.message
            : 'Node konnte nicht gespeichert werden.'
        );

      } finally {

        setEchoBusy(
          null
        );
      }
    };


  const echoStatusText =
    (
      status: string | null | undefined
    ) => {

      switch (
        String(
          status || ''
        ).toLowerCase()
      ) {

        case 'on':
        case 'online':
          return 'ONLINE';

        case 'busy':
          return 'BUSY';

        case 'offline':
          return 'OFFLINE';

        default:
          return 'UNBEKANNT';
      }
    };


  const [tgView, setTgView] =
    useState<TgView>('all');

  const [favoriteTgs, setFavoriteTgs] =
    useState<string[]>(() => {
      try {
        const stored =
          window.localStorage.getItem(
            'svxlink.favoriteTgs'
          );

        if (!stored) {
          return [];
        }

        const parsed =
          JSON.parse(stored);

        return Array.isArray(parsed)
          ? parsed.map(String)
          : [];
      } catch {
        return [];
      }
    });

  const [newFavoriteTg, setNewFavoriteTg] =
    useState('');

  const [favoriteHistory, setFavoriteHistory] =
    useState<Record<string, ActivityRecord>>({});

  const [buddyCalls, setBuddyCalls] =
    useState<string[]>(() => {
      try {
        const stored =
          window.localStorage.getItem(
            'svxlink.buddyCalls'
          );

        if (!stored) {
          return [];
        }

        const parsed =
          JSON.parse(stored);

        return Array.isArray(parsed)
          ? parsed
              .map((item) =>
                String(item)
                  .trim()
                  .toUpperCase()
              )
              .filter(Boolean)
          : [];
      } catch {
        return [];
      }
    });

  const [preferencesReady, setPreferencesReady] =
    useState(false);

  const [buddyHistory, setBuddyHistory] =
    useState<Record<string, ActivityRecord>>({});

  const [buddySearch, setBuddySearch] =
    useState('');

  const [buddySearchResult, setBuddySearchResult] =
    useState<ActivityRecord | null | undefined>(
      undefined
    );

  const [buddySearchBusy, setBuddySearchBusy] =
    useState(false);

  const [buddySearchError, setBuddySearchError] =
    useState('');

  const [error, setError] =
    useState('');

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const loadStatus = async () => {
      try {
        const [
          statusResponse,
          talkgroupsResponse,
        ] = await Promise.all([
          fetch(`${api}/status`, { cache: 'no-store' }),
          fetch(`${api}/talkgroups`, { cache: 'no-store' }),
        ]);

        if (
          !statusResponse.ok ||
          !talkgroupsResponse.ok
        ) {
          throw new Error();
        }

        if (stopped) {
          return;
        }

        setStatus(
          await statusResponse.json()
        );

        setTalkgroups(
          await talkgroupsResponse.json()
        );

        setError('');
      } catch {
        if (!stopped) {
          setError(
            'Backend nicht erreichbar.'
          );
        }
      }
    };

    const connectWebSocket = () => {
      if (stopped) {
        return;
      }

      const protocol =
        window.location.protocol === 'https:'
          ? 'wss:'
          : 'ws:';

      socket = new WebSocket(
        `${protocol}//${window.location.host}/api/ws/live`
      );

      socket.onopen = () => {
        console.log(
          '[FM-Funknetz] WebSocket verbunden'
        );
      };

      socket.onmessage = (message) => {
        try {
          const payload =
            JSON.parse(message.data);

          if (
            payload.event ===
            'fm-funknetz.state'
          ) {
            const external =
              payload.data;

            setTalkgroups(
              (current) => {
                if (!current) {
                  return current;
                }

                return {
                  ...current,
                  external: {
                    ...current.external,
                    ...external,
                  },
                };
              }
            );

            const lastEvent =
              external?.mqtt?.last_event;

            if (
              lastEvent?.call &&
              lastEvent?.tg &&
              lastEvent?.received_at
            ) {
              const call =
                String(
                  lastEvent.call
                ).toUpperCase();

              const tg =
                String(
                  lastEvent.tg
                );

              const parsedEpoch =
                Date.parse(
                  String(
                    lastEvent.received_at
                  )
                ) / 1000;

              const record:
                ActivityRecord = {
                  found: true,
                  active:
                    lastEvent.talk ===
                    'start',
                  call,
                  tg,
                  talk:
                    String(
                      lastEvent.talk ||
                      ''
                    ),
                  server:
                    String(
                      lastEvent.server ||
                      ''
                    ),
                  source_time:
                    String(
                      lastEvent.time ||
                      ''
                    ),
                  last_seen:
                    String(
                      lastEvent.received_at
                    ),
                  last_seen_epoch:
                    Number.isFinite(
                      parsedEpoch
                    )
                      ? parsedEpoch
                      : null,
                };

              setFavoriteHistory(
                (current) =>
                  Object.prototype
                    .hasOwnProperty
                    .call(
                      current,
                      tg
                    )
                    ? {
                        ...current,
                        [tg]: record,
                      }
                    : current
              );

              setBuddyHistory(
                (current) => {
                  let changed =
                    false;

                  const next = {
                    ...current,
                  };

                  for (
                    const base
                    of Object.keys(
                      current
                    )
                  ) {
                    if (
                      !callMatchesBuddy(
                        call,
                        base
                      )
                    ) {
                      continue;
                    }

                    changed = true;

                    next[base] = {
                      ...current[
                        base
                      ],

                      found:
                        true,

                      base_call:
                        base,

                      call:
                        base,

                      active:
                        lastEvent.talk ===
                        'start',

                      active_call:
                        lastEvent.talk ===
                        'start'
                          ? call
                          : null,

                      last_call:
                        call,

                      last_tg:
                        tg,

                      tg:
                        tg,

                      last_seen:
                        record.last_seen,

                      last_seen_epoch:
                        record.last_seen_epoch,
                    };
                  }

                  return changed
                    ? next
                    : current;
                }
              );

              setBuddySearchResult(
                (current) => {
                  const base =
                    current?.base_call ||
                    current?.call ||
                    '';

                  if (
                    !current ||
                    !callMatchesBuddy(
                      call,
                      base
                    )
                  ) {
                    return current;
                  }

                  return {
                    ...current,

                    found:
                      true,

                    active:
                      lastEvent.talk ===
                      'start',

                    active_call:
                      lastEvent.talk ===
                      'start'
                        ? call
                        : null,

                    last_call:
                      call,

                    last_tg:
                      tg,

                    tg:
                      tg,

                    last_seen:
                      record.last_seen,

                    last_seen_epoch:
                      record.last_seen_epoch,
                  };
                }
              );
            }
          }

          if (
            payload.event ===
            'node.status'
          ) {
            const dashboard =
              payload.data;

            if (
              dashboard &&
              dashboard.node &&
              dashboard.svxlink
            ) {
              setStatus(
                dashboard
              );
            }
          }
        } catch (err) {
          console.error(
            '[FM-Funknetz] WebSocket Nachricht ungültig',
            err
          );
        }
      };

      socket.onerror = () => {
        console.warn(
          '[FM-Funknetz] WebSocket Fehler'
        );
      };

      socket.onclose = () => {
        socket = null;

        if (!stopped) {
          console.warn(
            '[FM-Funknetz] WebSocket getrennt – Reconnect in 2 Sekunden'
          );

          reconnectTimer =
            window.setTimeout(
              connectWebSocket,
              2000
            );
        }
      };
    };

    loadStatus();
    connectWebSocket();

    /*
     * Status-/Konfigurationsdaten ändern
     * sich selten und dürfen weiter
     * gelegentlich aktualisiert werden.
     *
     * FM-Funknetz-Aktivität dagegen
     * kommt sofort per WebSocket.
     */
    const statusTimer =
      window.setInterval(
        loadStatus,
        60000
      );

    return () => {
      stopped = true;

      window.clearInterval(
        statusTimer
      );

      if (
        reconnectTimer !== null
      ) {
        window.clearTimeout(
          reconnectTimer
        );
      }

      if (socket) {
        socket.close();
      }
    };
  }, []);

  const groupedTalkgroups =
    useMemo<TalkgroupItem[]>(() => {
      if (!talkgroups) {
        return [];
      }

      const connected =
        talkgroups.active || null;

      const grouped =
        new Map<
          string,
          TalkgroupItem
        >();

      for (
        const entry of
          talkgroups.external.live || []
      ) {
        if (!entry.tg) {
          continue;
        }

        const existing =
          grouped.get(entry.tg);

        if (existing) {
          if (
            entry.call &&
            !existing.calls.includes(
              entry.call
            )
          ) {
            existing.calls.push(
              entry.call
            );
          }

          continue;
        }

        grouped.set(entry.tg, {
          tg: entry.tg,
          calls: entry.call
            ? [entry.call]
            : [],
          server: entry.server,
          time: entry.time,
          connected:
            entry.tg === connected,
          active: true,
        });
      }

      if (
        connected &&
        !grouped.has(connected)
      ) {
        grouped.set(connected, {
          tg: connected,
          calls: [],
          connected: true,
          active: false,
        });
      }

      return Array.from(
        grouped.values()
      ).sort((a, b) => {
        if (
          a.connected !== b.connected
        ) {
          return a.connected ? -1 : 1;
        }

        return Number(a.tg) -
          Number(b.tg);
      });
    }, [talkgroups]);

  useEffect(() => {
    let cancelled = false;

    const loadPreferences =
      async () => {
        try {
          const response =
            await fetch(
              `${api}/preferences`,
              {
                cache: 'no-store',
              }
            );

          if (!response.ok) {
            throw new Error();
          }

          const data =
            await response.json();

          const serverFavoriteTgs =
            Array.isArray(
              data.favorite_tgs
            )
              ? data.favorite_tgs
                  .map(String)
                  .filter(
                    (item: string) =>
                      /^\d{1,9}$/.test(
                        item
                      )
                  )
              : [];

          const serverBuddyCalls =
            Array.isArray(
              data.buddy_calls
            )
              ? data.buddy_calls
                  .map(
                    (item: unknown) =>
                      String(item)
                        .trim()
                        .toUpperCase()
                  )
                  .filter(Boolean)
              : [];

          const mergedFavoriteTgs =
            Array.from(
              new Set([
                ...serverFavoriteTgs,
                ...favoriteTgs,
              ])
            );

          const mergedBuddyCalls =
            Array.from(
              new Set([
                ...serverBuddyCalls,
                ...buddyCalls,
              ])
            );

          if (cancelled) {
            return;
          }

          setFavoriteTgs(
            mergedFavoriteTgs
          );

          setBuddyCalls(
            mergedBuddyCalls
          );

          const saveResponse =
            await fetch(
              `${api}/preferences`,
              {
                method: 'PUT',

                headers: {
                  'Content-Type':
                    'application/json',
                },

                body: JSON.stringify({
                  favorite_tgs:
                    mergedFavoriteTgs,

                  buddy_calls:
                    mergedBuddyCalls,
                }),
              }
            );

          if (!saveResponse.ok) {
            throw new Error();
          }

          if (!cancelled) {
            setPreferencesReady(true);

            try {
              window.localStorage
                .removeItem(
                  'svxlink.favoriteTgs'
                );

              window.localStorage
                .removeItem(
                  'svxlink.buddyCalls'
                );
            } catch {
              // Server ist jetzt Source of Truth.
            }
          }
        } catch {
          // Bei Backendfehler bleiben alte
          // localStorage-Daten erhalten.
        }
      };

    loadPreferences();

    return () => {
      cancelled = true;
    };
  }, []);


  useEffect(() => {
    if (!preferencesReady) {
      return;
    }

    const timer =
      window.setTimeout(
        async () => {
          try {
            const response =
              await fetch(
                `${api}/preferences`,
                {
                  method: 'PUT',

                  headers: {
                    'Content-Type':
                      'application/json',
                  },

                  body: JSON.stringify({
                    favorite_tgs:
                      favoriteTgs,

                    buddy_calls:
                      buddyCalls,
                  }),
                }
              );

            if (!response.ok) {
              console.warn(
                'Favoriten konnten nicht serverseitig gespeichert werden.'
              );
            }
          } catch {
            console.warn(
              'Favoriten konnten nicht serverseitig gespeichert werden.'
            );
          }
        },
        150
      );

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    favoriteTgs,
    buddyCalls,
    preferencesReady,
  ]);

  useEffect(() => {
    let cancelled = false;

    const fetchFavoriteHistory =
      async () => {
        if (!favoriteTgs.length) {
          setFavoriteHistory({});
          return;
        }

        try {
          const response =
            await fetch(
              `${api}/activity/talkgroups?tg=${encodeURIComponent(
                favoriteTgs.join(',')
              )}`,
              {
                cache: 'no-store',
              }
            );

          if (!response.ok) {
            return;
          }

          const data =
            await response.json();

          if (cancelled) {
            return;
          }

          const next:
            Record<string, ActivityRecord> = {};

          for (
            const item
            of data.items || []
          ) {
            if (item.tg) {
              next[
                String(item.tg)
              ] = item;
            }
          }

          setFavoriteHistory(
            next
          );
        } catch {
          // Live-MQTT läuft
          // unabhängig weiter.
        }
      };

    fetchFavoriteHistory();

    return () => {
      cancelled = true;
    };
  }, [favoriteTgs]);

  useEffect(() => {
    let cancelled = false;

    const fetchBuddyHistory =
      async () => {
        if (!buddyCalls.length) {
          setBuddyHistory({});
          return;
        }

        try {
          const response =
            await fetch(
              `${api}/nodes/buddies?call=${encodeURIComponent(
                buddyCalls.join(',')
              )}`,
              {
                cache: 'no-store',
              }
            );

          if (!response.ok) {
            return;
          }

          const data =
            await response.json();

          if (cancelled) {
            return;
          }

          const next:
            Record<string, ActivityRecord> = {};

          for (
            const item
            of data.items || []
          ) {
            const call =
              String(
                item.base_call ||
                item.call ||
                ''
              ).toUpperCase();

            if (call) {
              next[call] = item;
            }
          }

          setBuddyHistory(
            next
          );
        } catch {
          // optional
        }
      };

    fetchBuddyHistory();

    return () => {
      cancelled = true;
    };
  }, [buddyCalls]);

  const displayedTalkgroups =
    useMemo<TalkgroupItem[]>(() => {
      if (
        tgView === 'all'
      ) {
        return groupedTalkgroups;
      }

      const current =
        new Map(
          groupedTalkgroups.map(
            (item) => [
              item.tg,
              item,
            ]
          )
        );

      return favoriteTgs.map(
        (tg) =>
          current.get(tg) || {
            tg,
            calls: [],
            connected:
              talkgroups?.active === tg,
            active: false,
          }
      );
    }, [
      tgView,
      favoriteTgs,
      groupedTalkgroups,
      talkgroups,
    ]);

  const favoriteTalkgroups =
    useMemo<TalkgroupItem[]>(() => {
      const current =
        new Map(
          groupedTalkgroups.map(
            (item) => [
              item.tg,
              item,
            ]
          )
        );

      return favoriteTgs.map(
        (tg) =>
          current.get(tg) || {
            tg,
            calls: [],
            connected:
              talkgroups?.active === tg,
            active: false,
          }
      );
    }, [
      favoriteTgs,
      groupedTalkgroups,
      talkgroups,
    ]);

  // --- TOP TALKGROUPS LOADER ---

  useEffect(() => {
    let cancelled = false;

    const ranges = [
      '24h',
      '7d',
      '30d',
    ] as const;

    const loadTopTalkgroups =
      async () => {

        setTopTalkgroupsLoading(
          true
        );

        setTopTalkgroupsError(
          null
        );

        try {

          const results =
            await Promise.all(
              ranges.map(
                async (range) => {

                  const response =
                    await fetch(
                      `/api/fm-funknetz/top-talkgroups?range=${range}&limit=5`,
                      {
                        cache:
                          'no-store',
                      }
                    );

                  const data =
                    await response
                      .json()
                      .catch(
                        () => ({})
                      );

                  if (!response.ok) {
                    throw new Error(
                      data.detail ||
                      `Statistik ${range} konnte nicht geladen werden.`
                    );
                  }

                  return [
                    range,
                    Array.isArray(
                      data.talkgroups
                    )
                      ? data.talkgroups
                      : [],
                  ] as const;
                }
              )
            );


          if (!cancelled) {

            const next: Record<
              '24h' |
              '7d' |
              '30d',
              any[]
            > = {
              '24h': [],
              '7d': [],
              '30d': [],
            };

            for (
              const [
                range,
                rows,
              ] of results
            ) {
              next[
                range
              ] = rows;
            }

            setTopTalkgroupsByRange(
              next
            );
          }

        } catch (error) {

          if (!cancelled) {
            setTopTalkgroupsError(
              error instanceof Error
                ? error.message
                : 'Statistik konnte nicht geladen werden.'
            );
          }

        } finally {

          if (!cancelled) {
            setTopTalkgroupsLoading(
              false
            );
          }
        }
      };

    loadTopTalkgroups();

    return () => {
      cancelled = true;
    };

  }, []);


  // --- TG CONTROL FEEDBACK STATE ---

  const [
    pendingTg,
    setPendingTg,
  ] = useState<string | null>(
    null
  );

  const [
    tgControlError,
    setTgControlError,
  ] = useState<{
    tg: string;
    message: string;
  } | null>(
    null
  );

  const pendingTgRef =
    useRef<string | null>(
      null
    );

  const tgConfirmTimer =
    useRef<number | null>(
      null
    );


  // --- TG REALTIME CONTROL ---

  useEffect(() => {
    let socket: WebSocket | null =
      null;

    let reconnectTimer:
      number | null = null;

    let stopped = false;

    const connect =
      () => {
        const protocol =
          window.location.protocol ===
          'https:'
            ? 'wss'
            : 'ws';

        socket =
          new WebSocket(
            `${protocol}://${window.location.host}/api/ws/talkgroups`
          );

        socket.onmessage =
          (event) => {
            try {
              const message =
                JSON.parse(
                  event.data
                );

              if (
                message.type ===
                  'talkgroups.state' &&
                message.data
              ) {
                setTalkgroups(
                  (current: any) => ({
                    ...current,
                    ...message.data,
                  })
                );

                // --- TG WS CONFIRMATION FEEDBACK ---

                const waitingFor =
                  pendingTgRef.current;

                if (waitingFor) {
                  const selected =
                    String(
                      message.data
                        .selected ??
                      ''
                    );

                  const active =
                    String(
                      message.data
                        .active ??
                      ''
                    );

                  const confirmed =
                    waitingFor === '0'
                      ? (
                          selected === '0' ||
                          message.data
                            .using_default ===
                            true
                        )
                      : (
                          selected ===
                            waitingFor ||
                          active ===
                            waitingFor
                        );

                  if (confirmed) {
                    if (
                      tgConfirmTimer
                        .current !==
                      null
                    ) {
                      window.clearTimeout(
                        tgConfirmTimer
                          .current
                      );

                      tgConfirmTimer
                        .current = null;
                    }

                    pendingTgRef
                      .current = null;

                    setPendingTg(
                      null
                    );

                    setTgControlError(
                      null
                    );
                  }
                }
              }
            } catch {
              // ungültige Nachricht ignorieren
            }
          };

        socket.onclose =
          () => {
            if (!stopped) {
              reconnectTimer =
                window.setTimeout(
                  connect,
                  1200
                );
            }
          };
      };

    connect();

    return () => {
      stopped = true;

      if (
        reconnectTimer !== null
      ) {
        window.clearTimeout(
          reconnectTimer
        );
      }

      socket?.close();
    };
  }, []);


  const selectTalkgroup =
    async (
      tg: string | number
    ) => {
      const value =
        String(tg).trim();

      if (
        !/^\d+$/.test(value)
      ) {
        return;
      }

      if (
        !talkgroups?.control.enabled
      ) {
        setTgControlError({
          tg: value,
          message:
            'TG-Steuerung ist deaktiviert.',
        });

        return;
      }

      /*
       * Aktive TG nicht noch einmal auswählen.
       */
      if (
        value !== '0' &&
        value ===
          String(
            talkgroups?.active ??
            ''
          )
      ) {
        setTgControlError(
          null
        );

        return;
      }

      if (
        tgConfirmTimer.current !==
        null
      ) {
        window.clearTimeout(
          tgConfirmTimer.current
        );

        tgConfirmTimer.current =
          null;
      }

      pendingTgRef.current =
        value;

      setPendingTg(
        value
      );

      setTgControlError(
        null
      );

      try {
        const response =
          await fetch(
            `/api/talkgroups/select/${encodeURIComponent(value)}`,
            {
              method: 'POST',
            }
          );

        const result =
          await response
            .json()
            .catch(
              () => ({})
            );

        if (!response.ok) {
          throw new Error(
            result.detail ||
              'Talkgroup konnte nicht gewechselt werden.'
          );
        }

        /*
         * Erst echte SvxLink-Bestätigung
         * beendet den Pending-Zustand.
         */
        tgConfirmTimer.current =
          window.setTimeout(
            () => {
              if (
                pendingTgRef
                  .current ===
                value
              ) {
                pendingTgRef
                  .current = null;

                setPendingTg(
                  null
                );

                setTgControlError({
                  tg: value,
                  message:
                    'Keine Bestätigung von SvxLink.',
                });
              }
            },
            6000
          );

      } catch (error) {
        if (
          tgConfirmTimer.current !==
          null
        ) {
          window.clearTimeout(
            tgConfirmTimer.current
          );

          tgConfirmTimer.current =
            null;
        }

        pendingTgRef.current =
          null;

        setPendingTg(
          null
        );

        setTgControlError({
          tg: value,
          message:
            error instanceof Error
              ? error.message
              : 'Talkgroup konnte nicht gewechselt werden.',
        });
      }
    };


  const toggleFavorite = (
    tg: string
  ) => {
    setFavoriteTgs(
      (current) =>
        current.includes(tg)
          ? current.filter(
              (item) =>
                item !== tg
            )
          : [
              ...current,
              tg,
            ]
    );
  };


  const addFavoriteTg = (
    event?: React.FormEvent
  ) => {
    event?.preventDefault();

    const tg =
      newFavoriteTg.trim();

    if (!/^\d{1,9}$/.test(tg)) {
      return;
    }

    setFavoriteTgs(
      (current) =>
        current.includes(tg)
          ? current
          : [
              ...current,
              tg,
            ]
    );

    setNewFavoriteTg('');
  };

  const addBuddy = (
    callValue: string
  ) => {
    const call =
      callValue
        .trim()
        .toUpperCase();

    if (!call) {
      return;
    }

    setBuddyCalls(
      (current) =>
        current.includes(call)
          ? current
          : [
              ...current,
              call,
            ]
    );
  };

  const removeBuddy = (
    callValue: string
  ) => {
    const call =
      callValue
        .trim()
        .toUpperCase();

    setBuddyCalls(
      (current) =>
        current.filter(
          (item) =>
            item !== call
        )
    );
  };

  const searchBuddy = async (
    event?: React.FormEvent
  ) => {
    event?.preventDefault();

    const call =
      buddySearch
        .trim()
        .toUpperCase();

    if (!call) {
      return;
    }

    setBuddySearchBusy(true);
    setBuddySearchError('');

    try {
      const response =
        await fetch(
          `${api}/nodes/search?q=${encodeURIComponent(
            call
          )}`,
          {
            cache: 'no-store',
          }
        );

      if (!response.ok) {
        throw new Error();
      }

      const data =
        await response.json();

      setBuddySearchResult(
        data
      );
    } catch {
      setBuddySearchResult(
        null
      );

      setBuddySearchError(
        'FM-Funknetz Suche momentan nicht verfügbar.'
      );
    } finally {
      setBuddySearchBusy(
        false
      );
    }
  };


    const connectDirectTalkgroup =
      async () => {

        const tg =
          directTg.trim();


        if (
          !/^\d+$/.test(tg)
        ) {

          setTgControlError({
            tg,
            message:
              'Bitte eine gültige numerische Talkgroup eingeben.',
          });

          return;

        }


        await selectTalkgroup(
          tg
        );

      };


    const connectEchoDirect =
      async () => {

        const query =
          echoSearchQuery
            .trim()
            .toUpperCase();


        if (!query) {
          return;
        }


        setEchoSearchError(
          null
        );

        setEchoSearchDone(
          false
        );


        /*
         * Reine EchoLink Node-ID:
         * direkt verbinden.
         */
        if (
          /^\d+$/.test(query)
        ) {

          await echoConnect(
            query
          );

          return;

        }


        /*
         * Bei einem Rufzeichen zuerst
         * über das bereits vorhandene
         * Directory auflösen.
         */
        setEchoSearchBusy(
          true
        );


        try {

          const response =
            await fetch(
              `/api/echolink-webui/search?q=${encodeURIComponent(query)}`,
              {
                cache: 'no-store',
              }
            );


          const body =
            await response
              .json()
              .catch(
                () => ({})
              );


          if (!response.ok) {

            throw new Error(
              body.detail ||
              'EchoLink-Suche fehlgeschlagen.'
            );

          }


          const results =
            Array.isArray(
              body.results
            )
              ? body.results
              : [];


          /*
           * Ergebnisse gleichzeitig auch
           * in der normalen Directory-
           * Ansicht anzeigen.
           */
          setEchoSearchResults(
            results
          );

          setEchoSearchDone(
            true
          );


          const onlineResults =
            results.filter(
              (result: any) => {

                const nodeId =
                  String(
                    result?.node_id ||
                    ''
                  );


                return (
                  /^\d+$/.test(nodeId) &&
                  (
                    result?.online === true ||
                    result?.status === 'on'
                  )
                );

              }
            );


          /*
           * Exaktes Rufzeichen hat Vorrang.
           */
          let target =
            onlineResults.find(
              (result: any) =>
                String(
                  result?.callsign ||
                  ''
                )
                  .trim()
                  .toUpperCase() ===
                query
            );


          /*
           * Gibt es genau einen möglichen
           * Online-Treffer, ist die Auswahl
           * ebenfalls eindeutig.
           */
          if (
            !target &&
            onlineResults.length === 1
          ) {

            target =
              onlineResults[0];

          }


          if (!target) {

            if (
              onlineResults.length > 1
            ) {

              throw new Error(
                'Mehrere passende Online-Nodes gefunden. Bitte unten den gewünschten Node auswählen.'
              );

            }


            const first =
              results[0];


            if (
              first?.status === 'busy'
            ) {

              throw new Error(
                `${
                  first.callsign ||
                  query
                } ist momentan BUSY.`
              );

            }


            if (
              first?.status === 'offline' ||
              first?.online === false
            ) {

              throw new Error(
                `${
                  first.callsign ||
                  query
                } ist momentan OFFLINE.`
              );

            }


            throw new Error(
              'Keine online verfügbare EchoLink-Node gefunden.'
            );

          }


          await echoConnect(
            String(
              target.node_id
            )
          );


          /*
           * Bei erfolgreicher Direktwahl
           * brauchen wir die Suchresultate
           * nicht offen stehen lassen.
           */
          setEchoSearchResults(
            []
          );

          setEchoSearchDone(
            false
          );


        } catch (error) {

          setEchoSearchError(
            error instanceof Error
              ? error.message
              : 'EchoLink-Verbindung konnte nicht gestartet werden.'
          );


        } finally {

          setEchoSearchBusy(
            false
          );

        }

      };


  if (error) {
    return (
      <div className="loading-screen">
        <strong>{error}</strong>
      </div>
    );
  }

  if (!status || !talkgroups) {
    return (
      <div className="loading-screen">
        <div className="loader" />
        <span>
          Shari wird geladen …
        </span>
      </div>
    );
  }

  const node = status.node;

  const callsign = String(
    value(
      node,
      'Callsign',
      'CALLSIGN'
    ) || 'DA6IT-L'
  );

  const location = String(
    value(
      node,
      'Location',
      'nodeLocation'
    ) ||
      'Standort nicht konfiguriert'
  );

  const txFrequency =
    value(
      node,
      'TXFREQ',
      'RXFREQ'
    ) || '—';

  const rxFrequency =
    value(node, 'RXFREQ') || '—';

  const mode =
    value(node, 'Mode') || '—';

  const connectedTg =
    talkgroups.active;

  const connectedConfirmed =
    talkgroups.confirmed;

  const liveEntries =
    talkgroups.external.live || [];

  const activeTgCount =
    new Set(
      liveEntries
        .map((entry) => entry.tg)
        .filter(Boolean)
    ).size;

  const activeTalker =
    talkgroups.external.active;

  const local = status.local_log;

  const updatedAt =
    new Date(
      status.updated_at
    ).toLocaleTimeString(
      'de-DE',
      {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }
    );

  const navItems: {
    id: View;
    label: string;
  }[] = [
    {
      id: 'overview',
      label: 'Übersicht',
    },
    {
      id: 'fm',
      label: 'FM-Funknetz',
    },
    {
      id: 'echolink',
      label: 'EchoLink',
    },
  ];

  const goTo =
    (target: View) => {
      setView(target);
      window.scrollTo({
        top: 0,
        behavior: 'smooth',
      });
    };

  return (
    <div className="site">
      <header className="app-header">
        <div className="header-inner">
          <button
            className="brand"
            onClick={() =>
              goTo('overview')
            }
          >
            <span className="brand-mark">
              DA6IT
            </span>

            <span className="brand-divider" />

            <span className="brand-product">
              Shari
            </span>
          </button>

          <nav className='main-nav'>
            {navItems.map(
              (item) => (
                <button
                  key={item.id}
                  className={
                    view === item.id
                      ? 'is-current'
                      : ''
                  }
                  onClick={() =>
                    goTo(item.id)
                  }
                >
                  {item.label}
                </button>
              )
            )}

            <details className='nav-dropdown'>
              <summary
                className={
                  view === 'shari' ||
                  view === 'svxlink-config'
                    ? 'is-current'
                    : ''
                }
              >
                <span>Konfiguration</span>
                <span className='nav-dropdown-caret'>▾</span>
              </summary>

              <div className='nav-dropdown-menu'>
                <button
                  className={
                    view === 'shari'
                      ? 'is-current'
                      : ''
                  }
                  onClick={(event) => {
                    goTo('shari');
                    event.currentTarget
                      .closest('details')
                      ?.removeAttribute('open');
                  }}
                >
                  <strong>SHARI</strong>
                  <span>SA818 / Funkmodul</span>
                </button>

                <button
                  className={
                    view === 'svxlink-config'
                      ? 'is-current'
                      : ''
                  }
                  onClick={(event) => {
                    goTo('svxlink-config');
                    event.currentTarget
                      .closest('details')
                      ?.removeAttribute('open');
                  }}
                >
                  <strong>SvxLink</strong>
                  <span>Software &amp; Audio</span>
                </button>
              </div>
            </details>

            <button
              className={
                view === 'system'
                  ? 'is-current'
                  : ''
              }
              onClick={() =>
                goTo('system')
              }
            >
              System
            </button>
          </nav>

          <div className="header-status">
            <StatusDot
              active={
                status.svxlink
                  .status === 'online'
              }
            />

            <span>
              {status.svxlink
                .status === 'online'
                ? 'Online'
                : 'Offline'}
            </span>
          </div>
        </div>
      </header>

      {view === 'overview' && (
        <>
          <section className="app-hero">
            <div className="hero-glow hero-glow-green" />
            <div className="hero-glow hero-glow-cyan" />

            <div className="content hero-grid">
              <div className="hero-copy">
                <span className="eyebrow">
                  SVXLINK · FM-FUNKNETZ · ECHOLINK
                </span>

                <h1>
                  Dein Shari.
                  <br />
                  Alles im Blick.
                </h1>

                <p>
                  {callsign} · {location} · {txFrequency} MHz
                </p>

                <div className="hero-actions">
                  <button
                    className="button button-primary"
                    onClick={() => goTo('fm')}
                  >
                    FM-Funknetz
                  </button>

                  <button
                    className="button button-outline"
                    onClick={() => goTo('echolink')}
                  >
                    EchoLink
                  </button>
                </div>
              </div>

              <div className="hero-tools">
                <button
                  className="hero-tool-card hero-tool-fm"
                  onClick={() => goTo('fm')}
                >
                  <div className="hero-tool-head">
                    <span className="eyebrow">
                      FM-FUNKNETZ
                    </span>

                    <span className="hero-tool-arrow">
                      →
                    </span>
                  </div>

                  <div className="hero-tool-main">
                    <div>
                      <span className="hero-tool-label">
                        Aktuelle Talkgroup
                      </span>

                      <strong className="hero-tool-tg">
                        {connectedTg
                          ? tgLabel(connectedTg)
                          : 'Keine TG'}
                      </strong>
                    </div>

                    <div className="hero-tool-state">
                      {connectedTg && (
                        <Tag type="green">
                          {connectedConfirmed
                            ? 'Verbunden'
                            : 'Standard-TG'}
                        </Tag>
                      )}

                      {connectedTg &&
                        liveEntries.some(
                          (entry) =>
                            entry.tg === connectedTg
                        ) && (
                          <Tag type="cyan">
                            Aktiv
                          </Tag>
                        )}
                    </div>
                  </div>

                  <div className="hero-tool-footer">
                    <span>
                      {activeTgCount}{' '}
                      aktive TG
                      {activeTgCount === 1 ? '' : 's'}
                    </span>

                    {activeTalker ? (
                      <span>
                        Jetzt: {tgLabel(activeTalker.tg)}
                        {activeTalker.call
                          ? ` · ${activeTalker.call}`
                          : ''}
                      </span>
                    ) : (
                      <span>
                        Momentan ruhig
                      </span>
                    )}
                  </div>
                </button>

                <button
                  className="hero-tool-card hero-tool-el"
                  onClick={() => goTo('echolink')}
                >
                  <div className="hero-tool-head">
                    <span className="eyebrow">
                      ECHOLINK
                    </span>

                    <span className="hero-tool-arrow">
                      →
                    </span>
                  </div>

                  <div className="hero-el-main">
                    <div className="hero-el-icon">
                      EL
                    </div>

                    <div>
                      <strong>
                        {callsign}
                      </strong>

                      <span className="hero-el-live-meta">
                    {echoLink.node_id
                      ? `Node ${echoLink.node_id}`
                      : 'Node —'}
                    {' · '}
                    {echoLink.directory_online
                      ? 'Directory online'
                      : 'Directory offline'}
                  </span>
                    </div>
                  </div>

                  <div className="hero-tool-footer hero-el-live-footer">

                <span
                  className={`hero-el-overview-state ${
                    echoLink.directory_online
                      ? 'is-online'
                      : 'is-offline'
                  }`}
                >
                  <i />

                  {echoLink.directory_online
                    ? 'ONLINE'
                    : 'OFFLINE'}
                </span>


                <span className="hero-el-overview-connection">

                  {echoLink.client_count > 0
                    ? echoLink.client_count === 1
                      ? `${
                          echoLink.clients?.[0]?.callsign ||
                          '1 Station'
                        } verbunden`
                      : `${echoLink.client_count} Stationen verbunden`
                    : echoLink.module_active
                    ? 'Modul aktiv · keine Verbindung'
                    : 'Keine Verbindung'}

                </span>

              </div>
                </button>
              </div>
            </div>
          </section>

          <main className="content main-content">
            <section className="section home-favorites">
              <div className="section-heading compact-heading">
                <div>
                  <span className="eyebrow">
                    LIVE-MONITOR
                  </span>

                  <h2>
                    Meine Talkgroups
                  </h2>
                </div>

                <div className="watch-head-actions">
                  <form
                    className="watch-add-form"
                    onSubmit={
                      addFavoriteTg
                    }
                  >
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      value={
                        newFavoriteTg
                      }
                      onChange={
                        (event) =>
                          setNewFavoriteTg(
                            event.target
                              .value
                          )
                      }
                      placeholder="TG"
                      aria-label="Talkgroup hinzufügen"
                    />

                    <button
                      type="submit"
                    >
                      + TG
                    </button>
                  </form>

                  <button
                    className="text-button"
                    onClick={() =>
                      goTo('fm')
                    }
                  >
                    verwalten →
                  </button>
                </div>
              </div>

              <div className="home-favorites-strip">
                {favoriteTalkgroups.map(
                  (item) => {
                    const history =
                      favoriteHistory[
                        item.tg
                      ];

                    return (
                      <button
                        key={item.tg}
                        className={`home-favorite-tile ${
                          item.active
                            ? 'is-active'
                            : ''
                        } ${
                          item.connected
                            ? 'is-connected'
                            : ''
                        }`}
                        onClick={() =>
                          selectTalkgroup(
                            item.tg
                          )
                        }
                      >
                        {/* TG CONTROL HOME FEEDBACK */}
                      {pendingTg ===
                        String(item.tg) && (
                        <div className="tg-control-feedback is-pending">
                          <span className="tg-control-spinner" />
                          Wechselt…
                        </div>
                      )}

                      {tgControlError?.tg ===
                        String(item.tg) && (
                        <div className="tg-control-feedback is-error">
                          {tgControlError.message}
                        </div>
                      )}

                      {/* TG LEAVE HOME ERROR */}

                      {item.connected &&
                        tgControlError?.tg ===
                          '0' && (
                          <div className="tg-control-feedback is-error">
                            {tgControlError.message}
                          </div>
                        )}

                      <div className="home-favorite-top">
                          <span>
                            TG
                          </span>

                          <div className="home-favorite-top-right">
                            {item.connected && (
                              <span className="mini-connected">
                                VERBUNDEN
                              </span>
                            )}

                            {/* TG LEAVE HOME TILE */}

                            {item.connected &&
                              talkgroups?.using_default ===
                                false && (
                                <span
                                  className={`tg-leave-tile ${
                                    pendingTg === '0'
                                      ? 'is-pending'
                                      : ''
                                  }`}
                                  title="Talkgroup verlassen"
                                  onClick={(event) => {
                                    event.stopPropagation();

                                    if (
                                      pendingTg ===
                                      null
                                    ) {
                                      selectTalkgroup(
                                        '0'
                                      );
                                    }
                                  }}
                                >
                                  {pendingTg === '0'
                                    ? 'Trenne…'
                                    : 'Verlassen'}
                                </span>
                              )}

                            <StatusDot
                              active={
                                item.active
                              }
                            />
                          </div>
                        </div>

                        <strong>
                          {item.tg}
                        </strong>

                        {(tgNames[String(Number(item.tg))] ||
                          tgNames[String(item.tg)]) && (
                          <span className="home-favorite-tg-name">
                            {tgNames[String(Number(item.tg))] ||
                              tgNames[String(item.tg)]}
                          </span>
                        )}

                        <div className="home-favorite-bottom">
                          {item.active ? (
                            <>
                              <span className="live-text">
                                Jetzt aktiv
                              </span>

                              <span className="favorite-callsign">
                                {item.calls[0] ||
                                  'Talker aktiv'}
                              </span>
                            </>
                          ) : history?.found &&
                            history.last_seen_epoch ? (
                            <>
                              <span className="favorite-last">
                                Letzte Aktivität:
                                {' '}
                                {relativeAge(
                                  history.last_seen_epoch
                                )}
                              </span>

                              <span className="favorite-callsign">
                                {history.call ||
                                  '—'}
                              </span>
                            </>
                          ) : (
                            <span className="quiet-text">
                              Noch keine Aktivität gespeichert
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  }
                )}

                {!favoriteTalkgroups.length && (
                  <button
                    className="home-favorites-empty"
                    onClick={() =>
                      goTo('fm')
                    }
                  >
                    <span className="empty-star">
                      ★
                    </span>

                    <div>
                      <strong>
                        Noch keine Favoriten
                      </strong>

                      <span>
                        TG oben direkt
                        eintragen oder im
                        FM-Funknetz markieren.
                      </span>
                    </div>
                  </button>
                )}
              </div>
            </section>

            <section className="section home-buddies">
              <div className="section-heading compact-heading">
                <div>
                  <span className="eyebrow">
                    LAST SEEN
                  </span>

                  <h2>
                    Buddy List
                  </h2>
                </div>

                <form
                  className="buddy-search-form"
                  onSubmit={
                    searchBuddy
                  }
                >
                  <input
                    type="text"
                    value={
                      buddySearch
                    }
                    onChange={
                      (event) =>
                        setBuddySearch(
                          event.target
                            .value
                            .toUpperCase()
                        )
                    }
                    placeholder="z. B. DA6IT"
                    aria-label="Rufzeichen suchen"
                  />

                  <button
                    type="submit"
                    disabled={
                      buddySearchBusy
                    }
                  >
                    {buddySearchBusy
                      ? '…'
                      : 'Suchen'}
                  </button>
                </form>
              </div>

              {buddySearchResult !==
                undefined && (
                <div className="buddy-search-result buddy-directory-result">
                  {buddySearchResult ? (
                    <>
                      <div className="buddy-directory-head">
                        <div>
                          <strong>
                            {buddySearchResult.base_call ||
                              buddySearch.trim().toUpperCase()}
                          </strong>

                          <span>
                            {
                              buddySearchResult.variants?.length ||
                              0
                            }{' '}
                            bekannte Variante
                            {(buddySearchResult.variants?.length ||
                              0) === 1
                              ? ''
                              : 'n'}
                          </span>
                        </div>

                        <button
                          className="buddy-add-button"
                          onClick={() =>
                            addBuddy(
                              buddySearchResult.base_call ||
                                buddySearch
                            )
                          }
                        >
                          {buddyCalls.includes(
                            String(
                              buddySearchResult.base_call ||
                                buddySearch
                            ).toUpperCase()
                          )
                            ? '✓ Überwacht'
                            : '★ Komplett überwachen'}
                        </button>
                      </div>

                      <div className="buddy-variant-list">
                        {(buddySearchResult.variants ||
                          []).map(
                          (node) => (
                            <div
                              className={`buddy-variant ${
                                node.talk_active
                                  ? 'is-talking'
                                  : node.online
                                  ? 'is-online'
                                  : ''
                              }`}
                              key={
                                node.call
                              }
                            >
                              <div className="buddy-variant-call">
                                <strong>
                                  {node.call}
                                </strong>

                                {node.talk_active ? (
                                  <span className="variant-state talking">
                                    ● SPRICHT
                                  </span>
                                ) : node.online ? (
                                  <span className="variant-state online">
                                    ● ONLINE
                                  </span>
                                ) : (
                                  <span className="variant-state offline">
                                    OFFLINE
                                  </span>
                                )}
                              </div>

                              <div className="buddy-variant-meta">
                                <strong>
                                  {node.talk_tg || node.tg
                                  ? tgLabel(
                                      node.talk_tg ||
                                        node.tg
                                    )
                                  : 'TG —'}
                                </strong>

                                {node.last_activity
                                  ?.last_seen_epoch ? (
                                  <span>
                                    Zuletzt gesprochen{' '}
                                    {relativeAge(
                                      node.last_activity
                                        .last_seen_epoch
                                    )}
                                  </span>
                                ) : (
                                  <span>
                                    Noch keine
                                    Sprechaktivität
                                    gespeichert
                                  </span>
                                )}

                                {node.location && (
                                  <span>
                                    {node.location}
                                  </span>
                                )}
                              </div>
                            </div>
                          )
                        )}

                        {!buddySearchResult
                          .variants?.length && (
                          <div className="buddy-directory-empty">
                            Keine passende
                            Node-Variante im
                            FM-Funknetz-Verzeichnis
                            gefunden.
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <span>
                      {buddySearchError ||
                        'Keine Daten gefunden.'}
                    </span>
                  )}
                </div>
              )}

              <div className="buddy-strip">
                {buddyCalls.map(
                  (call) => {
                    const active =
                      liveEntries.find(
                        (entry) =>
                          callMatchesBuddy(
                            String(
                              entry.call ||
                              ''
                            ),
                            call
                          )
                      );

                    const history =
                      buddyHistory[
                        call
                      ];

                    const tg =
                      active?.tg ||
                      history?.last_tg ||
                      history?.tg;

                    return (
                      <article
                        className={`buddy-tile ${
                          active
                            ? 'is-active'
                            : ''
                        }`}
                        key={call}
                      >
                        <div className="buddy-tile-head">
                          <strong>
                            {call}
                          </strong>

                          <button
                            title="Buddy entfernen"
                            onClick={() =>
                              removeBuddy(
                                call
                              )
                            }
                          >
                            ×
                          </button>
                        </div>

                        {active ? (
                          <>
                            <span className="buddy-live">
                              ● JETZT AKTIV
                            </span>

                            <strong className="buddy-tg">
                              {String(
                                active.call ||
                                call
                              ).toUpperCase()}
                              {' · '}
                              {tgLabel(active.tg)}
                            </strong>
                          </>
                        ) : history?.online ? (
                          <>
                            <span className="buddy-online">
                              ● ONLINE
                            </span>

                            <strong className="buddy-tg">
                              {history.online_calls?.[0] ||
                                call}
                              {tg
                                ? ` · ${tgLabel(tg)}`
                                : ''}
                            </strong>
                          </>
                        ) : history?.found &&
                          history.last_seen_epoch ? (
                          <>
                            <span className="buddy-last">
                              Zuletzt{' '}
                              {relativeAge(
                                history.last_seen_epoch
                              )}
                            </span>

                            <strong className="buddy-tg">
                              {history.last_call ||
                                call}
                              {tg
                                ? ` · ${tgLabel(tg)}`
                                : ''}
                            </strong>
                          </>
                        ) : (
                          <>
                            <span className="buddy-last">
                              Noch nicht gesehen
                            </span>

                            <strong className="buddy-tg">
                              TG —
                            </strong>
                          </>
                        )}
                      </article>
                    );
                  }
                )}

                {!buddyCalls.length && (
                  <div className="buddy-empty">
                    Rufzeichen oben suchen
                    und als Buddy hinzufügen.
                  </div>
                )}
              </div>
            </section>

            <section className="status-row">
              <div className="mini-status">
                <span className="mini-status-label">
                  SHARI RX
                </span>

                <strong>
                  {local.rx.squelch ===
                  'open'
                    ? 'Squelch offen'
                    : local.rx
                        .squelch ===
                      'closed'
                    ? 'Squelch geschlossen'
                    : 'Keine Daten'}
                </strong>

                <span>
                  {local.rx.level !==
                  null
                    ? `Signal ${local.rx.level}`
                    : 'Lokale RF-Daten'}
                </span>
              </div>

              <div className="mini-status">
                <span className="mini-status-label">
                  SHARI TX
                </span>

                <strong>
                  {boolActive(
                    status.rf.tx
                      ?.state
                  )
                    ? 'Sendet'
                    : 'Bereit'}
                </strong>

                <span>
                  PTT /
                  Senderstatus
                </span>
              </div>

              <div className="mini-status">
                <span className="mini-status-label">
                  SVXLINK
                </span>

                <strong>
                  {status.svxlink
                    .status ===
                  'online'
                    ? 'Online'
                    : status.svxlink
                        .status}
                </strong>

                <span>
                  PID{' '}
                  {status.svxlink
                    .pid || '—'}
                </span>
              </div>

              <div className="mini-status">
                <span className="mini-status-label">
                  UPDATE
                </span>

                <strong>
                  {updatedAt}
                </strong>

                <span>
                  alle 15 Sekunden
                </span>
              </div>
            </section>
          </main>
        </>
      )}

      {view === 'fm' && (
        <>
          <section className="page-hero">
            <div className="hero-glow hero-glow-green" />
            <div className="hero-glow hero-glow-cyan" />

            <div className="content">
              <span className="eyebrow">
                FM-FUNKNETZ
              </span>

              <h1>
                Talkgroups
              </h1>

              <p>
                Deine Verbindung,
                aktuelle Aktivität und
                später die direkte
                TG-Auswahl an einer
                Stelle.
              </p>
            </div>
          </section>

          <main className="content main-content">
            <section className="current-connection-card">
              <div>
                <span className="eyebrow">
                  AKTUELL GEWÄHLT
                </span>

                <div className="connection-tg-large">
                  {connectedTg
                    ? tgLabel(connectedTg)
                    : 'Keine TG'}
                </div>

                <p>
                  {connectedTg
                    ? connectedConfirmed
                      ? 'Diese Talkgroup wurde lokal von SvxLink bestätigt.'
                      : 'Diese Talkgroup stammt aktuell aus der Konfiguration.'
                    : 'SvxLink meldet derzeit keine ausgewählte Talkgroup.'}
                </p>
              </div>

              <div className="connection-badges">
                {connectedTg && (
                  <Tag type="green">
                    {connectedConfirmed
                      ? 'Verbunden'
                      : 'Konfiguriert'}
                  </Tag>
                )}

                {connectedTg &&
                  liveEntries.some(
                    (entry) =>
                      entry.tg ===
                      connectedTg
                  ) && (
                    <Tag type="cyan">
                      Aktivität
                    </Tag>
                  )}
              </div>
</section>


              <section className="section fm-direct-section">

                <div className="fm-direct-panel">

                  <div className="fm-direct-copy">

                    <span className="eyebrow">
                      DIREKTWAHL
                    </span>

                    <h2>
                      Talkgroup verbinden
                    </h2>

                    <p>
                      Beliebige FM-Funknetz
                      Talkgroup direkt auswählen.
                    </p>

                  </div>


                  <form
                    className="fm-direct-form"
                    onSubmit={(event) => {

                      event.preventDefault();

                      connectDirectTalkgroup();

                    }}
                  >

                    <span className="fm-direct-prefix">
                      TG
                    </span>


                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      autoComplete="off"
                      value={directTg}
                      onChange={(event) => {

                        setDirectTg(
                          event.target.value.replace(
                            /\D/g,
                            ''
                          )
                        );

                        setTgControlError(
                          null
                        );

                      }}
                      placeholder="Talkgroup-ID"
                      aria-label="Talkgroup-ID"
                    />


                    <button
                      type="submit"
                      disabled={
                        !directTg.trim() ||
                        pendingTg !== null ||
                        !talkgroups.control.enabled
                      }
                    >

                      {pendingTg ===
                      directTg.trim()
                        ? 'Verbinde…'
                        : 'Verbinden'}

                    </button>

                  </form>


                  {!talkgroups.control.enabled && (

                    <div className="fm-direct-error">
                      TG-Steuerung ist aktuell
                      nicht verfügbar.
                    </div>

                  )}


                  {tgControlError &&
                    tgControlError.tg ===
                      directTg.trim() && (

                    <div className="fm-direct-error">
                      {tgControlError.message}
                    </div>

                  )}

                </div>

              </section>


                        <section className="section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">
                    LIVE
                  </span>

                  <h2>
                    Aktive
                    Talkgroups
                  </h2>
                </div>

                <div className="tg-view-toolbar">
                  <div className="tg-view-switch">
                    <button
                      className={
                        tgView === 'all'
                          ? 'is-active'
                          : ''
                      }
                      onClick={() =>
                        setTgView('all')
                      }
                    >
                      Alle
                    </button>

                    <button
                      className={
                        tgView ===
                        'favorites'
                          ? 'is-active'
                          : ''
                      }
                      onClick={() =>
                        setTgView(
                          'favorites'
                        )
                      }
                    >
                      Favoriten
                      <span>
                        {
                          favoriteTgs.length
                        }
                      </span>
                    </button>
                  </div>

                  <span className="section-meta">
                    {
                      displayedTalkgroups.length
                    }{' '}
                    sichtbar
                  </span>
                </div>
              </div>

              <div className="tg-grid">
                {displayedTalkgroups.map(
                  (item) => (
                    <button
                      key={item.tg}
                      className={`home-favorite-tile fm-talkgroup-tile ${
                        item.active
                          ? 'is-active'
                          : ''
                      } ${
                        item.connected
                          ? 'is-connected'
                          : ''
                      }`}
                      onClick={() =>
                        selectTalkgroup(
                          item.tg
                        )
                      }
                      aria-disabled={
                        !talkgroups?.control.enabled
                      }
                      title={
                        talkgroups
                          .control
                          .enabled
                          ? `${tgLabel(item.tg)} auswählen`
                          : 'TG-Steuerung ist im Backend noch deaktiviert.'
                      }
                    >
                      {/* TG CONTROL FM FEEDBACK */}
                      {pendingTg ===
                        String(item.tg) && (
                        <div className="tg-control-feedback is-pending">
                          <span className="tg-control-spinner" />
                          Wechselt…
                        </div>
                      )}

                      {tgControlError?.tg ===
                        String(item.tg) && (
                        <div className="tg-control-feedback is-error">
                          {tgControlError.message}
                        </div>
                      )}

                      {/* TG LEAVE FM ERROR */}

                      {item.connected &&
                        tgControlError?.tg ===
                          '0' && (
                          <div className="tg-control-feedback is-error">
                            {tgControlError.message}
                          </div>
                        )}

                      <div className="home-favorite-top">
                        <span>
                          TG
                        </span>

                        <div className="fm-talkgroup-top-right">
                          {item.connected && (
                            <span className="fm-talkgroup-state is-connected">
                              Verbunden
                            </span>
                          )}

                          {!item.connected &&
                            item.active && (
                              <span className="fm-talkgroup-state is-active">
                                Aktiv
                              </span>
                            )}

                          {/* TG LEAVE FM TILE */}

                          {item.connected &&
                            talkgroups?.using_default ===
                              false && (
                              <span
                                className={`tg-leave-tile ${
                                  pendingTg === '0'
                                    ? 'is-pending'
                                    : ''
                                }`}
                                title="Talkgroup verlassen"
                                onClick={(event) => {
                                  event.stopPropagation();

                                  if (
                                    pendingTg ===
                                    null
                                  ) {
                                    selectTalkgroup(
                                      '0'
                                    );
                                  }
                                }}
                              >
                                {pendingTg === '0'
                                  ? 'Trenne…'
                                  : 'Verlassen'}
                              </span>
                            )}

                          <span
                            className={`favorite-star ${
                              favoriteTgs.includes(
                                item.tg
                              )
                                ? 'is-favorite'
                                : ''
                            }`}
                            role="button"
                            tabIndex={0}
                            title={
                              favoriteTgs.includes(
                                item.tg
                              )
                                ? 'Aus Favoriten entfernen'
                                : 'Als Favorit überwachen'
                            }
                            onClick={(event) => {
                              event.stopPropagation();

                              toggleFavorite(
                                item.tg
                              );
                            }}
                            onKeyDown={(event) => {
                              if (
                                event.key === 'Enter' ||
                                event.key === ' '
                              ) {
                                event.preventDefault();
                                event.stopPropagation();

                                toggleFavorite(
                                  item.tg
                                );
                              }
                            }}
                          >
                            ★
                          </span>
                        </div>
                      </div>

                      <strong>
                        {item.tg}
                      </strong>

                      <span
                        className={`home-favorite-tg-name ${
                          tgNames[String(Number(item.tg))] ||
                          tgNames[String(item.tg)]
                            ? ''
                            : 'is-empty'
                        }`}
                      >
                        {tgNames[String(Number(item.tg))] ||
                          tgNames[String(item.tg)] ||
                          '\u00A0'}
                      </span>

                      <div className="home-favorite-bottom">
                        {item.calls.length ? (
                          <>
                            <span className="live-text">
                              Jetzt aktiv
                            </span>

                            <span className="favorite-callsign">
                              {item.calls
                                .slice(0, 2)
                                .join(', ')}
                            </span>
                          </>
                        ) : favoriteHistory[
                            item.tg
                          ]?.found &&
                          favoriteHistory[
                            item.tg
                          ]?.last_seen_epoch ? (
                          <>
                            <span className="favorite-last">
                              Letzte Aktivität:{' '}
                              {relativeAge(
                                favoriteHistory[
                                  item.tg
                                ].last_seen_epoch
                              )}
                            </span>

                            <span className="favorite-callsign">
                              {favoriteHistory[
                                item.tg
                              ].call ||
                                '—'}
                            </span>
                          </>
                        ) : (
                          <span className="favorite-last">
                            Noch keine Aktivität gespeichert
                          </span>
                        )}
                      </div>
                    </button>
                  )
                )}

                {!displayedTalkgroups
                  .length && (
                  <div className="empty-card">
                    {tgView ===
                    'favorites'
                      ? 'Noch keine Favoriten gespeichert. Markiere eine Talkgroup mit dem Stern.'
                      : 'Momentan werden keine aktiven Talkgroups geliefert.'}
                  </div>
                )}
              </div>
            </section>

            {/* TOP TALKGROUPS SECTION */}

            <section className="section top-talkgroups-section">

              <div className="section-heading">
                <div>

                  <span className="eyebrow">
                    STATISTIK
                  </span>

                  <h2>
                    Top Talkgroups
                  </h2>

                </div>
              </div>


              {topTalkgroupsLoading && (
                <div className="top-talkgroups-status">
                  Statistik wird geladen…
                </div>
              )}


              {topTalkgroupsError && (
                <div className="top-talkgroups-status is-error">
                  {topTalkgroupsError}
                </div>
              )}


              <div className="top-talkgroups-columns">

                {[
                  {
                    range:
                      '24h' as const,
                    title:
                      '24 Stunden Aktivität',
                  },
                  {
                    range:
                      '7d' as const,
                    title:
                      '7 Tage Aktivität',
                  },
                  {
                    range:
                      '30d' as const,
                    title:
                      '30 Tage Aktivität',
                  },
                ].map(
                  (period) => (

                    <div
                      className="top-talkgroups-period"
                      key={
                        period.range
                      }
                    >

                      <h3>
                        {period.title}
                      </h3>


                      <div className="top-talkgroups-mini-list">

                        {topTalkgroupsByRange[
                          period.range
                        ].map(
                          (
                            item,
                            index
                          ) => {

                            const connected =
                              String(
                                connectedTg ??
                                ''
                              ) ===
                              String(
                                item.tg
                              );

                            const pending =
                              String(
                                pendingTg ??
                                ''
                              ) ===
                              String(
                                item.tg
                              );

                            return (

                              <button
                                type="button"
                                key={
                                  item.tg
                                }
                                className={`top-talkgroup-mini ${
                                  connected
                                    ? 'is-connected'
                                    : ''
                                } ${
                                  pending
                                    ? 'is-pending'
                                    : ''
                                }`}
                                disabled={
                                  !talkgroups?.control.enabled
                                }
                                onClick={() =>
                                  selectTalkgroup(
                                    item.tg
                                  )
                                }
                                title={`${tgLabel(item.tg)} auswählen`}
                              >

                                <span className="top-talkgroup-mini-rank">
                                  #
                                  {index + 1}
                                </span>


                                <span className="top-talkgroup-mini-main">

                                  <strong>
                                    {tgLabel(
                                      item.tg
                                    )}
                                  </strong>

                                  <small>

                                    {Number(
                                      item.callers ||
                                      0
                                    ).toLocaleString(
                                      'de-DE'
                                    )}

                                    {' Rufzeichen · '}

                                    {Number(
                                      item.cnt ||
                                      0
                                    ).toLocaleString(
                                      'de-DE'
                                    )}

                                    {' Durchgänge'}

                                  </small>

                                </span>


                                <span className="top-talkgroup-mini-time">

                                  {pending
                                    ? 'Wechselt…'
                                    : item.duration_label}

                                </span>

                              </button>

                            );
                          }
                        )}

                      </div>

                    </div>

                  )
                )}

              </div>


              <div className="top-talkgroups-source">
                Quelle: FM-Funknetz · Rangfolge nach Sprechzeit
              </div>

            </section>



          </main>
        </>
      )}

      {view === 'echolink' && (

        <>

          <section className="page-hero">

            <div className="hero-glow hero-glow-green" />

            <div className="hero-glow hero-glow-cyan" />

            <div className="content">

              <span className="eyebrow">
                ECHOLINK
              </span>

              <h1>
                {echoLink.callsign ||
                  'EchoLink'}
              </h1>

              <p>
                Dein Node, deine Verbindungen
                und deine EchoLink-Favoriten.
              </p>

            </div>

          </section>


          <main className="content main-content el2-main">


            {echoError && (

              <div className="el2-error">
                {echoError}
              </div>

            )}


            <section className="el2-top">


              <article className="el2-node-card">

                <div className="el2-card-head">

                  <span className="eyebrow">
                    DEIN NODE
                  </span>

                  <span
                    className={`el2-directory ${
                      echoLink.directory_online
                        ? 'online'
                        : 'offline'
                    }`}
                  >

                    <span />

                    {echoLink.directory_online
                      ? 'EchoLink online'
                      : 'EchoLink offline'}

                  </span>

                </div>


                <div className="el2-own-call">
                  {echoLink.callsign || '—'}
                </div>


                <div className="el2-own-node">

                  <span>
                    Node
                  </span>

                  <strong>
                    {echoLink.node_id || '—'}
                  </strong>

                </div>


                <button
                  type="button"
                  className={
                    echoLink.module_active
                      ? 'el2-toggle secondary'
                      : 'el2-toggle'
                  }
                  disabled={
                    echoBusy !== null ||
                    !echoLink.control?.enabled
                  }
                  onClick={() =>
                    echoControl(
                      echoLink.module_active
                        ? 'deactivate'
                        : 'activate'
                    )
                  }
                >

                  {echoBusy === 'activate'
                    ? 'Aktiviere…'
                    : echoBusy === 'deactivate'
                    ? 'Deaktiviere…'
                    : echoLink.module_active
                    ? 'EchoLink deaktivieren'
                    : 'EchoLink aktivieren'}

                </button>

              </article>


              <article className="el2-live-card">

                <div className="el2-card-head">

                  <span className="eyebrow">
                    AKTUELL VERBUNDEN
                  </span>

                  {!!echoLink.client_count && (

                    <button
                      type="button"
                      className="el2-disconnect"
                      disabled={
                        echoBusy !== null
                      }
                      onClick={() =>
                        echoControl(
                          'disconnect'
                        )
                      }
                    >
                      Trennen
                    </button>

                  )}

                </div>


                {echoLink.clients?.length ? (

                  <div className="el2-current-list">

                    {echoLink.clients.map(
                      (client: any) => (

                        <div
                          className="el2-current-row"
                          key={client.id}
                        >

                          <div>

                            <strong>
                              {client.callsign}
                            </strong>

                            <span>

                              {client.direction === 'incoming'
                                ? 'Eingehend'
                                : client.direction === 'outgoing'
                                ? 'Ausgehend'
                                : 'Verbunden'}

                            </span>

                          </div>


                          <div>

                            <strong>
                              {echoDuration(
                                client.duration
                              )}
                            </strong>

                            <span>
                              seit {echoTime(
                                client.connected_at
                              )}
                            </span>

                          </div>

                        </div>

                      )
                    )}

                  </div>

                ) : (

                  <div className="el2-live-empty">

                    <strong>
                      Niemand verbunden
                    </strong>

                    <span>
                      Momentan besteht keine
                      EchoLink-Verbindung.
                    </span>

                  </div>

                )}

              </article>


            </section>



            <section className="section el2-search-section">

              <div className="section-heading">

                <div>

                  <span className="eyebrow">
                    ECHOLINK DIRECTORY
                  </span>

                  <h2>
                    Station oder Node suchen
                  </h2>

                </div>

              </div>


              <form
                className="el2-search"
                onSubmit={(event) => {

                  event.preventDefault();

                  connectEchoDirect();

                }}
              >

                <input
                  type="text"
                  value={
                    echoSearchQuery
                  }
                  onChange={(event) =>
                    setEchoSearchQuery(
                      event.target.value
                    )
                  }
                  placeholder="Rufzeichen oder Node-ID, z. B. DA6IT-L"
                  autoComplete="off"
                />

                <button
                  type="button"
                    className="el2-search-secondary"
                    onClick={() => echoSearch()}
                  disabled={
                    echoSearchBusy ||
                    !echoSearchQuery.trim()
                  }
                >

                  {echoSearchBusy
                    ? 'Suche…'
                    : 'Suchen'}

                </button>

                  <button
                    type="submit"
                    className="el2-connect-button"
                    disabled={
                      echoSearchBusy ||
                      echoBusy !== null ||
                      !echoSearchQuery.trim()
                    }
                  >

                    {echoSearchBusy ||
                    echoBusy !== null
                      ? 'Verbinde…'
                      : 'Verbinden'}

                  </button>

</form>


              {echoSearchError && (

                <div className="el2-search-error">
                  {echoSearchError}
                </div>

              )}


              {echoSearchDone &&
               !echoSearchError &&
               echoSearchResults.length === 0 && (

                <div className="el2-search-empty">

                  Keine registrierte EchoLink-Node
                  zu dieser Suche gefunden.

                </div>

              )}


              {!!echoSearchResults.length && (

                <div className="el2-search-results">

                  {echoSearchResults.map(
                    (result: any) => (

                      <article
                        className="el2-result"
                        key={
                          `${result.callsign}-${result.node_id}`
                        }
                      >

                        <div className="el2-result-main">

                          <div>

                            <strong>
                              {result.callsign}
                            </strong>

                            <span>
                              Node {result.node_id}
                            </span>

                          </div>


                          <div className="el2-result-meta">

                            <span
                              className={`el2-status ${
                                result.status ||
                                'offline'
                              }`}
                            >

                              {echoStatusText(
                                result.status
                              )}

                            </span>


                            <button
                              type="button"
                              className="el2-result-close"
                              title="Suchergebnis schließen"
                              aria-label="Suchergebnis schließen"
                              onClick={() => {

                                setEchoSearchResults(
                                  []
                                );

                                setEchoSearchDone(
                                  false
                                );

                                setEchoSearchError(
                                  null
                                );

                              }}
                            >
                              ×
                            </button>

                          </div>

                        </div>


                        {result.location && (

                          <div className="el2-location">
                            {result.location}
                          </div>

                        )}


                        <div className="el2-result-actions">

                          <button
                            type="button"
                            className="secondary"
                            disabled={
                              echoBusy !== null
                            }
                            onClick={() => {

                              setEchoSearchResults(
                                []
                              );

                              setEchoSearchDone(
                                false
                              );

                              setEchoSearchQuery(
                                ''
                              );

                              echoSaveSearchResult(
                                result
                              );

                            }}
                          >

                            {echoBusy ===
                              `save-search:${result.node_id}`
                              ? 'Speichere…'
                              : 'Speichern'}

                          </button>


                          <button
                            type="button"
                            disabled={
                              echoBusy !== null ||
                              result.status !== 'on'
                            }
                            onClick={() => {

                              setEchoSearchResults(
                                []
                              );

                              setEchoSearchDone(
                                false
                              );

                              setEchoSearchQuery(
                                ''
                              );

                              echoConnect(
                                result.node_id
                              );

                            }}
                          >

                            {echoBusy ===
                              `connect:${result.node_id}`
                              ? 'Verbinde…'
                              : result.status === 'busy'
                              ? 'Busy'
                              : result.status === 'offline'
                              ? 'Offline'
                              : 'Verbinden'}

                          </button>

                        </div>

                      </article>

                    )
                  )}

                </div>

              )}

            </section>



            <section className="section">

              <div className="section-heading">

                <div>

                  <span className="eyebrow">
                    FAVORITEN
                  </span>

                  <h2>
                    Meine EchoLink Nodes
                  </h2>

                </div>

              </div>


              {echoLink.nodes?.length ? (

                <div className="el2-favourites">

                  {echoLink.nodes.map(
                    (node: any) => (

                      <article
                        className="el2-favourite"
                        key={
                          node.node_id
                        }
                      >

                        <div className="el2-favourite-head">

                          <span
                            className={`el2-status ${
                              node.status ||
                              'offline'
                            }`}
                          >

                            {echoStatusText(
                              node.status
                            )}

                          </span>


                          <button
                            type="button"
                            className="el2-remove"
                            title="Node entfernen"
                            disabled={
                              echoBusy !== null
                            }
                            onClick={() =>
                              echoDeleteNode(
                                node.node_id
                              )
                            }
                          >
                            ×
                          </button>

                        </div>


                        <strong className="el2-favourite-call">
                          {node.callsign}
                        </strong>

                        <span className="el2-favourite-node">
                          Node {node.node_id}
                        </span>


                        {node.location && (

                          <span className="el2-favourite-location">
                            {node.location}
                          </span>

                        )}


                        <button
                          type="button"
                          className="el2-connect"
                          disabled={
                            echoBusy !== null ||
                            node.status !== 'on'
                          }
                          onClick={() =>
                            echoConnect(
                              node.node_id
                            )
                          }
                        >

                          {echoBusy ===
                            `connect:${node.node_id}`
                            ? 'Verbinde…'
                            : node.status === 'busy'
                            ? 'Busy'
                            : node.status === 'offline'
                            ? 'Offline'
                            : 'Verbinden'}

                        </button>

                      </article>

                    )
                  )}

                </div>

              ) : (

                <div className="el2-empty">

                  Suche oben nach einer
                  EchoLink-Station und speichere
                  sie als Favorit.

                </div>

              )}

            </section>



            <section className="section">

              <div className="section-heading">

                <div>

                  <span className="eyebrow">
                    VERLAUF
                  </span>

                  <h2>
                    EchoLink History
                  </h2>

                </div>

              </div>


              {echoLink.history?.length ? (

                <div className="el2-history">

                  {echoLink.history.map(
                    (entry: any) => (

                      <div
                        className="el2-history-row"
                        key={entry.id}
                      >

                        <div>

                          <strong>
                            {echoDate(
                              entry.connected_at
                            )}
                          </strong>

                          <span>
                            {echoTime(
                              entry.connected_at
                            )}
                          </span>

                        </div>


                        <div>

                          <strong>
                            {entry.callsign}
                          </strong>

                          <span>

                            {entry.direction === 'incoming'
                              ? 'Eingehend'
                              : entry.direction === 'outgoing'
                              ? 'Ausgehend'
                              : 'EchoLink'}

                          </span>

                        </div>


                        <strong className="el2-history-duration">

                          {echoDuration(
                            entry.duration
                          )}

                        </strong>

                      </div>

                    )
                  )}

                </div>

              ) : (

                <div className="el2-empty">

                  Noch keine EchoLink-Verbindungen
                  im Verlauf.

                </div>

              )}

            </section>


          </main>

        </>

      )}


      {view === 'shari' && (
        <>
          <section className="page-hero">
            <div className="hero-glow hero-glow-green" />
            <div className="hero-glow hero-glow-cyan" />

            <div className="content shari-hero">
              <div>
                <span className="eyebrow">
                  SHARI · FUNKMODUL
                </span>

                <h1>
                  SA818 Hardware
                </h1>

                <p>
                  Funkparameter direkt aus dem
                  eingebauten Funkmodul auslesen.
                </p>
              </div>

              <button
                className="button button-outline"
                disabled={shariHardwareBusy}
                onClick={() =>
                  void loadShariHardware()
                }
              >
                {shariHardwareBusy
                  ? 'Wird ausgelesen …'
                  : 'Neu auslesen'}
              </button>
            </div>
          </section>

          <main className="content main-content">

            <div className="shari-readonly-banner">
              <strong>
                Read-only
              </strong>

              <span>
                Dieser erste Stand liest ausschließlich
                DMOCONNECT, VERSION und DMOREADGROUP.
                Es werden keine Funkparameter verändert.
              </span>
            </div>

            {shariHardwareError && (
              <div className="shari-hardware-error">
                <strong>
                  Funkmodul nicht erreichbar
                </strong>

                <span>
                  {shariHardwareError}
                </span>
              </div>
            )}

            <div className="system-grid">

              <article className="system-card">
                <span>
                  Modul
                </span>

                <strong>
                  {shariHardware?.module || '—'}
                </strong>

                <small>
                  {shariHardware?.source ||
                    'SA818 UART'}
                </small>
              </article>

              <article className="system-card">
                <span>
                  Firmware
                </span>

                <strong>
                  {shariHardware?.firmware || '—'}
                </strong>

                <small>
                  {shariHardware?.firmware_raw ||
                    'Noch nicht ausgelesen'}
                </small>
              </article>

              <article className="system-card">
                <span>
                  Schnittstelle
                </span>

                <strong>
                  {shariHardware?.port ||
                    '/dev/ttyUSB0'}
                </strong>

                <small>
                  {shariHardware?.baudrate ||
                    9600}{' '}
                  Baud
                </small>
              </article>

              <article className="system-card">
                <span>
                  Verbindung
                </span>

                <strong>
                  {shariHardware?.available
                    ? 'Online'
                    : shariHardwareBusy
                    ? 'Lese …'
                    : 'Nicht geprüft'}
                </strong>

                <small>
                  {shariHardware?.updated_at
                    ? new Date(
                        shariHardware.updated_at
                      ).toLocaleString(
                        'de-DE'
                      )
                    : '—'}
                </small>
              </article>

            </div>

            <section className="section">

              <div className="section-heading">

                <div>
                  <span className="eyebrow">
                    AKTUELLE EINSTELLUNGEN
                  </span>

                  <h2>
                    Funkparameter
                  </h2>
                </div>

                <span className="shari-source">
                  direkt aus dem SA818S
                </span>

              </div>

              <div className="shari-parameter-grid">

                <article className="shari-parameter">
                  <span>
                    TX-Frequenz
                  </span>

                  <strong>
                    {shariHardware?.tx_frequency_mhz
                      ? `${shariHardware.tx_frequency_mhz} MHz`
                      : '—'}
                  </strong>

                  <small>
                    Sendefrequenz
                  </small>
                </article>

                <article className="shari-parameter">
                  <span>
                    RX-Frequenz
                  </span>

                  <strong>
                    {shariHardware?.rx_frequency_mhz
                      ? `${shariHardware.rx_frequency_mhz} MHz`
                      : '—'}
                  </strong>

                  <small>
                    Empfangsfrequenz
                  </small>
                </article>

                <article className="shari-parameter">
                  <span>
                    Kanalraster
                  </span>

                  <strong>
                    {shariHardware?.bandwidth_khz
                      ? `${shariHardware.bandwidth_khz} kHz`
                      : '—'}
                  </strong>

                  <small>
                    {shariHardware?.bandwidth_khz === 12.5
                      ? 'Narrowband'
                      : shariHardware?.bandwidth_khz === 25
                      ? 'Wideband'
                      : '—'}
                  </small>
                </article>

                <article className="shari-parameter">
                  <span>
                    CTCSS TX
                  </span>

                  <strong>
                    {shariHardware?.tx_cxcss_label ||
                      '—'}
                  </strong>

                  <small>
                    Code{' '}
                    {shariHardware?.tx_cxcss_code ||
                      '—'}
                  </small>
                </article>

                <article className="shari-parameter">
                  <span>
                    CTCSS RX
                  </span>

                  <strong>
                    {shariHardware?.rx_cxcss_label ||
                      '—'}
                  </strong>

                  <small>
                    Code{' '}
                    {shariHardware?.rx_cxcss_code ||
                      '—'}
                  </small>
                </article>

                <article className="shari-parameter">
                  <span>
                    Squelch
                  </span>

                  <strong>
                    {shariHardware?.squelch ??
                      '—'}
                  </strong>

                  <small>
                    Bereich 0–8
                  </small>
                </article>

              </div>

            </section>

            <section className="section">

              <div className="section-heading">
                <div>
                  <span className="eyebrow">
                    NÄCHSTER SCHRITT
                  </span>

                  <h2>
                    Konfiguration
                  </h2>
                </div>
              </div>

              <div className="shari-config-preview">

                <div>
                  <strong>
                    Funkparameter bearbeiten
                  </strong>

                  <span>
                    TX/RX-Frequenz, Raster,
                    CTCSS und Squelch werden
                    hier im nächsten Schritt
                    editierbar.
                  </span>
                </div>

                <button
                  className="button button-primary"
                  disabled
                >
                  Am Modul speichern
                </button>

              </div>

            </section>

          </main>
        </>
      )}

      {view === 'svxlink-config' && (
        <>
          <section className='page-hero'>
            <div className='hero-glow hero-glow-green' />
            <div className='hero-glow hero-glow-cyan' />

            <div className='content'>
              <span className='eyebrow'>
                KONFIGURATION · SVXLINK
              </span>

              <h1>SvxLink</h1>

              <p>
                Zentrale Einstellungen für SvxLink,
                Audio, PTT und die lokale Funklogik.
              </p>
            </div>
          </section>

          <main className='content main-content'>
            <div className='shari-readonly-banner'>
              <strong>Read-only</strong>
              <span>
                Dieser Bereich zeigt zunächst nur ausgewählte,
                unkritische SvxLink-Einstellungen. Schreibzugriffe
                folgen später kontrolliert mit Validierung und Backup.
              </span>
            </div>

            <div className='system-grid'>
              <article className='system-card'>
                <span>Rufzeichen</span>
                <strong>{callsign}</strong>
                <small>SimplexLogic</small>
              </article>

              <article className='system-card'>
                <span>RX Audio</span>
                <strong>
                  {status.config?.Rx1?.AUDIO_DEV || '—'}
                </strong>
                <small>Empfänger</small>
              </article>

              <article className='system-card'>
                <span>TX Audio</span>
                <strong>
                  {status.config?.Tx1?.AUDIO_DEV || '—'}
                </strong>
                <small>Sender</small>
              </article>

              <article className='system-card'>
                <span>PTT</span>
                <strong>
                  {status.config?.Tx1?.PTT_TYPE || '—'}
                </strong>
                <small>
                  {status.config?.Tx1?.HID_DEVICE ||
                    'Kein HID-Gerät angegeben'}
                </small>
              </article>
            </div>

            <section className='section'>
              <div className='section-heading'>
                <div>
                  <span className='eyebrow'>
                    NÄCHSTER SCHRITT
                  </span>
                  <h2>SvxLink konfigurieren</h2>
                </div>
              </div>

              <div className='shari-config-preview'>
                <div>
                  <strong>
                    Konfiguration bearbeiten
                  </strong>
                  <span>
                    Audio, PTT, Logics und weitere SvxLink-Parameter
                    werden hier schrittweise editierbar.
                  </span>
                </div>

                <button
                  className='button button-primary'
                  disabled
                >
                  Änderungen speichern
                </button>
              </div>
            </section>
          </main>
        </>
      )}

      {view === 'system' && (
        <>
          <section className="page-hero">
            <div className="hero-glow hero-glow-green" />
            <div className="hero-glow hero-glow-cyan" />

            <div className="content">
              <span className="eyebrow">
                SYSTEM
              </span>

              <h1>
                Shari & SvxLink
              </h1>

              <p>
                Technische Daten und
                Diagnose getrennt von
                der täglichen
                Bedienung.
              </p>
            </div>
          </section>

          <main className="content main-content">
            <div className="system-grid">
              <article className="system-card">
                <span>
                  SvxLink
                </span>

                <strong>
                  {status.svxlink
                    .status}
                </strong>

                <small>
                  PID{' '}
                  {status.svxlink
                    .pid || '—'} ·{' '}
                  {
                    status.svxlink
                      .substate
                  }
                </small>
              </article>

              <article className="system-card">
                <span>
                  Station
                </span>

                <strong>
                  {callsign}
                </strong>

                <small>
                  {location}
                </small>
              </article>

              <article className="system-card">
                <span>
                  Frequenz
                </span>

                <strong>
                  {txFrequency} MHz
                </strong>

                <small>
                  RX {rxFrequency} ·{' '}
                  {mode}
                </small>
              </article>

              <article className="system-card">
                <span>
                  FM-Funknetz
                </span>

                <strong>
                  {talkgroups.external
                    .available
                    ? 'Online'
                    : 'Nicht verfügbar'}
                </strong>

                <small>
                  Externe
                  Live-Daten
                </small>
              </article>

              <article className="system-card">
                <span>
                  Lokale TG
                </span>

                <strong>
                  {connectedTg
                    ? tgLabel(connectedTg)
                    : '—'}
                </strong>

                <small>
                  {connectedConfirmed
                    ? 'Aus SvxLink-Log'
                    : 'Aus Konfiguration'}
                </small>
              </article>

              <article className="system-card">
                <span>
                  Reflector
                </span>

                <strong>
                  {
                    status.reflector
                      .count
                  }{' '}
                  Events
                </strong>

                <small>
                  Lokale
                  Logauswertung
                </small>
              </article>
            </div>

            <UpdateCenter api={api} />

            <section className="section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">
                    LETZTE EVENTS
                  </span>

                  <h2>
                    Reflector
                  </h2>
                </div>
              </div>

              <div className="event-list">
                {status.reflector.events
                  .slice(-10)
                  .reverse()
                  .map(
                    (
                      event,
                      index
                    ) => (
                      <div
                        className="event-row"
                        key={`${event.timestamp}-${index}`}
                      >
                        <StatusDot
                          active={
                            event.event ===
                            'joined'
                          }
                        />

                        <strong>
                          {
                            event.callsign
                          }
                        </strong>

                        <span>
                          {event.event ===
                          'joined'
                            ? 'beigetreten'
                            : 'verlassen'}
                        </span>

                        <time>
                          {
                            event.timestamp
                          }
                        </time>
                      </div>
                    )
                  )}

                {!status.reflector
                  .events.length && (
                  <div className="empty-card">
                    Keine
                    Reflector-
                    Ereignisse
                    vorhanden.
                  </div>
                )}
              </div>
            </section>
          </main>
        </>
      )}

      <footer className="footer">
        <div className="content footer-inner">
          <span>
            DA6IT · Shari
          </span>

          <span>
            SvxLink WebUI ·{' '}
            {callsign}
          </span>
        </div>
      </footer>
    </div>
  );
}

createRoot(
  document.getElementById(
    'root'
  )!
).render(<App />);
