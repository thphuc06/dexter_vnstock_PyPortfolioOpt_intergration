"""
FastAPI Service cho Vietnamese Stock Market Data
Sử dụng thư viện vnstock để phục vụ AI Agent phân tích chứng khoán
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Any
import uvicorn
import pandas as pd
from vnstock import Vnstock
from datetime import datetime, timedelta
import time
import asyncio

# ---------------------------------------------------------------------------
# Simple TTL in-memory cache
# Prevents redundant external API calls when the agent calls the same
# endpoint multiple times within a single /ask request cycle.
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, Any]] = {}  # key → (expires_at, value)
DEFAULT_CACHE_TTL = 60  # seconds


def _cache_get(key: str) -> Any | None:
    entry = _CACHE.get(key)
    if entry and time.monotonic() < entry[0]:
        return entry[1]
    return None


def _cache_set(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> None:
    _CACHE[key] = (time.monotonic() + ttl, value)

app = FastAPI(
    title="VNStock API Service",
    description="API service for Vietnamese Stock Market data powered by vnstock",
    version="1.0.0"
)

# CORS middleware để cho phép Dexter (TypeScript) gọi được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origins, có thể giới hạn theo nhu cầu
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_vnstock_instance(ticker: str):
    """Tạo instance của Vnstock cho một mã cổ phiếu"""
    try:
        return Vnstock().stock(symbol=ticker.upper(), source='VCI')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi khởi tạo vnstock cho mã {ticker}: {str(e)}")


def get_company_dataframe(stock):
    """
    Try multiple company methods to stay compatible across vnstock versions/sources.
    Returns tuple: (dataframe, method_used).
    """
    company = getattr(stock, "company", None)
    if company is None:
        raise ValueError("Company data component is unavailable for this symbol")

    method_errors: List[str] = []
    for method_name in ("profile", "overview"):
        method = getattr(company, method_name, None)
        if not callable(method):
            method_errors.append(f"{method_name}:not_available")
            continue

        try:
            data = method()
            if data is not None and not data.empty:
                return data, method_name
            method_errors.append(f"{method_name}:empty")
        except Exception as e:
            method_errors.append(f"{method_name}:{str(e)}")

    raise ValueError("Không lấy được thông tin công ty (" + "; ".join(method_errors) + ")")


def get_company_dataframe_with_source_fallback(ticker: str):
    """
    Company endpoint fallback across providers because provider capabilities
    differ by vnstock version.
    Returns tuple: (dataframe, method_used, source_used).
    """
    source_errors: List[str] = []
    for source in ("VCI", "KBS"):
        try:
            stock = Vnstock().stock(symbol=ticker.upper(), source=source)
            data, method_used = get_company_dataframe(stock)
            return data, method_used, source
        except Exception as e:
            source_errors.append(f"{source}:{str(e)}")

    raise ValueError("Không lấy được thông tin công ty từ các nguồn (" + "; ".join(source_errors) + ")")


@app.get("/health")
async def health_check():
    """Endpoint kiểm tra service còn hoạt động không"""
    return {
        "status": "healthy",
        "service": "vnstock-api",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/price/{ticker}")
async def get_realtime_price(ticker: str):
    """
    Lấy giá intraday realtime của 1 mã cổ phiếu

    Params:
        ticker: Mã cổ phiếu (VD: VCB, ACB, HPG)

    Returns:
        Dữ liệu giá realtime trong ngày
    """
    cache_key = f"price:{ticker.upper()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        stock = get_vnstock_instance(ticker)
        data = stock.quote.intraday()

        if data is None or data.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu cho mã {ticker}")

        response = {
            "ticker": ticker.upper(),
            "data": data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat()
        }
        _cache_set(cache_key, response)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy giá realtime: {str(e)}")


@app.get("/history/{ticker}")
async def get_price_history(
    ticker: str,
    start: str = Query(..., description="Ngày bắt đầu (YYYY-MM-DD)"),
    end: str = Query(..., description="Ngày kết thúc (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, description="Giới hạn số dòng trả về (mặc định: tất cả). Dùng để tiết kiệm token")
):
    """
    Lấy lịch sử giá của mã cổ phiếu
    
    Params:
        ticker: Mã cổ phiếu
        start: Ngày bắt đầu (format: YYYY-MM-DD)
        end: Ngày kết thúc (format: YYYY-MM-DD)
        limit: Giới hạn số dòng trả về (mặc định: tất cả)
    
    Returns:
        Lịch sử giá theo khoảng thời gian
    """
    try:
        # Validate date format
        try:
            datetime.strptime(start, '%Y-%m-%d')
            datetime.strptime(end, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD")
        
        stock = get_vnstock_instance(ticker)
        data = stock.quote.history(start=start, end=end)
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu lịch sử cho mã {ticker}")
        
        # Apply limit if specified (take most recent rows)
        if limit and limit > 0:
            data = data.tail(limit)
        
        return {
            "ticker": ticker.upper(),
            "start_date": start,
            "end_date": end,
            "data": data.to_dict(orient='records'),
            "count": len(data),
            "limited": limit is not None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy lịch sử giá: {str(e)}")


@app.get("/financials/{ticker}")
async def get_financial_ratios(ticker: str, limit: int = Query(4, description="Giới hạn số kỳ trả về (mặc định: 4 kỳ gần nhất)")):
    """
    Lấy các chỉ số tài chính của công ty (P/E, ROE, EPS, ROA...)
    
    Params:
        ticker: Mã cổ phiếu
        limit: Số kỳ báo cáo trả về (mặc định: 4)
    
    Returns:
        Các chỉ số tài chính quan trọng
    """
    try:
        print(f"[INFO] Fetching financials for {ticker}...")
        stock = get_vnstock_instance(ticker)
        print(f"[INFO] Created vnstock instance for {ticker}")
        
        data = stock.finance.ratio()
        print(f"[INFO] Got ratio data for {ticker}: {len(data) if data is not None else 0} rows")
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu tài chính cho mã {ticker}")
        
        # Fix multi-level columns by flattening them
        if isinstance(data.columns, pd.MultiIndex):
            # Flatten multi-level columns: ('Meta', 'ticker') -> 'Meta_ticker'
            data.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in data.columns.values]
        
        # Apply limit (take most recent periods)
        if limit and limit > 0:
            data = data.head(limit)
        
        result = {
            "ticker": ticker.upper(),
            "data": data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat(),
            "periods_returned": len(data)
        }
        print(f"[SUCCESS] Returning {len(result['data'])} financial records for {ticker}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Lỗi khi lấy chỉ số tài chính: {str(e)}"
        print(f"[ERROR] {error_detail}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/balance_sheet/{ticker}")
async def get_balance_sheet(ticker: str, limit: int = Query(4, description="Giới hạn số kỳ trả về (mặc định: 4)")):
    """
    Lấy bảng cân đối kế toán của công ty
    
    Params:
        ticker: Mã cổ phiếu
        limit: Số kỳ báo cáo trả về (mặc định: 4)
    
    Returns:
        Dữ liệu bảng cân đối kế toán
    """
    try:
        stock = get_vnstock_instance(ticker)
        data = stock.finance.balance_sheet()
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bảng cân đối kế toán cho mã {ticker}")
        
        # Fix multi-level columns by flattening them
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in data.columns.values]
        
        # Apply limit (take most recent periods)
        if limit and limit > 0:
            data = data.head(limit)
        
        return {
            "ticker": ticker.upper(),
            "data": data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat(),
            "periods_returned": len(data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy bảng cân đối kế toán: {str(e)}")


@app.get("/income_statement/{ticker}")
async def get_income_statement(ticker: str, limit: int = Query(4, description="Giới hạn số kỳ trả về (mặc định: 4)")):
    """
    Lấy báo cáo kết quả kinh doanh của công ty
    
    Params:
        ticker: Mã cổ phiếu
        limit: Số kỳ báo cáo trả về (mặc định: 4)
    
    Returns:
        Dữ liệu kết quả kinh doanh
    """
    try:
        stock = get_vnstock_instance(ticker)
        data = stock.finance.income_statement()
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy kết quả kinh doanh cho mã {ticker}")
        
        # Fix multi-level columns by flattening them
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in data.columns.values]
        
        # Apply limit (take most recent periods)
        if limit and limit > 0:
            data = data.head(limit)
        
        return {
            "ticker": ticker.upper(),
            "data": data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat(),
            "periods_returned": len(data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy kết quả kinh doanh: {str(e)}")


@app.get("/board")
async def get_price_board(tickers: str = Query(..., description="Danh sách mã cổ phiếu, cách nhau bởi dấu phẩy (VD: VCB,ACB,TCB)")):
    """
    Lấy bảng giá của nhiều mã cổ phiếu cùng lúc

    Params:
        tickers: Danh sách mã cổ phiếu, cách nhau bởi dấu phẩy (VD: VCB,ACB,TCB)

    Returns:
        Bảng giá tổng hợp của các mã
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(',')]
        ticker_list = sorted(set(ticker_list))  # normalize for cache key

        if not ticker_list:
            raise HTTPException(status_code=400, detail="Vui lòng cung cấp ít nhất 1 mã cổ phiếu")

        cache_key = f"board:{','.join(ticker_list)}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        results = []
        errors = []

        for ticker in ticker_list:
            try:
                stock = Vnstock().stock(symbol=ticker, source='VCI')
                quote_data = stock.quote.intraday()

                if quote_data is not None and not quote_data.empty:
                    latest = quote_data.iloc[-1].to_dict()
                    latest['ticker'] = ticker
                    results.append(latest)
                else:
                    errors.append({"ticker": ticker, "error": "Không có dữ liệu"})
            except Exception as e:
                errors.append({"ticker": ticker, "error": str(e)})

        response = {
            "requested_tickers": ticker_list,
            "data": results,
            "errors": errors if errors else None,
            "timestamp": datetime.now().isoformat()
        }
        _cache_set(cache_key, response)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy bảng giá: {str(e)}")


@app.get("/company/{ticker}")
async def get_company_info(ticker: str):
    """
    Lấy thông tin tổng quan về công ty
    
    Params:
        ticker: Mã cổ phiếu
    
    Returns:
        Thông tin tổng quan công ty (ngành nghề, giới thiệu, ...)
    """
    try:
        data, method_used, source_used = get_company_dataframe_with_source_fallback(ticker)
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy thông tin công ty cho mã {ticker}")
        
        return {
            "ticker": ticker.upper(),
            "source_provider": source_used,
            "source_method": method_used,
            "data": data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin công ty: {str(e)}")


@app.get("/index")
async def get_market_indices():
    """
    Lấy thông tin các chỉ số thị trường: VN-Index, HNX-Index, UPCOM

    Returns:
        Dữ liệu các chỉ số thị trường hiện tại
    """
    cached = _cache_get("index")
    if cached is not None:
        return cached

    try:
        vnstock = Vnstock()

        results = {}

        # Lấy thông tin overview của thị trường
        # Dùng trading.price_board hoặc lấy từ một stock bất kỳ
        try:
            # Thử lấy market overview từ stock data
            stock = vnstock.stock(symbol='VCB', source='VCI')

            # Lấy giá lịch sử gần đây nhất để có context về market
            # Hoặc có thể dùng quote để lấy market info
            market_data = stock.quote.history(
                start=(datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                end=datetime.now().strftime('%Y-%m-%d')
            )

            # Trả về thông tin đơn giản hóa
            results = {
                "message": "Market indices data retrieval from vnstock library has limitations",
                "note": "For real-time VN-Index data, consider using alternative APIs or web scraping",
                "alternative": "You can get individual stock prices which reflect market movements",
                "sample_stock": "VCB" if market_data is not None and not market_data.empty else None,
                "market_open": True,  # Simplified - could check trading hours
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            results = {
                "error": "Unable to fetch market indices",
                "detail": str(e),
                "note": "VNINDEX/HNXINDEX data may require different data source"
            }

        response = {
            "indices": results,
            "timestamp": datetime.now().isoformat()
        }
        _cache_set("index", response, ttl=120)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy chỉ số thị trường: {str(e)}")


@app.get("/gold")
async def get_gold_price():
    """
    Lấy giá vàng SJC hiện tại
    
    Returns:
        Giá vàng SJC mua vào và bán ra
    """
    try:
        # Sử dụng Vnstock để lấy giá vàng
        vnstock = Vnstock()
        data = vnstock.stock(symbol='GOLD', source='VCI').quote.history(
            start=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end=datetime.now().strftime('%Y-%m-%d')
        )
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail="Không thể lấy dữ liệu giá vàng")
        
        return {
            "data": data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy giá vàng: {str(e)}")


@app.get("/screener")
async def stock_screener(
    exchange: str = Query(default="HOSE", description="Sàn giao dịch (HOSE/HNX/UPCOM)"),
    limit: int = Query(default=50, description="Số lượng cổ phiếu tối đa trả về")
):
    """
    Bộ lọc cổ phiếu theo sàn giao dịch
    
    Params:
        exchange: Sàn giao dịch (HOSE, HNX, UPCOM)
        limit: Số lượng cổ phiếu tối đa trả về
    
    Returns:
        Danh sách cổ phiếu theo điều kiện lọc
    """
    try:
        exchange = exchange.upper()
        if exchange not in ['HOSE', 'HNX', 'UPCOM']:
            raise HTTPException(status_code=400, detail="Sàn giao dịch phải là HOSE, HNX hoặc UPCOM")
        
        vnstock = Vnstock()
        # Sử dụng listing method để lấy danh sách cổ phiếu
        data = vnstock.stock(symbol='ACB', source='VCI').listing.all_symbols()
        
        if data is None or data.empty:
            raise HTTPException(status_code=404, detail="Không thể lấy danh sách cổ phiếu")
        
        # Lọc theo sàn giao dịch nếu có cột exchange
        if 'exchange' in data.columns:
            filtered_data = data[data['exchange'] == exchange]
        else:
            filtered_data = data
        
        # Giới hạn số lượng kết quả
        filtered_data = filtered_data.head(limit)
        
        return {
            "exchange": exchange,
            "limit": limit,
            "count": len(filtered_data),
            "data": filtered_data.to_dict(orient='records'),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lọc cổ phiếu: {str(e)}")


@app.get("/comprehensive_report/{ticker}")
async def get_comprehensive_report(ticker: str, limit: int = Query(4, description="Giới hạn số kỳ báo cáo")):
    """
    Lấy báo cáo tổng hợp (Company Info, Financials, Balance Sheet, Income Statement)
    
    Params:
        ticker: Mã cổ phiếu
        limit: Số kỳ báo cáo trả về (mặc định: 4)
    """
    cache_key = f"comprehensive:{ticker.upper()}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    ticker = ticker.upper()
    try:
        results = await asyncio.gather(
            get_company_info(ticker),
            get_financial_ratios(ticker, limit),
            get_balance_sheet(ticker, limit),
            get_income_statement(ticker, limit),
            return_exceptions=True
        )

        def handle_res(res):
            if isinstance(res, HTTPException):
                return {"error": res.detail}
            elif isinstance(res, Exception):
                return {"error": str(res)}
            return res

        profile_res = handle_res(results[0])
        ratios_res = handle_res(results[1])
        balance_res = handle_res(results[2])
        income_res = handle_res(results[3])

        def extract_data(res):
            if res and isinstance(res, dict) and "data" in res:
                return res["data"]
            return res

        response = {
            "ticker": ticker,
            "company_profile": profile_res,  # Contains 'data', 'source_provider', etc.
            "financial_ratios": extract_data(ratios_res),
            "balance_sheet": extract_data(balance_res),
            "income_statement": extract_data(income_res),
            "timestamp": datetime.now().isoformat()
        }
        
        _cache_set(cache_key, response, ttl=120)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy báo cáo tổng hợp: {str(e)}")


if __name__ == "__main__":
    print("🚀 Starting VNStock API Service on port 8050...")
    print("📊 Access API documentation at: http://localhost:8050/docs")
    uvicorn.run(app, host="0.0.0.0", port=8050)
