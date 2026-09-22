export type UpdateJob = {
  id?: string;
  action?: string;
  state?: string;
  progress?: number;
  message?: string;
  error?: string;
  target_version?: string;
  target_revision?: string;
  rollback_ok?: boolean;
  log_tail?: string[];
};


export type UpdateInfo = {
  version: string;
  revision: string;
  revision_short: string;
  branch: string;
  dirty: boolean;
  relation: string;
  available: boolean;
  enabled: boolean;
  can_install: boolean;
  branch_ok: boolean;
  rootless_ready: boolean;
  running_as: string;
  updater_user: string;
  worker_available: boolean;
  message: string;
  changelog: string;
  installed_changelog: string;
  system_migration_required: boolean;
  job: UpdateJob | null;

  channel: {
    name: string;
    remote: string;
    revision: string;
    revision_short: string;
    version: string;
  };

  permissions: {
    application: boolean;
    git: boolean;
    update_data: boolean;
    frontend: boolean;
  };
};
