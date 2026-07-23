import type { Plugin } from "@opencode-ai/plugin"

export const ValidationPlugin: Plugin = async (ctx) => {
  const { client, $ } = ctx

  async function validateJSONFile(filePath: string): Promise<boolean> {
    try {
      const result = await $`python scripts/validate_json.py ${filePath}`.quiet()
      return result.exitCode === 0
    } catch {
      return false
    }
  }

  return {
    "tool.execute.after": async (input: any, output: any) => {
      if (input.tool !== "task") return

      const resultText = output.result
      if (!resultText || typeof resultText !== "string") return

      const taskDescription = input.args?.description || ""

      await client.app.log({
        body: {
          service: "goodagent-validation",
          level: "info",
          message: `Afterhook inspecting task: ${taskDescription.substring(0, 80)}`,
        },
      })

      // 1. Checklist completion check
      const uncheckedItems = (resultText.match(/\[ \]/g) || []).length
      if (uncheckedItems > 0) {
        await client.app.log({
          body: {
            service: "goodagent-validation",
            level: "warn",
            message: `Checklist incomplete: ${uncheckedItems} items remain unchecked`,
            extra: { unchecked_count: uncheckedItems },
          },
        })
      }

      // 2. Output format validation
      const hasTableStructure = resultText.includes("|") && resultText.includes("行号")
      const hasNoFindings = resultText.includes("未发现") || resultText.includes("无硬编码")
      const hasValidOutput = hasTableStructure || hasNoFindings

      if (!hasValidOutput) {
        await client.app.log({
          body: {
            service: "goodagent-validation",
            level: "warn",
            message: "Subagent output missing expected table format or 'no findings' declaration",
          },
        })
      }

      // 3. Result completeness check — detect suspicious uniform severity
      const severityCounts = {
        high: (resultText.match(/❌高风险/g) || []).length,
        medium: (resultText.match(/⚠️中风险/g) || []).length,
        low: (resultText.match(/📝低风险/g) || []).length,
        info: (resultText.match(/🔍疑似误报/g) || []).length,
      }
      const totalFindings = severityCounts.high + severityCounts.medium + severityCounts.low + severityCounts.info
      const maxSeverity = Math.max(severityCounts.high, severityCounts.medium, severityCounts.low, severityCounts.info)

      if (totalFindings > 2 && maxSeverity === totalFindings) {
        await client.app.log({
          body: {
            service: "goodagent-validation",
            level: "warn",
            message: `All ${totalFindings} findings marked with same severity — possible incomplete classification`,
            extra: severityCounts,
          },
        })
      }

      // 4. JSON file validation via Python script (FR-015 bypass)
      const jsonFileMatch = resultText.match(/output\/[a-zA-Z0-9._-]+\/(?:tmp\/[a-z-]+\.json|alerts\.json)/g)
      if (jsonFileMatch) {
        for (const filePath of jsonFileMatch) {
          const valid = await validateJSONFile(filePath)
          await client.app.log({
            body: {
              service: "goodagent-validation",
              level: valid ? "info" : "error",
              message: valid
                ? `JSON file validated: ${filePath}`
                : `JSON file INVALID: ${filePath} — dispatching json-validator for repair`,
              extra: { file: filePath, valid },
            },
          })

          // FR-014: If invalid, dispatch json-validator subagent for auto-repair
          if (!valid) {
            try {
              await client.session.prompt({
                path: { id: input.sessionID },
                body: {
                  noReply: true,
                  parts: [{
                    type: "text",
                    text: `@json-validator 请校验并修复以下 JSON 文件：${filePath}`,
                  }],
                },
              })
            } catch (err) {
              await client.app.log({
                body: {
                  service: "goodagent-validation",
                  level: "error",
                  message: `Failed to dispatch json-validator: ${err}`,
                },
              })
            }
          }
        }
      }
    },
  }
}
