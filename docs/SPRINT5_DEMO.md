# Sprint 5 local demonstration

Sprint 5 is merged into `main` through feature PRs #6–#10. This launcher demonstrates the completed sprint locally; it is not a public production deployment.

On the prepared Mac, open `scripts/sprint5_demo.command`. It installs missing local dependencies on first run, resets a dedicated demo database under `~/.cache/qoldau-sprint5-demo`, starts the API and frontend, and opens the login page. Leave its Terminal window open while presenting; Control-C stops both servers.

Demo login details are in `README.md`. The data and accounts are generated examples. Use these five steps:

1. Admin: Configuration → switch RU, then KZ → Urgency keywords → Add (cancel without changing a rule).
2. Student: submit a request, open its timeline, send a message.
3. Agent: open a routed request, start work, reply.
4. Admin: export analytics and download the report.
5. GitHub: show the Sprint 5 project board and green checks on PRs #6–#10.

The browser suite automates the same connected journeys. Keep `presentations/Qoldau_Sprint5_Review.pdf` available as a fallback if the local server is unavailable during the talk.
