export const VNSTOCK_COMPREHENSIVE_DESCRIPTION = `
Comprehensive financial report for a Vietnamese company. This tool aggregates all fundamental data into a single response, including:
1. Company Profile (industry, overview)
2. Financial Ratios (P/E, ROE, ROA, Margins)
3. Balance Sheet (Assets, Liabilities, Equity)
4. Income Statement (Revenue, Profit)

## When to Use

- User asks for fundamental analysis, evaluation, or deep dive of a company (e.g., "Đánh giá tài chính HPG", "Tình hình kinh doanh FPT thế nào?").
- You need multiple financial metrics to understand the financial health of a company.
- User explicitly asks for income statements, balance sheets, or financial ratios.

## When NOT to Use

- **DO NOT USE FOR SIMPLE PRICE QUERIES**. If the user just asks "Giá FPT hôm nay?" or "Thị trường thế nào?", use \`get_vnstock_price\` or \`get_vnstock_price_board\` instead.
- This tool is slow and heavy, DO NOT use it unless deep financial analysis is explicitly or implicitly requested.

## Usage Notes

- Returns data for the last 4 periods by default.
- Contains massive amounts of multi-dimensional financial data in a single JSON.
- Synthesize the most relevant numbers (e.g., revenue growth, profit margins, ROE) rather than dumping all fields.
`.trim();
