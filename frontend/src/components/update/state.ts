import type {
  UpdateInfo,
} from './types';


export const terminalStates =
  new Set([
    'completed',
    'prepared',
    'failed',
  ]);


export function updateStateLabel(
  info: UpdateInfo | null
) {
  if (
    info?.job &&
    !terminalStates.has(
      info.job.state || ''
    )
  ) {
    return 'Update läuft';
  }

  if (
    info?.job?.state ===
    'failed'
  ) {
    return 'Update fehlgeschlagen';
  }

  if (
    info?.job?.state ===
    'completed'
  ) {
    return 'Update abgeschlossen';
  }

  if (info?.available) {
    return 'Update verfügbar';
  }

  if (
    info?.relation ===
    'local_ahead'
  ) {
    return 'Entwicklungsstand';
  }

  return 'Aktuell';
}


export function updateStateClass(
  info: UpdateInfo | null
) {
  if (
    info?.job?.state ===
    'failed'
  ) {
    return 'is-error';
  }

  if (
    info?.job &&
    !terminalStates.has(
      info.job.state || ''
    )
  ) {
    return 'is-running';
  }

  if (
    info?.available ||
    info?.job?.state ===
      'completed'
  ) {
    return 'is-ready';
  }

  return 'is-current';
}
