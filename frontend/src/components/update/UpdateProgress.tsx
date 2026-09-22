import type {
  UpdateJob,
} from './types';


type Props = {
  job: UpdateJob;
};


export default function UpdateProgress({
  job,
}: Props) {
  const progress =
    Math.max(
      0,
      Math.min(
        100,
        Number(
          job.progress || 0
        )
      )
    );

  return (
    <>
      <div className="update-progress">
        <div className="update-progress-head">
          <strong>
            {job.target_version
              ? `Update auf ${job.target_version}`
              : 'Update wird vorbereitet'}
          </strong>

          <span>
            {progress} %
          </span>
        </div>

        <div className="update-progress-track">
          <div
            className="update-progress-bar"
            style={{
              width:
                `${progress}%`,
            }}
          />
        </div>

        <small>
          Phase:{' '}
          {job.state || '—'}
        </small>
      </div>

      {job.log_tail &&
        job.log_tail.length > 0 && (
        <details className="update-log">
          <summary>
            Update-Protokoll
          </summary>

          <pre>
            {job.log_tail.join(
              '\n'
            )}
          </pre>
        </details>
      )}
    </>
  );
}
