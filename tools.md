message_bot: Rakazo built-in. Takes confirm_name (the recipient bot's name: "Research Analyst" or "IC Reviewer"), intent ("request") and message (the text to send). Returns a receipt with ok, the recipient's bot id and name; the recipient's final reply arrives later as a new message to the sender.

web_search: Rakazo built-in (DuckDuckGo by default). Takes query and maxResults. Returns a list of results, each with title, url and snippet.

web_fetch: Rakazo built-in. Takes url and maxChars. Returns the page's url, title and text, cut to maxChars. Rakazo holds the fetch for approval when the URL did not come from the bot's own search results.

find_sec_company: Takes ticker. Returns the company's ticker, 10-digit SEC CIK and registered name, from SEC EDGAR.

get_sec_financials: Takes ticker and years (1-5, default 3). Returns a table of annual figures from the company's 10-K XBRL filings (revenue, net income, diluted EPS, operating cash flow, capex, cash, assets, liabilities and equity) by fiscal year, and each 10-K's accession number and filing date to cite.

list_sec_filings: Takes ticker, forms (default 10-K, 10-Q, 8-K and DEF 14A) and limit (default 8). Returns the company's recent SEC filings, each with its form, filing date, report period, accession number and link.

get_price_history: Takes ticker and period (1mo, 3mo, 6mo, 1y, 2y or 5y; default 1y). Returns the exchange and currency, the latest price with its UTC timestamp, the low, high, first and last daily close over the period with the change in percent, and a source line to register, from Yahoo Finance's chart endpoint.

read_client_document: Takes name (a document attached to the request). Returns the document's text headed by its confidentiality label; if no attached document has that name, returns an error listing the attached names.

register_source: Takes title, source_type (primary filing, company website, market data, company-provided, independent media, industry data or other), location (the URL retrieved, or the client document's name), date, confidence (high, medium or low) and claims (what the source supports). Adds the source to the case's register and returns its ID (S1, S2, ...) and citation form; returns the existing ID when the location is already registered.

list_sources: Takes no input. Returns the case's source register as a table of ID, title, type, location, date and confidence.

get_case_status: Takes no input. Returns what has arrived in the case: the run ID, the attached client documents with their confidentiality labels, the number of registered sources, the evidence packets, the latest memo draft and review, and the delivered versions.

save_evidence_packet: Takes topic, summary, findings (each ending with its source IDs), source_ids, counter_evidence and gaps. Saves the packet to the case file and returns its ID (E1, E2, ...) and any cited source IDs that are not in the register.

get_evidence_packets: Takes no input. Returns every saved evidence packet with its summary, findings, counter-evidence and gaps.

save_memo_draft: Takes markdown (the memo with inline [S#] citations), rating (Buy, Add, Hold, Reduce, Sell, Watchlist or Hold-off for a listed company; Invest, Wait or Pass for a private one) and data_as_of (YYYY-MM-DD). Saves a new memo version and returns its version number; returns an error for any other rating.

get_memo_draft: Takes version (0 for the latest). Returns that version's rating, data-as-of date and Markdown.

get_memo_check: Takes version (0 for the latest). Returns the version's rating, the cited IDs found in the register, the registered IDs it doesn't cite, and findings: cited IDs missing from the register, numbers without a source, company claims without a verification status, a rating the evidence gate doesn't support, internal working material, and a missing disclaimer or data-as-of date. It reports and never blocks.

save_review: Takes memo_version, verdict (approve, revise or reject), must_fix and should_fix (lists of items). Saves the review to the case file and returns its ID (R1, R2, ...); returns an error if that memo version doesn't exist.

get_latest_review: Takes no input. Returns the most recent review: the memo version it covers, its verdict and its must-fix and should-fix items.

deliver_memo: Takes version (0 for the latest). Records the delivery, writes the memo to memo_v<N>.md in the run folder, and returns the delivered version, the review gate (whether that version was reviewed and approved, and by which review) and the memo check. In Phase 1 it never blocks a delivery.
