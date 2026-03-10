# import streamlit as st
# from ml.optimization import optimize_portfolio
# from database.curd import get_purchased_stocks
# import pandas as pd
# # from fpdf import FPDF
# import os

# def optimize():

#     result=None
#     fig=None
#     analysis=None

#     if "user" not in st.session_state:
#         st.warning("You are not logged in. Please login first.")
#         st.session_state["page"] = "login"
#         del st.session_state["user"]
#         st.rerun()
    
        

#     if st.session_state.page == "optimize":
#         st.title("Portfolio Optimization")

#         # Fetch user details
#         user_id = st.session_state["user"]

#         # st.write(user_id)

#         # Fetch purchased stocks for the user
#         purchased_stocks = get_purchased_stocks(user_id)
#         if purchased_stocks:
#             stock_data = []
#             save_data = {}
#             for stock in purchased_stocks.values():
#                 if stock["sold"]==False:
#                     save={}
#                     save["company"]=str(stock["company_name"])
#                     save["ticker"]=str(stock["ticker"])
#                     save["stocks_owned"]=int(stock["quantity"])

#                     # save_data["portfolio"]=save
#                     stock_data.append(save)
                    

                    
#                     # stock_data.append([stock["company_name"], stock["quantity"], stock["price_per_stock"], stock["total_cost"]])
                        
#             # Display the purchased stocks in a table

#             if stock_data:

#                 st.subheader("Your Purchased Stocks")

#                 send_data = {}
#                 send_data["user"]=str(user_id)
#                 send_data["portfolio"]=stock_data

#                 # st.write(send_data)


#                 # st.write(portfolio_data)
                
#                 # st.write(send_data['user'])
#                 df = pd.DataFrame(
#                     [
#                         {
#                             "Company Name": stock["company_name"],
#                             "Quantity": stock["quantity"],
#                             "Price_per_stock": stock["price_per_stock"],
#                             "Total Cost": stock["total_cost"],
#                         }
#                         for stock in purchased_stocks.values() if not stock["sold"]
#                     ]
#                 )
                
                
#                 st.table(df)

#         else:
#             st.warning("No stocks purchased yet.")

        

#         if st.button("Optimize Portfolio"):

#             # st.session_state['content'] = False
#             st.session_state['pdf'] = None
#             result, fig = optimize_portfolio(send_data)
#             st.success("Portfolio optimized successfully!")
            
#             st.pyplot(fig)
            
#             # session is needed because page is refreshed so we need to store the result in session state
#             st.session_state['analysis'] = result["ai_analysis"]["overall_analysis"]
            
#             # st.write(result['ai_analysis']['company_specific_analysis'].keys()) 
#             st.session_state['company specific analysis'] = result["ai_analysis"]["company_specific_analysis"]
#             # st.session_state['content'] = True
#             st.session_state['pdf'] = result["ai_analysis"]["overall_analysis"]

#         if st.session_state.get("analysis"):
#             # clear=False
#             if st.button("Generate Report"):
#                 st.write("Analysis:", st.session_state.get("analysis"))
#                 # clear=st.button("Clear Analysis")
#                 del st.session_state['analysis']

        
#         if st.session_state.get("company specific analysis"):
#             if st.button("Generate Company Specific Report"):
#                 st.subheader("Company Specific Analysis")
#                 company_specific_analysis = st.session_state.get("company specific analysis")

#                 for company, analysis in company_specific_analysis.items():
#                     st.write(f"**Company: {company}**")
#                     st.write("Analysis:", analysis)

#                 del st.session_state['company specific analysis']
#                     # clear=st.button("Clear Analysis")
#                     # if clear:

            

#         # if st.session_state.get("pdf"):
#         #     if st.button("Generate PDF"):
#         #         analysis = st.session_state.get("pdf")
#         #         if analysis:
#         #             pdf = FPDF()
#         #             pdf.add_page()
#         #             pdf.set_font("Arial", style="B", size=12)
#         #             pdf.cell(200, 10, txt="Portfolio Optimization Report", ln=True, align="C")
#         #             pdf.ln(10)
#         #             pdf.multi_cell(0, 10, txt=analysis)

#         #             pdf_file_path = os.path.join(os.getcwd(), "Portfolio_Optimization_Report.pdf")
#         #             pdf.output(pdf_file_path)

#         #             with open(pdf_file_path, "rb") as pdf_file:
#         #                 st.write("Your download will start shortly...")
#         #                 pdf_data = pdf_file.read()
#         #                 st.write("Download your report:")
#         #                 st.download_button(
#         #                     label="click to download",
#         #                     data=pdf_data,
#         #                     file_name="Portfolio_Optimization_Report.pdf",
#         #                     mime="application/pdf"
#         #                 )

#         #             os.remove(pdf_file_path)

#         #             del st.session_state['pdf']


        

#         if st.button("Home"):
#             st.session_state["page"] = "home"
#             st.rerun()
   


# if __name__ == "__main__":
#     optimize()

import streamlit as st
import pandas as pd

from ml.optimization import optimize_portfolio
from services.cache import cached_portfolio
from services.stock_services import fetch_stock_data


def _display_name(name_or_ticker):
    return str(name_or_ticker or "").replace(".NS", "").strip()


def _looks_like_ticker_name(value):
    text = str(value or "").strip().upper()
    if not text:
        return True
    if text.endswith(".NS"):
        return True
    return all(ch.isalnum() or ch in {".", "-", "&"} for ch in text) and len(text) <= 15


def _resolved_company_name(raw_name, ticker, name_map):
    key = str(ticker or "").strip().upper()
    raw = str(raw_name or "").strip()
    fetched = str((name_map or {}).get(key, "")).strip()
    if fetched and (_looks_like_ticker_name(raw) or not raw):
        return fetched
    return raw or fetched or _display_name(key)


def _aggregate_holdings(active_stocks):
    """Combine multiple purchase entries for the same ticker into one holding."""
    aggregated = {}

    for s in active_stocks:
        ticker = str(s.get("ticker", "")).strip().upper()
        ticker = ticker if ticker.endswith(".NS") else (ticker + ".NS" if ticker else "")
        if not ticker:
            continue

        if ticker not in aggregated:
            aggregated[ticker] = {
                "company_name": _display_name(s.get("company_name", ticker.replace(".NS", ""))),
                "ticker": ticker,
                "quantity": 0,
                "total_cost": 0.0,
            }

        aggregated[ticker]["quantity"] += int(s.get("quantity", 0) or 0)
        aggregated[ticker]["total_cost"] += float(s.get("total_cost", 0) or 0)

    return list(aggregated.values())

def optimize():

    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    st.title("Portfolio Optimization")

    if st.button("Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

    user_id = st.session_state["user"]

    purchased_stocks = cached_portfolio(user_id)

    if not purchased_stocks:
        st.warning("No stocks purchased yet.")
        return

    active_stocks = [
        s for s in purchased_stocks.values() if not s.get("sold", False)
    ]

    if not active_stocks:
        st.warning("No active stocks in portfolio.")
        return

    # Portfolio display (deduplicated by ticker)
    holdings = _aggregate_holdings(active_stocks)

    if not holdings:
        st.warning("No valid holdings available for optimization.")
        return

    table_rows = []
    ticker_list = [str(s.get("ticker", "")).strip().upper() for s in holdings if str(s.get("ticker", "")).strip()]
    market_meta = fetch_stock_data(ticker_list) if ticker_list else {}
    name_map = (market_meta or {}).get("name_map", {})

    for s in holdings:
        quantity = int(s.get("quantity", 0) or 0)
        total_cost = float(s.get("total_cost", 0) or 0)

        ticker = str(s.get("ticker", "")).strip().upper()
        ticker_ns = ticker if ticker.endswith(".NS") else (ticker + ".NS" if ticker else "")

        live_price = 0.0
        if ticker_ns:
            live_price = float((market_meta or {}).get(ticker_ns, 0) or 0)

        stored_price = float(s.get("price_per_stock", 0) or 0)
        derived_price = (total_cost / quantity) if quantity > 0 else 0
        display_price = round(live_price or stored_price or derived_price, 2)

        table_rows.append({
            "Company": _resolved_company_name(s.get("company_name", ""), ticker_ns, name_map),
            "Quantity": quantity,
            "Price": display_price,
            "Total Cost": round(total_cost, 2),
        })

        s["position_value"] = float(quantity * display_price)

    df = pd.DataFrame(table_rows)

    df.index = df.index + 1

    st.subheader("Your Portfolio")
    st.dataframe(df, width='stretch')

    send_data = {
        "user": user_id,
        "portfolio": [
            {
                "company": _resolved_company_name(s.get("company_name", ""), s.get("ticker", ""), name_map),
                "ticker": s["ticker"],
                "stocks_owned": s["quantity"],
                "position_value": float(s.get("position_value", 0) or 0),
            }
            for s in holdings
        ]
    }

    use_ml_prediction = st.checkbox(
        "Use ML prediction (slow, may rate limit)",
        value=False,
        help="When enabled, optimization trains per-stock models via yfinance history. Keep off for faster and more reliable runs.",
    )

    use_ai_analysis = st.checkbox(
        "Use AI narrative analysis (slow)",
        value=False,
        help="Calls external LLM APIs for explanation. Turn off for fastest reliable optimization results.",
    )

    use_news_sentiment = st.checkbox(
        "Use live news sentiment (slow)",
        value=False,
        help="Scrapes external news websites per company. Keep off to avoid delays/rate limits.",
    )

    company_count = len(send_data.get("portfolio", []))
    quote_calls = 1  # batched quote fetch already performed above
    yfinance_training_calls = company_count if use_ml_prediction else 0
    ai_calls = (company_count + 1) if use_ai_analysis else 0  # overall + company-specific analysis
    news_calls = company_count * 2 if use_news_sentiment else 0

    if use_ml_prediction:
        st.warning(
            f"Estimated external load: quotes ~{quote_calls}, yfinance training ~{yfinance_training_calls}, AI calls ~{ai_calls}. "
            "This mode may trigger provider rate limits."
        )
    else:
        st.caption(
            f"Estimated external load (fast mode): quotes ~{quote_calls}, yfinance training ~0, AI calls ~{ai_calls}, news scrapes ~{news_calls}."
        )

    if st.button("Optimize Portfolio"):
        with st.spinner("Optimizing portfolio..."):
            result, fig = optimize_portfolio(
                send_data,
                use_ai_analysis=use_ai_analysis,
                use_market_agents=False,
                use_ml_prediction=use_ml_prediction,
                use_news_sentiment=use_news_sentiment,
                preloaded_quotes=market_meta,
            )

        if result is None or fig is None:
            st.error("Stock data unavailable due to rate limit. Please try again in a few minutes.")
            return

        st.session_state["result"] = result
        st.session_state["fig"] = fig

        ai_analysis = result.get("ai_analysis") or {}
        st.session_state["analysis"] = ai_analysis.get("overall_analysis", "AI analysis unavailable.")
        st.session_state["company_analysis"] = ai_analysis.get("company_specific_analysis", {})
    
    if "fig" in st.session_state:
        st.success("Portfolio optimized successfully!")
        st.pyplot(st.session_state["fig"])
        
    if st.session_state.get("analysis"):
        st.subheader("Overall Analysis")
        if "api error" in str(st.session_state["analysis"]).lower() or "organization has been restricted" in str(st.session_state["analysis"]).lower():
            st.warning("Live AI provider error detected. Showing fallback analysis.")
        st.write(st.session_state["analysis"])

    if st.session_state.get("company_analysis"):

        st.subheader("Company Specific Analysis")

        for company, analysis in st.session_state["company_analysis"].items():

            st.markdown(f"**{_display_name(company)}**")
            st.write(analysis)

    if st.button("Home"):
        st.session_state["page"] = "home"
        st.rerun()


if __name__ == "__main__":
    optimize()