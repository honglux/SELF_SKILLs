import type { Plugin } from "@opencode-ai/plugin"

export const ValidationPlugin: Plugin = async (ctx) => {
  const { client, $ } = ctx

  async function logToFile(sessionId: string, message: string) {
    const logPath = `output/${sessionId}/tmp/errors.log`
    const timestamp = new Date().toISOString().replace("T", " ").substring(0, 19)
    const line = `[${timestamp}] ${message}`
    try {
      await $`echo ${line} >> ${logPath}`.quiet()
    } catch {
      // 目录可能不存在，静默跳过
    }
  }

  async function validateJSONFile(filePath: string, sessionId: string): Promise<boolean> {
    try {
      const result = await $`python scripts/validate_json.py ${filePath}`.quiet()
      return result.exitCode === 0
    } catch {
      await logToFile(sessionId, `JSON_VALIDATE_ERROR file=${filePath} python_script_failed`)
      return false
    }
  }

  return {
    "tool.execute.after": async (input: any, output: any) => {
      if (input.tool !== "task") return

      const resultText = output.result
      if (!resultText || typeof resultText !== "string") return

      const taskDescription = input.args?.description || ""
      // 从 task description 中提取 session_id
      const sidMatch = taskDescription.match(/session[_-]?id[=:]\s*["']?([a-zA-Z0-9._-]+)/i)
        || resultText.match(/session[_-]?id["']?\s*:\s*["']([a-zA-Z0-9._-]+)/)
      const sessionId = sidMatch ? sidMatch[1] : "unknown"

      await logToFile(sessionId, `AFTERHOOK_START task=${taskDescription.substring(0, 60)}`)

      // 1. Checklist completion check — scan ALL agent checklists
      const checklistPattern = /output\/[a-zA-Z0-9._-]+\/tmp\/checklist_[a-z-]+\.md/g
      const checklistFiles = resultText.match(checklistPattern) || []
      // Also check known paths
      const knownChecklists = [
        `output/${sessionId}/tmp/checklist_sentinel.md`,
        `output/${sessionId}/tmp/checklist_hardcoded-secret.md`,
        `output/${sessionId}/tmp/checklist_json-validator.md`,
      ]
      for (const clPath of [...new Set([...checklistFiles, ...knownChecklists])]) {
        try {
          const readResult = await $`cat ${clPath}`.quiet()
          const clContent = readResult.stdout?.toString() || ""
          const unchecked = (clContent.match(/\[ \]/g) || []).length
          if (unchecked > 0) {
            await logToFile(sessionId, `CHECKLIST_INCOMPLETE file=${clPath} unchecked=${unchecked}`)
          } else {
            await logToFile(sessionId, `CHECKLIST_COMPLETE file=${clPath}`)
          }
        } catch {
          // checklist file may not exist yet — agent hasn't created it
        }
      }

      // 2. Output format validation
      const hasTableStructure = resultText.includes("|") && resultText.includes("行号")
      const hasNoFindings = resultText.includes("未发现") || resultText.includes("无硬编码")
      const hasValidOutput = hasTableStructure || hasNoFindings

      if (!hasValidOutput) {
        await logToFile(sessionId, `FORMAT_INVALID missing_table_or_declaration`)
      }

      // 3. Result completeness — uniform severity check
      const severityCounts = {
        high: (resultText.match(/❌高风险/g) || []).length,
        medium: (resultText.match(/⚠️中风险/g) || []).length,
        low: (resultText.match(/📝低风险/g) || []).length,
        info: (resultText.match(/🔍疑似误报/g) || []).length,
      }
      const totalFindings = severityCounts.high + severityCounts.medium + severityCounts.low + severityCounts.info
      const maxSeverity = Math.max(severityCounts.high, severityCounts.medium, severityCounts.low, severityCounts.info)

      if (totalFindings > 2 && maxSeverity === totalFindings) {
        await logToFile(sessionId, `UNIFORM_SEVERITY total=${totalFindings} all_same_level`)
      }

      await logToFile(sessionId, `AFTERHOOK_SUMMARY total_findings=${totalFindings} h=${severityCounts.high} m=${severityCounts.medium} l=${severityCounts.low} i=${severityCounts.info} format_ok=${hasValidOutput}`)

      // 4. JSON file validation via Python script (FR-015)
      const jsonFileMatch = resultText.match(/output\/[a-zA-Z0-9._-]+\/(?:tmp\/[a-z-]+\.json|alerts\.json)/g)
      if (jsonFileMatch) {
        for (const filePath of jsonFileMatch) {
          const valid = await validateJSONFile(filePath, sessionId)
          await logToFile(sessionId, `JSON_VALIDATE file=${filePath} valid=${valid}`)

          // FR-014: If invalid, dispatch json-validator subagent
          if (!valid) {
            await logToFile(sessionId, `JSON_VALIDATOR_DISPATCH file=${filePath}`)
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
              await logToFile(sessionId, `JSON_VALIDATOR_DISPATCH_FAILED error=${err}`)
            }
          }
        }
      }

      await logToFile(sessionId, `AFTERHOOK_END`)
    },
  }
}
