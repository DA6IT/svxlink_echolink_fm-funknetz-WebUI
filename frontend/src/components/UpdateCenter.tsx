import {
  useCallback,
  useEffect,
  useState,
} from 'react';

import './UpdateCenter.css';

import UpdateChangelog
  from './update/UpdateChangelog';

import UpdateProgress
  from './update/UpdateProgress';

import UpdateSummary
  from './update/UpdateSummary';

import {
  terminalStates,
} from './update/state';

import type {
  UpdateInfo,
} from './update/types';


type Props = {
  api: string;
};


export default function UpdateCenter({
  api,
}: Props) {
  const [
    info,
    setInfo,
  ] = useState<UpdateInfo | null>(
    null
  );

  const [
    busy,
    setBusy,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState('');


  const load =
    useCallback(
      async (
        quiet = false
      ) => {
        if (!quiet) {
          setBusy(true);
        }

        setError('');

        try {
          const response =
            await fetch(
              `${api}/system/update`,
              {
                cache:
                  'no-store',
              }
            );

          if (!response.ok) {
            throw new Error(
              'Update-Status konnte nicht geladen werden.'
            );
          }

          const data:
            UpdateInfo =
              await response.json();

          setInfo(
            data
          );

        } catch (caught) {
          setError(
            caught instanceof Error
              ? caught.message
              : 'Update-Status konnte nicht geladen werden.'
          );

        } finally {
          if (!quiet) {
            setBusy(false);
          }
        }
      },
      [api]
    );


  useEffect(
    () => {
      void load();

      const timer =
        window.setInterval(
          () => {
            void load(
              true
            );
          },
          5000
        );

      return () =>
        window.clearInterval(
          timer
        );
    },
    [load]
  );


  const running =
    Boolean(
      info?.job &&
      !terminalStates.has(
        info.job.state || ''
      )
    );


  useEffect(
    () => {
      if (!running) {
        return;
      }

      const timer =
        window.setInterval(
          () => {
            void load(
              true
            );
          },
          1500
        );

      return () =>
        window.clearInterval(
          timer
        );
    },
    [
      running,
      load,
    ]
  );


  const install =
    async () => {
      if (
        !info?.can_install
        || busy
      ) {
        return;
      }

      if (
        !window.confirm(
          'Das verfügbare Update jetzt installieren?'
        )
      ) {
        return;
      }

      setBusy(true);
      setError('');

      try {
        const response =
          await fetch(
            `${api}/system/update/install`,
            {
              method:
                'POST',
            }
          );

        const data =
          await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail ||
            'Update konnte nicht gestartet werden.'
          );
        }

        await load(
          true
        );

      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : 'Update konnte nicht gestartet werden.'
        );

      } finally {
        setBusy(false);
      }
    };


  return (
    <section className="section update-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">
            SOFTWARE
          </span>

          <h2>
            Updates
          </h2>
        </div>

        <button
          className="text-button"
          onClick={() =>
            void load()
          }
          disabled={
            busy ||
            running
          }
        >
          {busy
            ? 'Prüfe …'
            : 'Neu prüfen ↻'}
        </button>
      </div>

      <div className="update-card">
        <UpdateSummary
          info={info}
        />

        {running &&
          info?.job && (
          <UpdateProgress
            job={
              info.job
            }
          />
        )}

        {info?.job?.state ===
          'failed' && (
          <div className="update-error">
            <strong>
              Update fehlgeschlagen
            </strong>

            <span>
              {info.job.error ||
                info.job.message ||
                'Unbekannter Fehler.'}
            </span>

            {info.job.rollback_ok ===
              true && (
              <small>
                Der vorherige Stand wurde
                erfolgreich wiederhergestellt.
              </small>
            )}
          </div>
        )}

        {info?.changelog && (
          <div className="update-changelog">
            <strong>
              Changelog
            </strong>

            <UpdateChangelog
              value={
                info.changelog
              }
            />
          </div>
        )}

        {error && (
          <div className="update-error">
            {error}
          </div>
        )}

        <div className="update-actions">
          <button
            className="button button-primary"
            onClick={() =>
              void install()
            }
            disabled={
              !info?.can_install ||
              busy ||
              running
            }
          >
            {running
              ? 'Update läuft …'
              : 'Update installieren'}
          </button>

          <span>
            {!info?.enabled
              ? 'Installation ist administrativ deaktiviert.'
              : !info?.rootless_ready
                ? 'Rootless Updater ist noch nicht bereit.'
                : info?.dirty
                  ? 'Lokale Änderungen blockieren das Update.'
                  : !info?.branch_ok
                    ? 'Update auf Entwicklungsbranch blockiert.'
                    : !info?.available
                      ? 'Kein neues Update verfügbar.'
                      : 'Update wird vor Aktivierung vollständig geprüft.'}
          </span>
        </div>
      </div>
    </section>
  );
}
