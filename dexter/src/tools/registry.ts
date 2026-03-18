import { StructuredToolInterface } from '@langchain/core/tools';
import { createFinancialSearch, createFinancialMetrics, createReadFilings } from './finance/index.js';
import { exaSearch, perplexitySearch, tavilySearch } from './search/index.js';
import { skillTool, SKILL_TOOL_DESCRIPTION } from './skill.js';
import { webFetchTool } from './fetch/index.js';
import { browserTool } from './browser/index.js';
import { readFileTool, writeFileTool, editFileTool } from './filesystem/index.js';
import { stockAdvisoryTool } from './advisory/index.js';
import {
  getVnstockHealth,
  getVnstockPrice,
  getVnstockHistory,
  getVnstockPriceBoard,
  getVnstockComprehensiveReport,
  getVnstockIndex,
  getVnstockGold,
  getVnstockScreener,
} from './vnstock/index.js';
import { FINANCIAL_SEARCH_DESCRIPTION, FINANCIAL_METRICS_DESCRIPTION, WEB_SEARCH_DESCRIPTION, WEB_FETCH_DESCRIPTION, READ_FILINGS_DESCRIPTION, BROWSER_DESCRIPTION, READ_FILE_DESCRIPTION, WRITE_FILE_DESCRIPTION, EDIT_FILE_DESCRIPTION, STOCK_ADVISORY_DESCRIPTION } from './descriptions/index.js';
import {
  VNSTOCK_HEALTH_DESCRIPTION,
  VNSTOCK_PRICE_DESCRIPTION,
  VNSTOCK_HISTORY_DESCRIPTION,
  VNSTOCK_PRICE_BOARD_DESCRIPTION,
} from './descriptions/index.js';
import {
  VNSTOCK_COMPREHENSIVE_DESCRIPTION,
} from './descriptions/index.js';
import {
  VNSTOCK_INDEX_DESCRIPTION,
  VNSTOCK_GOLD_DESCRIPTION,
  VNSTOCK_SCREENER_DESCRIPTION,
} from './descriptions/index.js';
import { discoverSkills } from '../skills/index.js';

/**
 * A registered tool with its rich description for system prompt injection.
 */
export interface RegisteredTool {
  /** Tool name (must match the tool's name property) */
  name: string;
  /** The actual tool instance */
  tool: StructuredToolInterface;
  /** Rich description for system prompt (includes when to use, when not to use, etc.) */
  description: string;
}

/**
 * Get all registered tools with their descriptions.
 * Conditionally includes tools based on environment configuration.
 *
 * @param model - The model name (needed for tools that require model-specific configuration)
 * @returns Array of registered tools
 */
export function getToolRegistry(model: string): RegisteredTool[] {
  const tools: RegisteredTool[] = [];
  
  // Skip meta-tools (financial_search, financial_metrics, read_filings) for Ollama
  // These tools use LLM internally and can cause issues with local models
  const isOllama = model.startsWith('ollama:');
  
  if (!isOllama) {
    tools.push(
      {
        name: 'financial_search',
        tool: createFinancialSearch(model),
        description: FINANCIAL_SEARCH_DESCRIPTION,
      },
      {
        name: 'financial_metrics',
        tool: createFinancialMetrics(model),
        description: FINANCIAL_METRICS_DESCRIPTION,
      },
      {
        name: 'read_filings',
        tool: createReadFilings(model),
        description: READ_FILINGS_DESCRIPTION,
      }
    );
  }
  
  // Core tools (always available)
  tools.push(
    {
      name: 'web_fetch',
      tool: webFetchTool,
      description: WEB_FETCH_DESCRIPTION,
    },
    {
      name: 'browser',
      tool: browserTool,
      description: BROWSER_DESCRIPTION,
    },
    {
      name: 'read_file',
      tool: readFileTool,
      description: READ_FILE_DESCRIPTION,
    },
    {
      name: 'write_file',
      tool: writeFileTool,
      description: WRITE_FILE_DESCRIPTION,
    },
    {
      name: 'edit_file',
      tool: editFileTool,
      description: EDIT_FILE_DESCRIPTION,
    },
    {
      name: 'stock_advisory',
      tool: stockAdvisoryTool,
      description: STOCK_ADVISORY_DESCRIPTION,
    },
    // Vietnamese Stock Market Tools
    {
      name: 'get_vnstock_health',
      tool: getVnstockHealth,
      description: VNSTOCK_HEALTH_DESCRIPTION,
    },
    {
      name: 'get_vnstock_price',
      tool: getVnstockPrice,
      description: VNSTOCK_PRICE_DESCRIPTION,
    },
    {
      name: 'get_vnstock_history',
      tool: getVnstockHistory,
      description: VNSTOCK_HISTORY_DESCRIPTION,
    },
    {
      name: 'get_vnstock_price_board',
      tool: getVnstockPriceBoard,
      description: VNSTOCK_PRICE_BOARD_DESCRIPTION,
    },
    {
      name: 'get_vnstock_comprehensive_report',
      tool: getVnstockComprehensiveReport,
      description: VNSTOCK_COMPREHENSIVE_DESCRIPTION,
    },
    {
      name: 'get_vnstock_index',
      tool: getVnstockIndex,
      description: VNSTOCK_INDEX_DESCRIPTION,
    },
    {
      name: 'get_vnstock_gold',
      tool: getVnstockGold,
      description: VNSTOCK_GOLD_DESCRIPTION,
    },
    {
      name: 'get_vnstock_screener',
      tool: getVnstockScreener,
      description: VNSTOCK_SCREENER_DESCRIPTION,
    }
  );

  // Include web_search if Exa, Perplexity, or Tavily API key is configured (Exa → Perplexity → Tavily)
  if (process.env.EXASEARCH_API_KEY) {
    tools.push({
      name: 'web_search',
      tool: exaSearch,
      description: WEB_SEARCH_DESCRIPTION,
    });
  } else if (process.env.PERPLEXITY_API_KEY) {
    tools.push({
      name: 'web_search',
      tool: perplexitySearch,
      description: WEB_SEARCH_DESCRIPTION,
    });
  } else if (process.env.TAVILY_API_KEY) {
    tools.push({
      name: 'web_search',
      tool: tavilySearch,
      description: WEB_SEARCH_DESCRIPTION,
    });
  }

  // Include skill tool if any skills are available
  const availableSkills = discoverSkills();
  if (availableSkills.length > 0) {
    tools.push({
      name: 'skill',
      tool: skillTool,
      description: SKILL_TOOL_DESCRIPTION,
    });
  }

  return tools;
}

/**
 * Get just the tool instances for binding to the LLM.
 *
 * @param model - The model name
 * @returns Array of tool instances
 */
export function getTools(model: string): StructuredToolInterface[] {
  return getToolRegistry(model).map((t) => t.tool);
}

/**
 * Build the tool descriptions section for the system prompt.
 * Formats each tool's rich description with a header.
 *
 * @param model - The model name
 * @returns Formatted string with all tool descriptions
 */
export function buildToolDescriptions(model: string): string {
  return getToolRegistry(model)
    .map((t) => `### ${t.name}\n\n${t.description}`)
    .join('\n\n');
}
