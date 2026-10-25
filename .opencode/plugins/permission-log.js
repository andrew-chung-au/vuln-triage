// Logs every OpenCode permission prompt (and its reply) as one JSON line to
// .agent-logs/permission-prompts.jsonl (git-ignored; not .scratch/, which
// `make clean-scratch` empties), so
// `make permission-report` can count real prompts instead of what agents
// remembered to list. Append-only: it never blocks or changes a permission.
// VERIFY: the payload of permission.asked / permission.replied is not
// documented, so the raw event is written as received.
import { appendFileSync, mkdirSync } from "node:fs"
import { join } from "node:path"

export const PermissionLog = async ({ client, directory }) => {
  const dir = join(directory, ".agent-logs")
  const file = join(dir, "permission-prompts.jsonl")

  return {
    event: async ({ event }) => {
      if (event.type !== "permission.asked" && event.type !== "permission.replied") return
      const line = JSON.stringify({ at: new Date().toISOString(), type: event.type, properties: event.properties })
      try {
        mkdirSync(dir, { recursive: true })
        appendFileSync(file, line + "\n")
      } catch (err) {
        await client.app.log({
          body: { service: "permission-log", level: "warn", message: "could not write " + file, extra: { error: String(err) } },
        })
      }
    },
  }
}
