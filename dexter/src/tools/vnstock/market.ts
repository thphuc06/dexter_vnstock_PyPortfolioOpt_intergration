import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { callVnstockApi } from './api.js';
import { formatToolResult } from '../types.js';

export const getVnstockIndex = new DynamicStructuredTool({
  name: 'get_vnstock_index',
  description:
    'Get current values and data for Vietnamese market indices (VN-Index, HNX-Index, UPCOM-Index)',
  schema: z.object({}),
  func: async () => {
    try {
      const { data, url } = await callVnstockApi('/index', {});
      return formatToolResult(data, [url]);
    } catch (error) {
      throw new Error(
        `Failed to fetch market indices: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  },
});

export const getVnstockGold = new DynamicStructuredTool({
  name: 'get_vnstock_gold',
  description:
    'Get current gold prices in Vietnam (SJC gold, PNJ gold, etc.). Useful when users ask about gold prices or precious metals in Vietnam',
  schema: z.object({}),
  func: async () => {
    try {
      const { data, url } = await callVnstockApi('/gold', {});
      return formatToolResult(data, [url]);
    } catch (error) {
      throw new Error(
        `Failed to fetch gold prices: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  },
});

export const getVnstockScreener = new DynamicStructuredTool({
  name: 'get_vnstock_screener',
  description:
    'Screen and filter Vietnamese stocks by exchange. Returns a list of stocks with key metrics. Useful for finding stocks on specific exchanges or getting market overview',
  schema: z.object({
    exchange: z
      .enum(['HOSE', 'HNX', 'UPCOM'])
      .default('HOSE')
      .describe(
        "Stock exchange: 'HOSE' (Ho Chi Minh Stock Exchange - largest), 'HNX' (Hanoi Stock Exchange), or 'UPCOM' (Unlisted Public Company Market)"
      ),
    limit: z
      .number()
      .default(20)
      .describe(
        'Maximum number of stocks to return (default: 20). Use higher values for comprehensive market scans'
      ),
  }),
  func: async (input) => {
    try {
      const { data, url } = await callVnstockApi('/screener', {
        exchange: input.exchange,
        limit: input.limit,
      });
      return formatToolResult(data, [url]);
    } catch (error) {
      throw new Error(
        `Failed to screen stocks on ${input.exchange}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  },
});
