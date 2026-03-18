import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { callVnstockApi } from './api.js';
import { formatToolResult } from '../types.js';

export const getVnstockComprehensiveReport = new DynamicStructuredTool({
  name: 'get_vnstock_comprehensive_report',
  description:
    'Get comprehensive financial report for a Vietnamese company including company profile, financial ratios, balance sheet, and income statement. USE ONLY for fundamental analysis or evaluation.',
  schema: z.object({
    ticker: z
      .string()
      .describe(
        "Vietnamese stock ticker symbol (e.g., 'FPT', 'VCB', 'HPG')"
      ),
    limit: z
      .number()
      .optional()
      .default(4)
      .describe(
        "Number of periods to return for financial statements (default: 4)"
      ),
  }),
  func: async (input) => {
    try {
      const { data, url } = await callVnstockApi(
        `/comprehensive_report/${input.ticker}`,
        { limit: input.limit !== undefined ? input.limit : 4 },
        { cacheable: true } // Comprehensive report can be cached
      );
      return formatToolResult(data, [url]);
    } catch (error) {
      throw new Error(
        `Failed to fetch comprehensive report for ${input.ticker}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  },
});
