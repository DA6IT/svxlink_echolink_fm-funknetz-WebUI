import {
  useMemo,
} from 'react';


type Props = {
  value: string;
};


export default function UpdateChangelog({
  value,
}: Props) {
  const lines =
    useMemo(
      () =>
        value
          .split('\n')
          .filter(
            line =>
              line.trim().length > 0
          ),
      [value]
    );

  return (
    <div className="update-changelog-body">
      {lines.map(
        (line, index) => {
          if (
            line.startsWith(
              '### '
            )
          ) {
            return (
              <h4 key={index}>
                {line.slice(4)}
              </h4>
            );
          }

          if (
            line.startsWith(
              '## '
            )
          ) {
            return (
              <h3 key={index}>
                {line.slice(3)}
              </h3>
            );
          }

          if (
            line.startsWith(
              '# '
            )
          ) {
            return (
              <h3 key={index}>
                {line.slice(2)}
              </h3>
            );
          }

          if (
            line.startsWith(
              '- '
            )
          ) {
            return (
              <div
                className="update-changelog-item"
                key={index}
              >
                <span>•</span>

                <p>
                  {line.slice(2)}
                </p>
              </div>
            );
          }

          return (
            <p key={index}>
              {line}
            </p>
          );
        }
      )}
    </div>
  );
}
