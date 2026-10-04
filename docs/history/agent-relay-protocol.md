# Agent relay

A mailbox between the Mac agent (Claude Code, elisa-proof main checkout) and the
Windows agent (Claude Code / Codex in WSL). This branch holds messages only; it never
merges into `main`.

## Protocol
- Mac -> Windows: `to-windows/NNNN-slug.md`. Windows -> Mac: `to-mac/NNNN-slug.md`.
  NNNN increases per direction; never edit another agent's message.
- Each message starts with `From:`, `Date:`, `Kind:` (task | result | question | ack),
  `Re:` (the message it answers, if any), then the body.
- To claim a task, commit `to-mac/NNNN-ack.md` with `Re:` set to that task. Then do it.
- When a message is handled, `git mv` it into `done/` in the same commit as the reply.
- Results that are large (census output, logs) go in the message body if they are under
  about 200 lines; otherwise attach a file next to the message, `NNNN-slug.log`.
- Work products (code) go on their own branch, `win/<slug>`, pushed to origin. Never push
  to `main`, never amend, never force-push this branch.
- Check for mail: `git fetch origin agent-relay && git log HEAD..origin/agent-relay --stat`,
  then `git pull --rebase` before writing. Poll every 10-20 minutes while idle.

## Rules the Windows agent inherits
Proof code stays in Elisa; Python/shell only orchestrate. Files <= 600 lines. Every
capability gets positive, adversarial, malformed and budget tests. Do not modify the
compiler repository. Commit messages end with a Co-Authored-By line.
