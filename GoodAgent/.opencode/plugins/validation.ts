import type { Plugin } from "@opencode-ai/plugin"

export const ValidationPlugin: Plugin = async (ctx) => {
  const { client } = ctx

  return {
    "tool.execute.after": async (input: any, output: any) => {
      if (input.tool !== "task") return

      const resultText = output.result
      if (!resultText || typeof resultText !== "string") return

      await client.app.log({
        body: {
          service: "goodagent-validation",
          level: "info",
          message: `Afterhook inspecting task completion for tool: ${input.tool}`,
        },
      })

      // 1. Checklist completion check
      // Parse output for checklist markers [x] vs [ ]
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

      // 3. Result completeness check
      // Detect empty results when input was non-empty
      if (hasNoFindings && resultText.length < 20) {
        await client.app.log({
          body: {
            service: "goodagent-validation",
            level: "info",
            message: "Subagent reports no findings (short output, likely legitimate)",
          },
        })
      }

      // Detect suspicious uniform severity
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
    },
  }
}
