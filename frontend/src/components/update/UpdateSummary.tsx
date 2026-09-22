import type {
  UpdateInfo,
} from './types';

import {
  updateStateClass,
  updateStateLabel,
} from './state';


type Props = {
  info: UpdateInfo | null;
};


export default function UpdateSummary({
  info,
}: Props) {
  return (
    <>
      <div className="update-version-grid">
        <div className="update-version-item">
          <span>
            Installiert
          </span>

          <strong>
            {info?.version || '—'}
          </strong>

          <small>
            {info?.revision_short
              ? `Revision ${info.revision_short}`
              : 'Revision unbekannt'}
          </small>
        </div>

        <div className="update-version-item">
          <span>
            Update-Kanal
          </span>

          <strong>
            {info?.channel.name ||
              'main'}
          </strong>

          <small>
            {info?.channel.version
              ? `${info.channel.version} · `
              : ''}

            {info?.channel.revision_short
              ? `Revision ${info.channel.revision_short}`
              : 'nicht erreichbar'}
          </small>
        </div>

        <div className="update-version-item">
          <span>
            Rootless Updater
          </span>

          <strong>
            {info?.rootless_ready
              ? 'Bereit'
              : 'Noch nicht bereit'}
          </strong>

          <small>
            Updater:{' '}
            {info?.updater_user ||
              'nicht aktiv'}
          </small>
        </div>
      </div>

      <div className="update-status-line">
        <span
          className={
            `update-state ${updateStateClass(info)}`
          }
        >
          {updateStateLabel(info)}
        </span>

        <span>
          {info?.job?.message ||
            info?.message ||
            'Noch nicht geprüft.'}
        </span>
      </div>

      {info?.dirty && (
        <div className="update-warning">
          Der lokale Git-Checkout enthält
          uncommittete Änderungen. Automatische
          Updates sind auf diesem Stand blockiert.
        </div>
      )}

      {!info?.branch_ok &&
        info && (
        <div className="update-warning">
          Aktiver Entwicklungsbranch:{' '}
          <strong>
            {info.branch}
          </strong>.
          Der automatische Update-Kanal ist{' '}
          <strong>
            {info.channel.name}
          </strong>.
        </div>
      )}

      {!info?.rootless_ready &&
        info && (
        <div className="update-permissions">
          <strong>
            Rootless-Vorbereitung
          </strong>

          <div>
            <span>
              Anwendung
            </span>
            <b>
              {info.permissions.application
                ? '✓'
                : '–'}
            </b>

            <span>
              Git
            </span>
            <b>
              {info.permissions.git
                ? '✓'
                : '–'}
            </b>

            <span>
              Update-Daten
            </span>
            <b>
              {info.permissions.update_data
                ? '✓'
                : '–'}
            </b>

            <span>
              Frontend
            </span>
            <b>
              {info.permissions.frontend
                ? '✓'
                : '–'}
            </b>
          </div>
        </div>
      )}
    </>
  );
}
