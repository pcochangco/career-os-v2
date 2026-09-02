# CareerOS release checklist

Use this checklist for web, API, and native beta releases. A release is not complete until the live health and core-flow checks pass.

## Before merging

- Confirm the change is based on the current `main` head and contains no unrelated workspace files.
- Run backend formatting, lint, and the full test suite.
- Run the frontend TypeScript check and production web export.
- Confirm Alembic has one head and test `alembic upgrade head` against a disposable database.
- Review new environment variables and keep secrets out of source, logs, screenshots, and Expo public configuration.
- For a schema change, confirm cascade behavior, index impact, deployment ordering, and rollback limits.

## Privacy and authentication

- Verify the public preview creates no user and stores no typed goal.
- Verify Apple or Google sign-in creates a saved account before the first goal write.
- Verify returning sign-in restores only the saved user and never merges browser-local data.
- Verify linking a second provider keeps the current user ID and data.
- Verify sign-out revokes the previous session.
- Verify account deletion removes the user-owned data and invalidates access.
- Keep provider identity tokens out of the database and application logs.
- Publish a real `EXPO_PUBLIC_SUPPORT_EMAIL` before public beta.
- Recheck `/privacy`, `/terms`, `/account-deletion`, `/support`, and the signed-in `/report-issue` flow in both themes and on a narrow mobile viewport.
- Update the Apple privacy disclosure and Google Play Data safety form whenever data practices or SDKs change.

## Deployment

- Confirm a recent database backup or recoverable snapshot exists before a destructive migration.
- Deploy the exact reviewed Git commit without force-updating `main`.
- Watch the migration and startup logs through the service swap.
- Require repeated `200 OK` responses from `/api/v1/health`.
- Confirm response security headers and a unique `X-Request-ID` on production.
- Scan post-startup logs for tracebacks, migration errors, secret values, user content, and repeated `5xx` responses.

## Live smoke test

- Open CareerOS signed out and inspect the example path.
- Type a goal, sign in, confirm it is created once, and reject one invalid goal.
- Complete an adaptively sized three-to-six-question discovery, generate a roadmap, accept it, save one learning record, and mark one step complete.
- Dismiss one current-step resource, use Undo, and confirm the same resource returns.
- Refresh and confirm the app resumes the same state without duplicate goals or roadmaps.
- Open Settings, change appearance, and confirm all legal/support links work.
- Submit one issue report and retain its `CAR-` reference without placing private goal content in the report.
- Delete the test account and confirm the old session returns `401`.

## Rollback

- Record the previous live deploy and database revision before release.
- Roll application code back only when the previous version is compatible with the migrated schema.
- Prefer a forward fix for irreversible or data-bearing migrations; never downgrade blindly.
- After rollback or forward fix, rerun health checks, inspect logs, and repeat the affected smoke-test path.
