"""
Generates complete metadata, data dictionary, temporal metadata, relationships,
validation expectations, and 100+ golden questions for Vidyut Electricals & Power Solutions.
"""

import os
import csv
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_DIR = os.path.join(BASE_DIR, "metadata")
os.makedirs(META_DIR, exist_ok=True)

# 1. DATA DICTIONARY
data_dict_rows = [
    # Master
    ["branches", "branch_id", "VARCHAR", "PK", "", "Unique branch identifier (e.g. BR-01)", "None", "Dimension"],
    ["branches", "branch_code", "VARCHAR", "", "", "Branch business shortcode (e.g. HQ-CHN)", "None", "Dimension"],
    ["branches", "branch_name", "VARCHAR", "", "", "Full branch display name", "None", "Dimension"],
    ["branches", "city", "VARCHAR", "", "", "City where branch is located (Chennai, Bangalore, Coimbatore)", "None", "Dimension"],
    ["branches", "area", "VARCHAR", "", "", "Locality/neighborhood address", "None", "Dimension"],
    ["branches", "branch_type", "VARCHAR", "", "", "Type of branch: Hub & Retail, Retail Outlet", "None", "Dimension"],
    ["branches", "opening_date", "DATE", "", "", "Date on which branch started operations", "Date branch opened for business", "Date"],
    ["branches", "status", "VARCHAR", "", "", "Operational status: Active, Inactive", "None", "Dimension"],

    ["employees", "employee_id", "VARCHAR", "PK", "", "Unique employee identifier (e.g. EMP-001)", "None", "Dimension"],
    ["employees", "employee_code", "VARCHAR", "", "", "Employee internal shortcode", "None", "Dimension"],
    ["employees", "employee_name", "VARCHAR", "", "", "Employee full legal name", "None", "Dimension"],
    ["employees", "role", "VARCHAR", "", "", "Job designation: Managing Director, Branch Manager, Sales Executive, etc.", "None", "Dimension"],
    ["employees", "branch_id", "VARCHAR", "FK", "branches.branch_id", "Branch where employee is stationed", "None", "Dimension"],
    ["employees", "joining_date", "DATE", "", "", "Date employee joined the company", "Date employment started", "Date"],
    ["employees", "exit_date", "DATE", "", "", "Date employee exited (NULL if currently active)", "Date employment ended", "Date"],
    ["employees", "status", "VARCHAR", "", "", "Employment status: Active, Exited", "None", "Dimension"],

    ["products", "product_id", "VARCHAR", "PK", "", "Unique product identifier (e.g. PRD-001)", "None", "Dimension"],
    ["products", "sku", "VARCHAR", "UK", "", "Stock Keeping Unit code (e.g. LED-BULB-09W)", "None", "Dimension"],
    ["products", "product_name", "VARCHAR", "", "", "Full product brand and technical description", "None", "Dimension"],
    ["products", "category", "VARCHAR", "", "", "Main product category (Lighting, Appliances, Wires & Cables, Switches, Switchgear, Accessories)", "None", "Dimension"],
    ["products", "subcategory", "VARCHAR", "", "", "Sub-classification (LED Bulbs, Ceiling Fans, Building Wires, etc.)", "None", "Dimension"],
    ["products", "brand", "VARCHAR", "", "", "Brand name (EcoGlow, Lumina, Zephyr, Orbit, MaxVolt, ElectroSafe, Vardhman, Kiran)", "None", "Dimension"],
    ["products", "unit", "VARCHAR", "", "", "Unit of measure: NOS (Pieces), COIL (90m Roll), MTR (Meter), PKT (Pack)", "None", "Dimension"],
    ["products", "purchase_price", "DOUBLE", "", "", "Standard supplier cost per unit (INR)", "None", "Measure"],
    ["products", "selling_price", "DOUBLE", "", "", "Base retail/contractor selling price per unit (INR)", "None", "Measure"],
    ["products", "reorder_level", "INTEGER", "", "", "Minimum safety stock trigger quantity", "None", "Measure"],
    ["products", "reorder_quantity", "INTEGER", "", "", "Standard procurement replenishment batch size", "None", "Measure"],
    ["products", "tax_rate", "DOUBLE", "", "", "Applicable GST percentage (18.0%)", "None", "Measure"],
    ["products", "launch_date", "DATE", "", "", "Date product was introduced to catalog", "Date product became sellable", "Date"],
    ["products", "discontinued_date", "DATE", "", "", "Date product was phased out (NULL if active)", "Date product sales ceased", "Date"],
    ["products", "status", "VARCHAR", "", "", "Catalog status: Active, Discontinued", "None", "Dimension"],

    ["customers", "customer_id", "VARCHAR", "PK", "", "Unique customer identifier (e.g. CUST-001)", "None", "Dimension"],
    ["customers", "customer_code", "VARCHAR", "", "", "Customer short code", "None", "Dimension"],
    ["customers", "customer_name", "VARCHAR", "", "", "Customer / business trading entity name", "None", "Dimension"],
    ["customers", "customer_type", "VARCHAR", "", "", "Customer segment: Contractor, Electrician, Retailer / Trader, Builder / Commercial, Institution, Small Commercial, Residential / B2C", "None", "Dimension"],
    ["customers", "phone", "VARCHAR", "", "", "Primary contact mobile number", "None", "Dimension"],
    ["customers", "email", "VARCHAR", "", "", "Contact email address", "None", "Dimension"],
    ["customers", "city", "VARCHAR", "", "", "Customer city (Chennai, Bangalore, Coimbatore)", "None", "Dimension"],
    ["customers", "area", "VARCHAR", "", "", "Locality / address area", "None", "Dimension"],
    ["customers", "state", "VARCHAR", "", "", "State (Tamil Nadu, Karnataka)", "None", "Dimension"],
    ["customers", "customer_since", "DATE", "", "", "Date customer first registered or transacted", "Date account was opened", "Date"],
    ["customers", "credit_allowed", "BOOLEAN", "", "", "Flag indicating whether credit billing is permitted", "None", "Dimension"],
    ["customers", "credit_limit", "DOUBLE", "", "", "Maximum approved credit exposure (INR)", "None", "Measure"],
    ["customers", "payment_terms", "VARCHAR", "", "", "Standard agreed terms: Net 7, Net 15, Net 30, Net 45, Immediate Cash, Immediate UPI, Immediate Card", "None", "Dimension"],
    ["customers", "status", "VARCHAR", "", "", "Account status: Active, Inactive", "None", "Dimension"],
    ["customers", "inactive_date", "DATE", "", "", "Date account became inactive (NULL if active)", "Date relationship ceased", "Date"],

    ["suppliers", "supplier_id", "VARCHAR", "PK", "", "Unique supplier identifier (e.g. SUP-001)", "None", "Dimension"],
    ["suppliers", "supplier_code", "VARCHAR", "", "", "Supplier short code", "None", "Dimension"],
    ["suppliers", "supplier_name", "VARCHAR", "", "", "Supplier registered corporate name", "None", "Dimension"],
    ["suppliers", "city", "VARCHAR", "", "", "Supplier headquarter city", "None", "Dimension"],
    ["suppliers", "state", "VARCHAR", "", "", "Supplier state", "None", "Dimension"],
    ["suppliers", "contact", "VARCHAR", "", "", "Vendor contact phone number", "None", "Dimension"],
    ["suppliers", "payment_terms", "VARCHAR", "", "", "Vendor payment credit terms (Net 15, Net 30, Net 45, Net 60, Advance 50%)", "None", "Dimension"],
    ["suppliers", "lead_time_days", "INTEGER", "", "", "Average lead time in calendar days from PO to receipt", "None", "Measure"],
    ["suppliers", "supplier_since", "DATE", "", "", "Date vendor onboarding agreement began", "Vendor relationship start date", "Date"],
    ["suppliers", "status", "VARCHAR", "", "", "Vendor status: Active, Inactive", "None", "Dimension"],

    # Sales
    ["sales_orders", "order_id", "VARCHAR", "PK", "", "Unique sales order number (e.g. SO-000001)", "None", "Dimension"],
    ["sales_orders", "order_date", "DATE", "", "", "Date on which sales order was placed", "Date order was booked by customer", "Date"],
    ["sales_orders", "customer_id", "VARCHAR", "FK", "customers.customer_id", "Customer placing the order", "None", "Dimension"],
    ["sales_orders", "customer_name", "VARCHAR", "", "", "Customer trading name", "None", "Dimension"],
    ["sales_orders", "customer_type", "VARCHAR", "", "", "Customer segment", "None", "Dimension"],
    ["sales_orders", "branch_id", "VARCHAR", "FK", "branches.branch_id", "Branch executing the order", "None", "Dimension"],
    ["sales_orders", "salesperson_id", "VARCHAR", "FK", "employees.employee_id", "Sales employee managing the sale", "None", "Dimension"],
    ["sales_orders", "subtotal", "DOUBLE", "", "", "Order total before GST taxes (INR)", "None", "Measure"],
    ["sales_orders", "tax_amount", "DOUBLE", "", "", "Total GST tax amount (INR)", "None", "Measure"],
    ["sales_orders", "grand_total", "DOUBLE", "", "", "Total invoiceable amount including tax (INR)", "None", "Measure"],
    ["sales_orders", "order_status", "VARCHAR", "", "", "Order lifecycle status: Invoiced, Cancelled", "None", "Dimension"],

    ["sales_order_items", "order_item_id", "VARCHAR", "PK", "", "Unique line item identifier", "None", "Dimension"],
    ["sales_order_items", "order_id", "VARCHAR", "FK", "sales_orders.order_id", "Parent sales order reference", "None", "Dimension"],
    ["sales_order_items", "order_date", "DATE", "", "", "Denormalized order transaction date", "Date of parent order", "Date"],
    ["sales_order_items", "product_id", "VARCHAR", "FK", "products.product_id", "Product SKU identifier", "None", "Dimension"],
    ["sales_order_items", "sku", "VARCHAR", "", "", "Stock keeping unit code", "None", "Dimension"],
    ["sales_order_items", "product_name", "VARCHAR", "", "", "Product description", "None", "Dimension"],
    ["sales_order_items", "category", "VARCHAR", "", "", "Product category", "None", "Dimension"],
    ["sales_order_items", "quantity", "INTEGER", "", "", "Number of units ordered", "None", "Measure"],
    ["sales_order_items", "unit_price", "DOUBLE", "", "", "Base unit selling price (INR)", "None", "Measure"],
    ["sales_order_items", "discount_pct", "DOUBLE", "", "", "Promotional / slab discount percentage applied", "None", "Measure"],
    ["sales_order_items", "final_price", "DOUBLE", "", "", "Discounted effective unit price (INR)", "None", "Measure"],
    ["sales_order_items", "line_total", "DOUBLE", "", "", "Net item subtotal = quantity * final_price (INR)", "None", "Measure"],
    ["sales_order_items", "tax_amount", "DOUBLE", "", "", "Item GST amount (INR)", "None", "Measure"],

    ["invoices", "invoice_id", "VARCHAR", "PK", "", "Unique tax invoice number (e.g. INV-000001)", "None", "Dimension"],
    ["invoices", "order_id", "VARCHAR", "FK", "sales_orders.order_id", "Linked sales order reference", "None", "Dimension"],
    ["invoices", "invoice_date", "DATE", "", "", "Date invoice was officially generated", "Date invoice was issued to customer", "Date"],
    ["invoices", "due_date", "DATE", "", "", "Payment contractual due date based on customer credit terms", "Contractual payment deadline", "Date"],
    ["invoices", "customer_id", "VARCHAR", "FK", "customers.customer_id", "Billed customer identifier", "None", "Dimension"],
    ["invoices", "customer_name", "VARCHAR", "", "", "Billed customer name", "None", "Dimension"],
    ["invoices", "branch_id", "VARCHAR", "FK", "branches.branch_id", "Billing branch", "None", "Dimension"],
    ["invoices", "subtotal", "DOUBLE", "", "", "Invoice taxable amount (INR)", "None", "Measure"],
    ["invoices", "tax_amount", "DOUBLE", "", "", "Invoice GST tax total (INR)", "None", "Measure"],
    ["invoices", "grand_total", "DOUBLE", "", "", "Invoice gross payable amount (INR)", "None", "Measure"],
    ["invoices", "payment_terms", "VARCHAR", "", "", "Payment terms applied to invoice", "None", "Dimension"],
    ["invoices", "payment_status", "VARCHAR", "", "", "Invoice payment status: Paid, Pending, Overdue", "None", "Dimension"],

    ["customer_payments", "payment_id", "VARCHAR", "PK", "", "Unique payment receipt identifier (e.g. PAY-000001)", "None", "Dimension"],
    ["customer_payments", "invoice_id", "VARCHAR", "FK", "invoices.invoice_id", "Invoice being settled", "None", "Dimension"],
    ["customer_payments", "order_id", "VARCHAR", "FK", "sales_orders.order_id", "Sales order reference", "None", "Dimension"],
    ["customer_payments", "customer_id", "VARCHAR", "FK", "customers.customer_id", "Payer customer identifier", "None", "Dimension"],
    ["customer_payments", "payment_date", "DATE", "", "", "Date on which money was received / bank credit occurred", "Date funds cleared in business account", "Date"],
    ["customer_payments", "amount_paid", "DOUBLE", "", "", "Total cash / bank amount received (INR)", "None", "Measure"],
    ["customer_payments", "payment_mode", "VARCHAR", "", "", "Payment channel: NEFT / Bank Transfer, UPI, Cash, Cheque, Credit Card, RTGS", "None", "Dimension"],
    ["customer_payments", "reference_number", "VARCHAR", "", "", "Bank UTR / Transaction reference number", "None", "Dimension"],
    ["customer_payments", "notes", "VARCHAR", "", "", "Payment narration / remarks", "None", "Dimension"],

    # Inventory
    ["inventory_movements", "movement_id", "VARCHAR", "PK", "", "Unique movement ledger record (e.g. MOV-0000001)", "None", "Dimension"],
    ["inventory_movements", "movement_date", "DATE", "", "", "Date and time when physical stock movement occurred", "Date inventory quantity changed", "Date"],
    ["inventory_movements", "branch_id", "VARCHAR", "FK", "branches.branch_id", "Branch / warehouse location", "None", "Dimension"],
    ["inventory_movements", "product_id", "VARCHAR", "FK", "products.product_id", "Product SKU moved", "None", "Dimension"],
    ["inventory_movements", "sku", "VARCHAR", "", "", "SKU code", "None", "Dimension"],
    ["inventory_movements", "movement_type", "VARCHAR", "", "", "Movement category: PURCHASE_IN, SALE_OUT, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT_DAMAGE, CUSTOMER_RETURN_IN", "None", "Dimension"],
    ["inventory_movements", "quantity_change", "INTEGER", "", "", "Quantity delta (+ positive for inflows, - negative for outflows)", "None", "Measure"],
    ["inventory_movements", "running_balance", "INTEGER", "", "", "Cumulative closing stock on hand at branch after movement", "None", "Measure"],
    ["inventory_movements", "reference_doc_id", "VARCHAR", "", "", "Source transaction reference (GRN ID, Invoice ID, Transfer ID, Adjustment ID)", "None", "Dimension"],
    ["inventory_movements", "description", "VARCHAR", "", "", "Ledger movement narration", "None", "Dimension"],

    # Finance
    ["expenses", "expense_id", "VARCHAR", "PK", "", "Unique operating expense voucher ID (e.g. EXP-000001)", "None", "Dimension"],
    ["expenses", "expense_date", "DATE", "", "", "Date on which expense occurred or was paid", "Date expenditure occurred", "Date"],
    ["expenses", "branch_id", "VARCHAR", "FK", "branches.branch_id", "Branch incurring the expense", "None", "Dimension"],
    ["expenses", "category", "VARCHAR", "", "", "Expense head: Rent, Salaries, Electricity & Utilities, Vehicle Fuel & Freight, Office Supplies, Staff Refreshments", "None", "Dimension"],
    ["expenses", "amount", "DOUBLE", "", "", "Expense amount paid (INR)", "None", "Measure"],
    ["expenses", "description", "VARCHAR", "", "", "Detailed purpose of expenditure", "None", "Dimension"],
    ["expenses", "payment_mode", "VARCHAR", "", "", "Payment instrument: Bank Transfer, Online Banking, Cash / UPI", "None", "Dimension"],
    ["expenses", "status", "VARCHAR", "", "", "Payment state: Paid, Accrued", "None", "Dimension"]
]

with open(os.path.join(META_DIR, "data_dictionary.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["dataset_name", "column_name", "data_type", "key_type", "references", "description", "date_semantics", "role"])
    writer.writerows(data_dict_rows)

print(f"Generated data_dictionary.csv with {len(data_dict_rows)} column entries.")

# 2. TEMPORAL METADATA
temporal_meta = {
    "enterprise_name": "Vidyut Electricals & Power Solutions",
    "timezone": "Asia/Kolkata",
    "fiscal_year_start": "04-01",
    "historical_start": "2024-01-01",
    "historical_cutoff": "2026-09-30",
    "forecast_horizon_start": "2026-10-01",
    "forecast_horizon_end": "2026-12-31",
    "datasets": {
        "sales_orders": {
            "primary_date_column": "order_date",
            "secondary_date_columns": [],
            "temporal_grain": "daily",
            "date_semantics": "Date order was booked by customer",
            "suitable_for_forecasting": True,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "sales_order_items": {
            "primary_date_column": "order_date",
            "secondary_date_columns": [],
            "temporal_grain": "daily / item-level",
            "date_semantics": "Date order was placed for specific SKU line item",
            "suitable_for_forecasting": True,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "invoices": {
            "primary_date_column": "invoice_date",
            "secondary_date_columns": ["due_date"],
            "temporal_grain": "daily",
            "date_semantics": "invoice_date = date billed; due_date = contractual payment deadline",
            "suitable_for_forecasting": True,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "customer_payments": {
            "primary_date_column": "payment_date",
            "secondary_date_columns": [],
            "temporal_grain": "daily / transactional",
            "date_semantics": "Date cash/bank receipt cleared into accounts",
            "suitable_for_forecasting": True,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "inventory_movements": {
            "primary_date_column": "movement_date",
            "secondary_date_columns": [],
            "temporal_grain": "continuous event timestamp",
            "date_semantics": "Date physical stock moved in or out of warehouse/branch",
            "suitable_for_forecasting": True,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "purchase_orders": {
            "primary_date_column": "po_date",
            "secondary_date_columns": ["expected_delivery_date"],
            "temporal_grain": "daily",
            "date_semantics": "po_date = date PO issued; expected_delivery_date = promised supplier dispatch",
            "suitable_for_forecasting": False,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "goods_receipts": {
            "primary_date_column": "receipt_date",
            "secondary_date_columns": [],
            "temporal_grain": "daily",
            "date_semantics": "Date goods arrived and were verified by warehouse supervisor",
            "suitable_for_forecasting": False,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "expenses": {
            "primary_date_column": "expense_date",
            "secondary_date_columns": [],
            "temporal_grain": "daily / monthly recurring",
            "date_semantics": "Date operational expense voucher was booked / settled",
            "suitable_for_forecasting": True,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "product_price_history": {
            "primary_date_column": "effective_date",
            "secondary_date_columns": [],
            "temporal_grain": "event effective date",
            "date_semantics": "Date price revision came into effect across branches",
            "suitable_for_forecasting": False,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "promotions": {
            "primary_date_column": "start_date",
            "secondary_date_columns": ["end_date"],
            "temporal_grain": "campaign validity window",
            "date_semantics": "start_date = campaign launch; end_date = campaign expiry",
            "suitable_for_forecasting": False,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "deliveries": {
            "primary_date_column": "order_date",
            "secondary_date_columns": ["promised_date", "actual_delivery_date"],
            "temporal_grain": "daily delivery lifecycle",
            "date_semantics": "Lifecycle from order date to promised date and actual delivery date",
            "suitable_for_forecasting": False,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        },
        "salesperson_targets": {
            "primary_date_column": "period_start",
            "secondary_date_columns": ["period_end"],
            "temporal_grain": "monthly target window",
            "date_semantics": "Monthly quota performance evaluation window",
            "suitable_for_forecasting": False,
            "suitable_for_trend_analysis": True,
            "suitable_for_period_comparison": True
        }
    }
}

with open(os.path.join(META_DIR, "temporal_metadata.json"), "w", encoding="utf-8") as f:
    json.dump(temporal_meta, f, indent=2)

print("Generated temporal_metadata.json.")

# 3. RELATIONSHIPS METADATA
relationships = {
    "enterprise": "Vidyut Electricals & Power Solutions",
    "entities": ["branches", "employees", "suppliers", "products", "customers"],
    "transactions": [
        "sales_orders", "sales_order_items", "invoices", "customer_payments", "sales_returns", "credit_notes",
        "purchase_orders", "purchase_order_items", "goods_receipts", "goods_receipt_items",
        "inventory_opening_balances", "inventory_movements", "stock_transfers", "stock_adjustments",
        "expenses", "cash_transactions", "deliveries", "salesperson_targets", "product_price_history", "promotions"
    ],
    "foreign_keys": [
        {"from_table": "employees", "from_column": "branch_id", "to_table": "branches", "to_column": "branch_id", "type": "many-to-one"},
        {"from_table": "sales_orders", "from_column": "customer_id", "to_table": "customers", "to_column": "customer_id", "type": "many-to-one"},
        {"from_table": "sales_orders", "from_column": "branch_id", "to_table": "branches", "to_column": "branch_id", "type": "many-to-one"},
        {"from_table": "sales_orders", "from_column": "salesperson_id", "to_table": "employees", "to_column": "employee_id", "type": "many-to-one"},
        {"from_table": "sales_order_items", "from_column": "order_id", "to_table": "sales_orders", "to_column": "order_id", "type": "many-to-one"},
        {"from_table": "sales_order_items", "from_column": "product_id", "to_table": "products", "to_column": "product_id", "type": "many-to-one"},
        {"from_table": "invoices", "from_column": "order_id", "to_table": "sales_orders", "to_column": "order_id", "type": "one-to-one"},
        {"from_table": "invoices", "from_column": "customer_id", "to_table": "customers", "to_column": "customer_id", "type": "many-to-one"},
        {"from_table": "customer_payments", "from_column": "invoice_id", "to_table": "invoices", "to_column": "invoice_id", "type": "many-to-one"},
        {"from_table": "purchase_orders", "from_column": "supplier_id", "to_table": "suppliers", "to_column": "supplier_id", "type": "many-to-one"},
        {"from_table": "purchase_order_items", "from_column": "po_id", "to_table": "purchase_orders", "to_column": "po_id", "type": "many-to-one"},
        {"from_table": "purchase_order_items", "from_column": "product_id", "to_table": "products", "to_column": "product_id", "type": "many-to-one"},
        {"from_table": "goods_receipts", "from_column": "po_id", "to_table": "purchase_orders", "to_column": "po_id", "type": "many-to-one"},
        {"from_table": "goods_receipt_items", "from_column": "receipt_id", "to_table": "goods_receipts", "to_column": "receipt_id", "type": "many-to-one"},
        {"from_table": "inventory_movements", "from_column": "branch_id", "to_table": "branches", "to_column": "branch_id", "type": "many-to-one"},
        {"from_table": "inventory_movements", "from_column": "product_id", "to_table": "products", "to_column": "product_id", "type": "many-to-one"},
        {"from_table": "deliveries", "from_column": "order_id", "to_table": "sales_orders", "to_column": "order_id", "type": "many-to-one"},
        {"from_table": "expenses", "from_column": "branch_id", "to_table": "branches", "to_column": "branch_id", "type": "many-to-one"}
    ]
}

with open(os.path.join(META_DIR, "relationships.json"), "w", encoding="utf-8") as f:
    json.dump(relationships, f, indent=2)

print("Generated relationships.json.")

# 4. GOLDEN QUESTIONS (105 Realistic Questions)
golden_q_list = [
    # Historical
    ["HQ-001", "Historical Aggregation", "What was the total sales revenue generated in 2024?", "SELECT SUM(grand_total) FROM sales_orders WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31' AND order_status != 'Cancelled'", "sales_orders", "grand_total, order_date"],
    ["HQ-002", "Historical Aggregation", "What were the total sales in 2025 across all branches?", "SELECT SUM(grand_total) FROM sales_orders WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31'", "sales_orders", "grand_total, order_date"],
    ["HQ-003", "Historical Aggregation", "What is the total revenue achieved year-to-date in 2026 (up to September 30)?", "SELECT SUM(grand_total) FROM sales_orders WHERE order_date BETWEEN '2026-01-01' AND '2026-09-30'", "sales_orders", "grand_total, order_date"],
    ["HQ-004", "Category Breakdown", "What is the revenue breakdown by product category in 2025?", "SELECT category, SUM(line_total) AS revenue FROM sales_order_items WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY category ORDER BY revenue DESC", "sales_order_items", "category, line_total, order_date"],
    ["HQ-005", "Branch Breakdown", "Which branch had the highest sales revenue in 2024?", "SELECT b.branch_name, SUM(so.grand_total) AS total_sales FROM sales_orders so JOIN branches b ON so.branch_id = b.branch_id WHERE so.order_date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY b.branch_name ORDER BY total_sales DESC LIMIT 1", "sales_orders, branches", "grand_total, branch_id, branch_name"],
    ["HQ-006", "Branch Breakdown", "Compare total sales revenue between Chennai, Bangalore, and Coimbatore branches for 2025.", "SELECT b.city, SUM(so.grand_total) AS total_sales FROM sales_orders so JOIN branches b ON so.branch_id = b.branch_id WHERE so.order_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY b.city ORDER BY total_sales DESC", "sales_orders, branches", "city, grand_total"],
    ["HQ-007", "Top Products", "What were the top 5 best-selling products by quantity in 2025?", "SELECT product_name, SUM(quantity) AS total_qty FROM sales_order_items WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY product_name ORDER BY total_qty DESC LIMIT 5", "sales_order_items", "product_name, quantity"],
    ["HQ-008", "Top Products", "What are the top 10 revenue-generating SKUs across all time?", "SELECT sku, product_name, SUM(line_total) AS revenue FROM sales_order_items GROUP BY sku, product_name ORDER BY revenue DESC LIMIT 10", "sales_order_items", "sku, product_name, line_total"],
    ["HQ-009", "Top Customers", "Who are our top 5 customers by total invoice billing?", "SELECT customer_name, customer_type, SUM(grand_total) AS total_spent FROM invoices GROUP BY customer_name, customer_type ORDER BY total_spent DESC LIMIT 5", "invoices", "customer_name, grand_total"],
    ["HQ-010", "Customer Segment", "What proportion of our sales comes from Contractors compared to Retailers and B2C?", "SELECT customer_type, SUM(grand_total) AS revenue, ROUND(100.0 * SUM(grand_total) / (SELECT SUM(grand_total) FROM sales_orders), 2) AS pct_share FROM sales_orders GROUP BY customer_type ORDER BY revenue DESC", "sales_orders", "customer_type, grand_total"],

    # Time-Series & Trends
    ["HQ-011", "Monthly Trend", "Show monthly sales revenue trend for 2024 and 2025.", "SELECT STRFTIME(order_date, '%Y-%m') AS month, SUM(grand_total) AS revenue FROM sales_orders WHERE order_date <= '2025-12-31' GROUP BY month ORDER BY month", "sales_orders", "order_date, grand_total"],
    ["HQ-012", "Monthly Trend", "What was our highest sales revenue month in company history?", "SELECT STRFTIME(order_date, '%Y-%m') AS month, SUM(grand_total) AS revenue FROM sales_orders GROUP BY month ORDER BY revenue DESC LIMIT 1", "sales_orders", "order_date, grand_total"],
    ["HQ-013", "Seasonality", "Which months consistently show peak sales for Fans & Appliances?", "SELECT STRFTIME(order_date, '%m') AS month_num, SUM(line_total) AS fan_sales FROM sales_order_items WHERE category = 'Appliances' GROUP BY month_num ORDER BY fan_sales DESC", "sales_order_items", "category, line_total, order_date"],
    ["HQ-014", "Seasonality", "How do Lighting sales perform during October and November compared to other months?", "SELECT CASE WHEN STRFTIME(order_date, '%m') IN ('10', '11') THEN 'Festive Season (Oct-Nov)' ELSE 'Rest of Year' END AS period, AVG(line_total) AS avg_item_sale, SUM(line_total) AS total_sales FROM sales_order_items WHERE category = 'Lighting' GROUP BY period", "sales_order_items", "category, line_total, order_date"],
    ["HQ-015", "Year-over-Year Growth", "What was the year-over-year revenue growth percentage from 2024 to 2025?", "WITH yearly AS (SELECT STRFTIME(order_date, '%Y') AS yr, SUM(grand_total) AS rev FROM sales_orders GROUP BY yr) SELECT y25.rev AS rev_2025, y24.rev AS rev_2024, ROUND(100.0 * (y25.rev - y24.rev) / y24.rev, 2) AS yoy_growth_pct FROM yearly y25, yearly y24 WHERE y25.yr = '2025' AND y24.yr = '2024'", "sales_orders", "order_date, grand_total"],
    ["HQ-016", "Quarterly Comparison", "Compare Q1 2024, Q1 2025, and Q1 2026 total revenue.", "SELECT STRFTIME(order_date, '%Y') AS year, SUM(grand_total) AS q1_revenue FROM sales_orders WHERE STRFTIME(order_date, '%m') IN ('01', '02', '03') GROUP BY year ORDER BY year", "sales_orders", "order_date, grand_total"],
    ["HQ-017", "Quarterly Comparison", "Compare Q2 2025 with Q2 2026 sales revenue.", "SELECT STRFTIME(order_date, '%Y') AS year, SUM(grand_total) AS q2_revenue FROM sales_orders WHERE STRFTIME(order_date, '%m') IN ('04', '05', '06') GROUP BY year ORDER BY year", "sales_orders", "order_date, grand_total"],
    ["HQ-018", "Quarterly Trend", "Show total sales revenue grouped by calendar quarter from Q1 2024 to Q3 2026.", "SELECT STRFTIME(order_date, '%Y') || '-Q' || CAST((CAST(STRFTIME(order_date, '%m') AS INTEGER) - 1)/3 + 1 AS VARCHAR) AS quarter, SUM(grand_total) AS revenue FROM sales_orders GROUP BY quarter ORDER BY quarter", "sales_orders", "order_date, grand_total"],
    ["HQ-019", "Product Trend", "How has monthly demand for 1.5 sq mm wire (WIR-FR-150) evolved over time?", "SELECT STRFTIME(order_date, '%Y-%m') AS month, SUM(quantity) AS coils_sold FROM sales_order_items WHERE sku = 'WIR-FR-150' GROUP BY month ORDER BY month", "sales_order_items", "sku, quantity, order_date"],
    ["HQ-020", "Product Trend", "Did the launch of Zephyr BLDC fans in March 2024 impact standard ceiling fan sales?", "SELECT STRFTIME(order_date, '%Y-Q') AS quarter, sku, SUM(quantity) AS units_sold FROM sales_order_items WHERE sku IN ('FAN-CEIL-1200', 'FAN-BLDC-1200') GROUP BY quarter, sku ORDER BY quarter, sku", "sales_order_items", "sku, quantity, order_date"],

    # Forecasting & Predictive Questions
    ["HQ-021", "Forecasting Total Sales", "Forecast total sales revenue for Q4 2026 (October, November, December).", "Prediction task using historical sales_orders time series (2024-01-01 to 2026-09-30)", "sales_orders", "order_date, grand_total"],
    ["HQ-022", "Forecasting Monthly Demand", "What is the projected sales revenue for October 2026?", "Prediction task using monthly seasonality and YoY trend from historical sales_orders", "sales_orders", "order_date, grand_total"],
    ["HQ-023", "Product Demand Forecast", "Forecast monthly demand for EcoGlow 9W LED Bulbs (PRD-001) for the next 3 months.", "Time-series forecasting on sales_order_items for PRD-001", "sales_order_items", "product_id, quantity, order_date"],
    ["HQ-024", "Product Demand Forecast", "What will demand look like for Orbit 2.5 sq mm copper wire in Q4 2026?", "Time-series forecasting on sales_order_items for WIR-FR-250", "sales_order_items", "sku, quantity, order_date"],
    ["HQ-025", "Branch Sales Forecast", "Forecast Q4 2026 sales revenue for the Bangalore Electronic City branch.", "Branch-level time series forecasting on sales_orders for BR-02", "sales_orders", "branch_id, grand_total, order_date"],
    ["HQ-026", "Branch Sales Forecast", "Forecast Q4 2026 sales revenue for the Coimbatore branch.", "Branch-level time series forecasting on sales_orders for BR-03", "sales_orders", "branch_id, grand_total, order_date"],
    ["HQ-027", "Category Forecast", "Forecast lighting category sales for the upcoming Diwali festive season in Q4 2026.", "Category-level forecasting factoring in October/November seasonal multipliers", "sales_order_items", "category, line_total, order_date"],
    ["HQ-028", "Expense Forecast", "What are our expected operating expenses for next month (October 2026)?", "Time series forecasting on expenses factoring in recurring rent, salaries, utilities, and historical variance", "expenses", "expense_date, amount, category"],
    ["HQ-029", "Cash Flow Forecast", "Will customer cash collections exceed operating expenses over the next 60 days?", "Cash flow simulation: forecast payments + cash sales vs projected expenses", "customer_payments, expenses, cash_transactions", "payment_date, expense_date, amount"],
    ["HQ-030", "Inventory Stockout Forecast", "Which SKUs have current stock levels lower than their 30-day forecasted demand?", "Inventory stock level comparison against 30-day demand forecast per product", "inventory_movements, sales_order_items, products", "product_id, running_balance, quantity"],

    # Inventory & Supply Chain
    ["HQ-031", "Stock on Hand", "What is our current stock on hand across all branches for each SKU as of September 30, 2026?", "SELECT p.sku, p.product_name, SUM(im.quantity_change) AS current_stock FROM inventory_movements im JOIN products p ON im.product_id = p.product_id GROUP BY p.sku, p.product_name ORDER BY p.sku", "inventory_movements, products", "product_id, quantity_change"],
    ["HQ-032", "Central Hub Inventory", "What is the stock on hand at the Chennai Central Hub (BR-01)?", "SELECT p.sku, p.product_name, SUM(im.quantity_change) AS hub_stock FROM inventory_movements im JOIN products p ON im.product_id = p.product_id WHERE im.branch_id = 'BR-01' GROUP BY p.sku, p.product_name", "inventory_movements, products", "branch_id, quantity_change"],
    ["HQ-033", "Reorder Level Breach", "Which products currently have stock below their designated reorder level at the Chennai Central Hub?", "WITH current_stock AS (SELECT product_id, SUM(quantity_change) AS qty FROM inventory_movements WHERE branch_id = 'BR-01' GROUP BY product_id) SELECT p.sku, p.product_name, cs.qty AS on_hand, p.reorder_level FROM current_stock cs JOIN products p ON cs.product_id = p.product_id WHERE cs.qty < p.reorder_level", "inventory_movements, products", "quantity_change, reorder_level"],
    ["HQ-034", "Slow Moving Inventory", "Which active SKUs have had zero or fewer than 10 sales in the last 90 days?", "SELECT p.sku, p.product_name, COALESCE(SUM(soi.quantity), 0) AS units_sold_last_90_days FROM products p LEFT JOIN sales_order_items soi ON p.product_id = soi.product_id AND soi.order_date BETWEEN '2026-07-01' AND '2026-09-30' WHERE p.status = 'Active' GROUP BY p.sku, p.product_name HAVING units_sold_last_90_days < 10 ORDER BY units_sold_last_90_days", "products, sales_order_items", "sku, quantity, order_date"],
    ["HQ-035", "Stock Transfers", "How many inter-branch stock transfers occurred from Chennai Hub to Bangalore in 2025?", "SELECT COUNT(*), SUM(quantity_transferred) FROM stock_transfers WHERE from_branch = 'BR-01' AND to_branch = 'BR-02' AND transfer_date BETWEEN '2025-01-01' AND '2025-12-31'", "stock_transfers", "from_branch, to_branch, transfer_date, quantity_transferred"],
    ["HQ-036", "Damaged Stock", "What is the total quantity and valuation of stock written off due to damages in 2025?", "SELECT p.category, SUM(ABS(sa.quantity_adjusted)) AS total_units_damaged, SUM(ABS(sa.quantity_adjusted) * p.purchase_price) AS damage_valuation FROM stock_adjustments sa JOIN products p ON sa.product_id = p.product_id WHERE sa.adjustment_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY p.category", "stock_adjustments, products", "quantity_adjusted, purchase_price, adjustment_date"],
    ["HQ-037", "Supplier Purchase Volume", "Which supplier did we spend the most with in 2025?", "SELECT supplier_name, SUM(total_amount) AS total_purchases FROM purchase_orders WHERE po_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY supplier_name ORDER BY total_purchases DESC", "purchase_orders", "supplier_name, total_amount, po_date"],
    ["HQ-038", "Supplier Lead Time & Delays", "Which suppliers have experienced delivery delays exceeding their contractual lead time?", "SELECT po.supplier_name, COUNT(*) AS delayed_shipments, AVG(DATEDIFF('day', po.expected_delivery_date, gr.receipt_date)) AS avg_days_late FROM purchase_orders po JOIN goods_receipts gr ON po.po_id = gr.po_id WHERE gr.receipt_date > po.expected_delivery_date GROUP BY po.supplier_name ORDER BY delayed_shipments DESC", "purchase_orders, goods_receipts", "expected_delivery_date, receipt_date, supplier_name"],
    ["HQ-039", "Partial Goods Receipts", "How many purchase orders received partial goods receipts rather than full delivery in 2025?", "SELECT COUNT(*) FROM goods_receipts WHERE inspection_status = 'Partial Receipt' AND receipt_date BETWEEN '2025-01-01' AND '2025-12-31'", "goods_receipts", "inspection_status, receipt_date"],
    ["HQ-040", "Inventory Turnover", "What is the inventory turnover ratio by product category in 2025?", "Calculated from COGS (sum of quantity_sold * purchase_price) divided by average inventory valuation", "sales_order_items, products, inventory_movements", "quantity, purchase_price, line_total"],

    # Finance & Accounts Receivable
    ["HQ-041", "Accounts Receivable Outstanding", "What is the total outstanding unpaid accounts receivable balance as of September 30, 2026?", "SELECT SUM(grand_total) FROM invoices WHERE payment_status IN ('Pending', 'Overdue')", "invoices", "grand_total, payment_status"],
    ["HQ-042", "Overdue Invoices", "What is the total overdue invoice balance past due date as of September 30, 2026?", "SELECT SUM(grand_total) FROM invoices WHERE payment_status = 'Overdue' AND due_date < '2026-09-30'", "invoices", "grand_total, payment_status, due_date"],
    ["HQ-043", "Overdue Customers", "Which customers have the highest overdue payment balance?", "SELECT customer_name, SUM(grand_total) AS overdue_balance FROM invoices WHERE payment_status = 'Overdue' GROUP BY customer_name ORDER BY overdue_balance DESC LIMIT 5", "invoices", "customer_name, grand_total, payment_status"],
    ["HQ-044", "Credit Limit Utilization", "Which customers are currently utilizing more than 80% of their approved credit limit?", "WITH outstanding AS (SELECT customer_id, SUM(grand_total) AS balance FROM invoices WHERE payment_status IN ('Pending', 'Overdue') GROUP BY customer_id) SELECT c.customer_name, c.credit_limit, o.balance, ROUND(100.0 * o.balance / c.credit_limit, 2) AS util_pct FROM outstanding o JOIN customers c ON o.customer_id = c.customer_id WHERE c.credit_allowed = TRUE AND (o.balance / c.credit_limit) > 0.80 ORDER BY util_pct DESC", "invoices, customers", "grand_total, credit_limit, payment_status"],
    ["HQ-045", "Payment Delay Days", "What is the average number of days taken by Contractors to settle invoices compared to agreed payment terms?", "SELECT c.customer_type, AVG(DATEDIFF('day', inv.invoice_date, cp.payment_date)) AS avg_days_to_pay FROM customer_payments cp JOIN invoices inv ON cp.invoice_id = inv.invoice_id JOIN customers c ON cp.customer_id = c.customer_id GROUP BY c.customer_type", "customer_payments, invoices, customers", "invoice_date, payment_date, customer_type"],
    ["HQ-046", "Payment Modes", "What percentage of customer payments were collected via UPI, NEFT, and Cash in 2025?", "SELECT payment_mode, COUNT(*) AS tx_count, SUM(amount_paid) AS total_collected, ROUND(100.0 * SUM(amount_paid) / (SELECT SUM(amount_paid) FROM customer_payments WHERE payment_date BETWEEN '2025-01-01' AND '2025-12-31'), 2) AS share_pct FROM customer_payments WHERE payment_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY payment_mode ORDER BY total_collected DESC", "customer_payments", "payment_mode, amount_paid, payment_date"],
    ["HQ-047", "Operating Expenses Breakdown", "What was the breakdown of operating expenses by category in 2025?", "SELECT category, SUM(amount) AS total_expense FROM expenses WHERE expense_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY category ORDER BY total_expense DESC", "expenses", "category, amount, expense_date"],
    ["HQ-048", "Monthly Rent and Salaries", "What is our fixed monthly overhead commitment across rent and staff salaries?", "SELECT STRFTIME(expense_date, '%Y-%m') AS month, SUM(amount) AS fixed_overhead FROM expenses WHERE category IN ('Rent', 'Salaries') GROUP BY month ORDER BY month DESC LIMIT 12", "expenses", "category, amount, expense_date"],
    ["HQ-049", "Net Operating Margin", "What was our estimated gross profit margin in 2025 (Revenue minus COGS)?", "WITH cogs AS (SELECT SUM(soi.quantity * p.purchase_price) AS total_cogs, SUM(soi.line_total) AS total_rev FROM sales_order_items soi JOIN products p ON soi.product_id = p.product_id WHERE soi.order_date BETWEEN '2025-01-01' AND '2025-12-31') SELECT total_rev, total_cogs, (total_rev - total_cogs) AS gross_profit, ROUND(100.0 * (total_rev - total_cogs) / total_rev, 2) AS gross_margin_pct FROM cogs", "sales_order_items, products", "quantity, purchase_price, line_total, order_date"],
    ["HQ-050", "Cash Inflow vs Outflow", "Compare monthly total cash inflows and outflows for 2025.", "SELECT STRFTIME(transaction_date, '%Y-%m') AS month, SUM(CASE WHEN flow_type = 'INFLOW' THEN amount ELSE 0 END) AS total_inflow, SUM(CASE WHEN flow_type = 'OUTFLOW' THEN amount ELSE 0 END) AS total_outflow FROM cash_transactions WHERE transaction_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY month ORDER BY month", "cash_transactions", "transaction_date, flow_type, amount"],

    # Pricing & Margin Impact
    ["HQ-051", "Price Revision Impact", "When did the copper wire price increase take effect, and what was the new selling price for 1.5 sq mm wire?", "SELECT effective_date, purchase_price, selling_price, change_reason FROM product_price_history WHERE sku = 'WIR-FR-150' ORDER BY effective_date DESC", "product_price_history", "sku, effective_date, selling_price, purchase_price"],
    ["HQ-052", "Price Revision Impact", "Did unit sales volume of Orbit wires decline in the 60 days following the February 2025 price increase?", "SELECT CASE WHEN order_date BETWEEN '2024-12-01' AND '2025-01-31' THEN '60 Days Pre-Price Hike' WHEN order_date BETWEEN '2025-02-01' AND '2025-03-31' THEN '60 Days Post-Price Hike' END AS period, SUM(quantity) AS total_coils_sold, SUM(line_total) AS revenue FROM sales_order_items WHERE category = 'Wires & Cables' AND order_date BETWEEN '2024-12-01' AND '2025-03-31' GROUP BY period", "sales_order_items", "category, quantity, line_total, order_date"],
    ["HQ-053", "Product Margin Comparison", "Which product category yields the highest average gross profit margin percentage?", "SELECT p.category, SUM(soi.line_total) AS rev, SUM(soi.quantity * p.purchase_price) AS cogs, ROUND(100.0 * (SUM(soi.line_total) - SUM(soi.quantity * p.purchase_price)) / SUM(soi.line_total), 2) AS margin_pct FROM sales_order_items soi JOIN products p ON soi.product_id = p.product_id GROUP BY p.category ORDER BY margin_pct DESC", "sales_order_items, products", "category, line_total, quantity, purchase_price"],
    ["HQ-054", "Price History Inquiry", "List all price revisions that occurred during 2025.", "SELECT * FROM product_price_history WHERE effective_date BETWEEN '2025-01-01' AND '2025-12-31' ORDER BY effective_date", "product_price_history", "effective_date, sku, selling_price"],
    ["HQ-055", "Promotion Effectiveness", "How much revenue was generated during the Diwali 2024 promotion compared to regular weeks?", "SELECT p.promo_name, SUM(soi.line_total) AS promo_revenue FROM sales_order_items soi, promotions p WHERE soi.order_date BETWEEN p.start_date AND p.end_date AND p.promo_id = 'PROMO-001' GROUP BY p.promo_name", "sales_order_items, promotions", "order_date, line_total, start_date, end_date"],

    # Operations & Deliveries
    ["HQ-056", "On-Time Delivery Rate", "What percentage of contractor deliveries were delivered on or before the promised delivery date in 2025?", "SELECT COUNT(*) AS total_deliveries, SUM(CASE WHEN actual_delivery_date <= promised_date THEN 1 ELSE 0 END) AS on_time_deliveries, ROUND(100.0 * SUM(CASE WHEN actual_delivery_date <= promised_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct FROM deliveries WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31' AND delivery_status = 'Delivered'", "deliveries", "order_date, promised_date, actual_delivery_date, delivery_status"],
    ["HQ-057", "Delivery Delay Analysis", "What was the average delivery delay in days for orders delivered late in 2025?", "SELECT AVG(DATEDIFF('day', promised_date, actual_delivery_date)) AS avg_delay_days FROM deliveries WHERE actual_delivery_date > promised_date AND order_date BETWEEN '2025-01-01' AND '2025-12-31'", "deliveries", "promised_date, actual_delivery_date, order_date"],
    ["HQ-058", "Sales Rep Target Achievement", "Which sales executives achieved over 100% of their monthly sales quota in August 2025?", "Sales performance comparison joining salesperson_targets with sales_orders by salesperson_id and month", "salesperson_targets, sales_orders", "target_month, target_amount, grand_total"],
    ["HQ-059", "Top Performing Salesperson", "Who was the top-performing salesperson by total revenue generated in 2025?", "SELECT e.employee_name, b.branch_name, SUM(so.grand_total) AS total_sales FROM sales_orders so JOIN employees e ON so.salesperson_id = e.employee_id JOIN branches b ON so.branch_id = b.branch_id WHERE so.order_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY e.employee_name, b.branch_name ORDER BY total_sales DESC LIMIT 1", "sales_orders, employees, branches", "employee_name, grand_total, order_date"],
    ["HQ-060", "Customer Returns Rate", "What was the total value of sales returns and credit notes issued in 2025?", "SELECT SUM(refund_amount) AS total_returns FROM sales_returns WHERE return_date BETWEEN '2025-01-01' AND '2025-12-31'", "sales_returns", "refund_amount, return_date"],
    ["HQ-061", "Product Return Causes", "Which product SKU had the highest number of defect returns?", "SELECT sku, COUNT(*) AS return_incidents, SUM(quantity_returned) AS units_returned, reason FROM sales_returns GROUP BY sku, reason ORDER BY units_returned DESC LIMIT 3", "sales_returns", "sku, quantity_returned, reason"],

    # Customer Lifecycle & Attrition
    ["HQ-062", "Customer Inactivity", "Which customers have not placed any orders since January 1, 2026?", "SELECT c.customer_id, c.customer_name, c.city, MAX(so.order_date) AS last_order_date FROM customers c LEFT JOIN sales_orders so ON c.customer_id = so.customer_id WHERE c.status = 'Active' GROUP BY c.customer_id, c.customer_name, c.city HAVING last_order_date < '2026-01-01' OR last_order_date IS NULL ORDER BY last_order_date", "customers, sales_orders", "customer_name, order_date, status"],
    ["HQ-063", "Declining Customer Spend", "Which B2B contractor customers experienced a spend decline of more than 20% in 2026 compared to 2025?", "Quarterly and annual customer spend comparison between 2025 and 2026", "sales_orders, customers", "customer_name, grand_total, order_date"],
    ["HQ-064", "New Customer Acquisition", "How many new customers transacted with us for the first time in 2025?", "SELECT COUNT(*) FROM customers WHERE customer_since BETWEEN '2025-01-01' AND '2025-12-31'", "customers", "customer_since"],
    ["HQ-065", "Repeat Customer Order Frequency", "What is the average order frequency per month for contractor customers?", "SELECT c.customer_name, COUNT(so.order_id) / 33.0 AS avg_orders_per_month FROM sales_orders so JOIN customers c ON so.customer_id = c.customer_id WHERE c.customer_type = 'Contractor' GROUP BY c.customer_name ORDER BY avg_orders_per_month DESC", "sales_orders, customers", "customer_name, customer_type, order_id"],

    # Scenario Simulation & What-If Analysis
    ["HQ-066", "Scenario Price Increase", "What would be the estimated impact on gross profit if selling prices across all LED lighting products increase by 5%?", "Simulation applying +5% to line_total for category='Lighting' on historical base", "sales_order_items, products", "category, line_total, quantity"],
    ["HQ-067", "Scenario Copper Cost Surge", "If copper wire supplier costs increase by 10% next quarter without retail price adjustment, what will be the margin reduction?", "Simulation increasing purchase_price by 10% on Wires & Cables", "sales_order_items, products", "category, purchase_price, line_total"],
    ["HQ-068", "Scenario Credit Period Relaxation", "If credit terms for Tier-2 electricians are relaxed from Net 15 to Net 30, what is the estimated increase in accounts receivable working capital requirement?", "Working capital exposure simulation based on average monthly electrician billing", "invoices, customers", "customer_type, grand_total, payment_terms"],
    ["HQ-069", "Scenario Warehouse Consolidation", "How much monthly showroom and warehouse rent would be saved if Bangalore retail shifted to a smaller footprint saving 20% lease rent?", "Expense reduction simulation: 20% off BR-02 lease rent", "expenses", "branch_id, category, amount"],
    ["HQ-070", "Scenario Discount Elimination", "What was the total rupee value of trade discounts given to customers in 2025?", "SELECT SUM(quantity * unit_price * (discount_pct / 100.0)) AS total_discounts_given FROM sales_order_items WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31'", "sales_order_items", "quantity, unit_price, discount_pct, order_date"],

    # Knowledge / Policy RAG Queries
    ["HQ-071", "Business Knowledge RAG", "What is the company's approved credit policy for electrical contractors?", "RAG retrieval from credit_policy.txt (Category B contractors: Net 30 days, limit up to Rs. 2,50,000)", "credit_policy.txt", "RAG Document Knowledge"],
    ["HQ-072", "Business Knowledge RAG", "What is the warranty period and return policy for defective LED bulbs?", "RAG retrieval from return_policy.txt (2 years over-the-counter replacement warranty)", "return_policy.txt", "RAG Document Knowledge"],
    ["HQ-073", "Business Knowledge RAG", "What are the standard working hours and Sunday timings for our branches?", "RAG retrieval from branch_operations.txt (Mon-Sat 9:30 AM to 8:30 PM, closed Sunday except Diwali season)", "branch_operations.txt", "RAG Document Knowledge"],
    ["HQ-074", "Business Knowledge RAG", "What are the volume rebate slabs available for high-billing electrical contractors?", "RAG retrieval from discount_policy.txt (1.5% for 5-10L, 3.0% for 10-25L, 4.5% above 25L)", "discount_policy.txt", "RAG Document Knowledge"],
    ["HQ-075", "Business Knowledge RAG", "What are our designated bank account details for receiving RTGS and NEFT customer payments?", "RAG retrieval from payment_terms.txt (HDFC Bank Parrys Corner Branch)", "payment_terms.txt", "RAG Document Knowledge"],
    ["HQ-076", "Business Knowledge RAG", "What is the standard reorder protocol when central hub inventory falls below safety levels?", "RAG retrieval from inventory_policy.txt (2 weeks buffer stock, automatic reorder trigger)", "inventory_policy.txt", "RAG Document Knowledge"],
    ["HQ-077", "Business Knowledge RAG", "What is the company policy when a supplier delivery is delayed by more than 5 days?", "RAG retrieval from procurement_policy.txt (Notify branch managers, prioritize alternate stock transfers)", "procurement_policy.txt", "RAG Document Knowledge"],
    ["HQ-078", "Business Knowledge RAG", "Who is authorized to approve customer credit limit increases exceeding Rs. 50,000?", "RAG retrieval from credit_policy.txt (Managing Director Venkatesh Kumar)", "credit_policy.txt", "RAG Document Knowledge"],
    ["HQ-079", "Business Knowledge RAG", "Under what conditions can custom-cut underground power cables be returned?", "RAG retrieval from return_policy.txt (Non-returnable item)", "return_policy.txt", "RAG Document Knowledge"],
    ["HQ-080", "Business Knowledge RAG", "What is the spot cash discount permitted for counter invoice payments above Rs. 10,000?", "RAG retrieval from discount_policy.txt (1.0% spot cash discount)", "discount_policy.txt", "RAG Document Knowledge"],

    # Hybrid Cross-Dataset Reasoning
    ["HQ-081", "Cross-Dataset Hybrid", "Did customers with overdue invoices receive sales deliveries during August 2026?", "Join between invoices (payment_status='Overdue') and deliveries (actual_delivery_date in August 2026)", "invoices, deliveries", "payment_status, actual_delivery_date, customer_id"],
    ["HQ-082", "Cross-Dataset Hybrid", "Did supplier delivery delays in Q2 2025 correspond to stockouts in 1.5 sq mm copper wire?", "Correlate goods_receipts delay with inventory_movements running balance reaching 0", "goods_receipts, purchase_orders, inventory_movements", "receipt_date, expected_delivery_date, running_balance"],
    ["HQ-083", "Cross-Dataset Hybrid", "Compare monthly salesperson commission quotas against actual billed invoices for each rep in 2025.", "Join salesperson_targets with invoices grouped by salesperson_id and month", "salesperson_targets, invoices, employees", "target_amount, grand_total, target_month"],
    ["HQ-084", "Cross-Dataset Hybrid", "Identify which contractors qualified for the 3% annual loyalty volume rebate based on 2025 invoice billing exceeding Rs. 10 Lakhs.", "SELECT customer_name, SUM(grand_total) AS total_annual_billing FROM invoices WHERE invoice_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY customer_name HAVING total_annual_billing BETWEEN 1000000 AND 2500000", "invoices, discount_policy.txt", "customer_name, grand_total, invoice_date"],
    ["HQ-085", "Cross-Dataset Hybrid", "Did the price reduction in LED batten lights in July 2025 result in an increase in monthly unit sales volume?", "Compare monthly quantity in sales_order_items pre and post July 2025 for PRD-004 and PRD-005", "sales_order_items, product_price_history", "sku, quantity, order_date, effective_date"],
    ["HQ-086", "Cross-Dataset Hybrid", "What was the total procurement spend with Orbit Wires compared to the total revenue generated from Orbit products in 2025?", "Compare SUM(purchase_order_items.line_total) for Orbit with SUM(sales_order_items.line_total) for brand='Orbit'", "purchase_order_items, sales_order_items, products", "brand, line_total"],
    ["HQ-087", "Cross-Dataset Hybrid", "Calculate the average gross margin earned per branch in 2025 after accounting for branch operating expenses.", "Branch gross profit (revenue minus cogs) minus branch operating expenses from expenses table", "sales_order_items, products, expenses, branches", "branch_id, line_total, purchase_price, amount"],
    ["HQ-088", "Cross-Dataset Hybrid", "Which products experienced both price increases and sales volume growth in 2025?", "Identify SKUs with price increase in product_price_history and positive YoY quantity growth", "sales_order_items, product_price_history", "sku, quantity, effective_date"],
    ["HQ-089", "Cross-Dataset Hybrid", "Find all sales orders where the actual delivery date exceeded promised date by more than 2 days.", "SELECT * FROM deliveries WHERE DATEDIFF('day', promised_date, actual_delivery_date) > 2", "deliveries, sales_orders", "promised_date, actual_delivery_date, order_id"],
    ["HQ-090", "Cross-Dataset Hybrid", "What is the total cash outflow across supplier purchases, rent, salaries, and electricity for each quarter of 2025?", "Aggregate cash_transactions outflow grouped by quarter and category", "cash_transactions", "transaction_date, flow_type, category, amount"],

    # Granular Period & Entity Comparisons
    ["HQ-091", "Period Comparison", "Compare total units of 9W LED bulbs sold between Diwali 2024 and Diwali 2025.", "Filter sales_order_items for PRD-001 during festive promotion dates in 2024 and 2025", "sales_order_items, promotions", "sku, quantity, order_date"],
    ["HQ-092", "Period Comparison", "Compare summer fan sales revenue in March-May 2024 vs March-May 2025 vs March-May 2026.", "Aggregate sales_order_items where category='Appliances' across the three summer periods", "sales_order_items", "category, line_total, order_date"],
    ["HQ-093", "Period Comparison", "How did Coimbatore branch sales grow from Q3 2024 to Q3 2025 to Q3 2026?", "Compare Coimbatore sales_orders across Q3 of 2024, 2025, and 2026", "sales_orders, branches", "branch_id, grand_total, order_date"],
    ["HQ-094", "Entity Comparison", "Compare average order value between Chennai Central Hub and Bangalore Retail Outlet.", "SELECT b.branch_name, AVG(so.grand_total) AS aov, COUNT(*) AS total_orders FROM sales_orders so JOIN branches b ON so.branch_id = b.branch_id WHERE so.branch_id IN ('BR-01', 'BR-02') GROUP BY b.branch_name", "sales_orders, branches", "branch_id, grand_total"],
    ["HQ-095", "Entity Comparison", "Compare profit margins between Lumina Lighting products and EcoGlow Lighting products.", "SELECT p.brand, SUM(soi.line_total) AS rev, SUM(soi.quantity * p.purchase_price) AS cogs, ROUND(100.0 * (SUM(soi.line_total) - SUM(soi.quantity * p.purchase_price)) / SUM(soi.line_total), 2) AS margin_pct FROM sales_order_items soi JOIN products p ON soi.product_id = p.product_id WHERE p.brand IN ('Lumina', 'EcoGlow') GROUP BY p.brand", "sales_order_items, products", "brand, line_total, purchase_price"],

    # Advanced Multi-Dimensional Queries
    ["HQ-096", "Multi-Dimensional", "Which day of the week typically generates the highest sales revenue?", "SELECT STRFTIME(order_date, '%w') AS day_num, CASE STRFTIME(order_date, '%w') WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END AS day_name, SUM(grand_total) AS revenue, COUNT(*) AS order_count FROM sales_orders GROUP BY day_num, day_name ORDER BY revenue DESC", "sales_orders", "order_date, grand_total"],
    ["HQ-097", "Multi-Dimensional", "What is the distribution of sales revenue across different invoice value brackets (<Rs 5k, 5k-25k, 25k-100k, >100k)?", "SELECT CASE WHEN grand_total < 5000 THEN 'Under 5K' WHEN grand_total BETWEEN 5000 AND 25000 THEN '5K to 25K' WHEN grand_total BETWEEN 25000 AND 100000 THEN '25K to 100K' ELSE 'Over 100K' END AS ticket_size, COUNT(*) AS order_count, SUM(grand_total) AS total_revenue FROM sales_orders GROUP BY ticket_size ORDER BY total_revenue DESC", "sales_orders", "grand_total"],
    ["HQ-098", "Multi-Dimensional", "Which zip/area in Chennai generates the highest sales volume for industrial switchgear?", "SELECT c.area, SUM(soi.line_total) AS switchgear_sales FROM sales_order_items soi JOIN sales_orders so ON soi.order_id = so.order_id JOIN customers c ON so.customer_id = c.customer_id WHERE soi.category = 'Switchgear' AND c.city = 'Chennai' GROUP BY c.area ORDER BY switchgear_sales DESC", "sales_order_items, sales_orders, customers", "area, city, category, line_total"],
    ["HQ-099", "Multi-Dimensional", "What is the average collection turnaround time (DSO) for invoices issued in Q1 2025 vs Q1 2026?", "Days Sales Outstanding calculation from invoice date to payment date", "invoices, customer_payments", "invoice_date, payment_date, grand_total"],
    ["HQ-100", "Multi-Dimensional", "What is the total value of GST tax collected and remitted to government in FY 2024-25 (April 2024 to March 2025)?", "SELECT SUM(tax_amount) AS total_output_gst FROM invoices WHERE invoice_date BETWEEN '2024-04-01' AND '2025-03-31'", "invoices", "tax_amount, invoice_date"],

    # Verification & Holdout Accuracy Check Questions
    ["HQ-101", "Holdout Evaluation", "What were the actual total sales in Q4 2026 (holdout evaluation)?", "SELECT SUM(grand_total) FROM actual_sales_q4_2026", "actual_sales_q4_2026", "grand_total, order_date"],
    ["HQ-102", "Holdout Evaluation", "What was the actual demand for 9W LED bulbs in October 2026?", "SELECT SUM(quantity) FROM actual_sales_items_q4_2026 WHERE sku = 'LED-BULB-09W' AND order_date BETWEEN '2026-10-01' AND '2026-10-31'", "actual_sales_items_q4_2026", "sku, quantity, order_date"],
    ["HQ-103", "Holdout Evaluation", "Compare UNIVA forecasted sales for Q4 2026 against actual holdout sales to calculate forecast error (MAPE).", "Holdout evaluation metric comparing forecasted series vs actual_sales_q4_2026", "actual_sales_q4_2026, sales_orders", "grand_total, order_date"],
    ["HQ-104", "Holdout Evaluation", "Did Diwali festive lighting sales in October/November 2026 follow the predicted seasonal surge?", "Comparison of holdout lighting sales against seasonal forecast", "actual_sales_items_q4_2026", "category, line_total, order_date"],
    ["HQ-105", "Holdout Evaluation", "What was the actual gross revenue achieved by Bangalore branch in Q4 2026?", "SELECT SUM(grand_total) FROM actual_sales_q4_2026 WHERE branch_id = 'BR-02'", "actual_sales_q4_2026", "branch_id, grand_total, order_date"]
]

with open(os.path.join(META_DIR, "golden_questions.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["question_id", "category", "natural_language_question", "expected_sql_or_approach", "primary_tables", "key_attributes"])
    writer.writerows(golden_q_list)

print(f"Generated golden_questions.csv with {len(golden_q_list)} curated golden benchmark questions.")

# 5. DATASET CATALOG (Machine-Readable JSON)
catalog_data = {
    "enterprise": {
        "name": "Vidyut Electricals & Power Solutions",
        "description": "Indian micro-enterprise trading in electrical equipment, lighting, switchgear, wires & appliances across South India.",
        "branches_count": 3,
        "employees_count": 12,
        "products_count": 38,
        "customers_count": 48,
        "suppliers_count": 8,
        "historical_period": "2024-01-01 to 2026-09-30",
        "holdout_period": "2026-10-01 to 2026-12-31"
    },
    "tables": [
        {"name": "branches", "category": "master", "file": "data/master/branches.csv", "grain": "branch", "description": "Branch locations & showrooms"},
        {"name": "employees", "category": "master", "file": "data/master/employees.csv", "grain": "employee", "description": "Staff roster, roles, and branch assignments"},
        {"name": "suppliers", "category": "master", "file": "data/master/suppliers.csv", "grain": "supplier", "description": "Approved vendor list, lead times, and payment terms"},
        {"name": "products", "category": "master", "file": "data/master/products.csv", "grain": "product SKU", "description": "Product catalog, pricing, tax rates, and reorder levels"},
        {"name": "customers", "category": "master", "file": "data/master/customers.csv", "grain": "customer", "description": "B2B contractors, electricians, retailers, institutions, B2C clients"},
        {"name": "sales_orders", "category": "sales", "file": "data/sales/sales_orders.csv", "grain": "order", "description": "Header sales orders with dates, branches, and totals"},
        {"name": "sales_order_items", "category": "sales", "file": "data/sales/sales_order_items.csv", "grain": "order line item", "description": "Line item sales with quantities, prices, and discounts"},
        {"name": "invoices", "category": "sales", "file": "data/sales/invoices.csv", "grain": "invoice", "description": "Tax invoices issued to customers with due dates and payment status"},
        {"name": "customer_payments", "category": "sales", "file": "data/sales/customer_payments.csv", "grain": "payment transaction", "description": "Cash, UPI, and bank receipts from customers"},
        {"name": "sales_returns", "category": "sales", "file": "data/sales/sales_returns.csv", "grain": "return event", "description": "Customer return records and warranty defect claims"},
        {"name": "credit_notes", "category": "sales", "file": "data/sales/credit_notes.csv", "grain": "credit note", "description": "Credit notes issued for return refunds and ledger adjustments"},
        {"name": "purchase_orders", "category": "procurement", "file": "data/procurement/purchase_orders.csv", "grain": "purchase order", "description": "Supplier purchase orders with dates and expected delivery"},
        {"name": "purchase_order_items", "category": "procurement", "file": "data/procurement/purchase_order_items.csv", "grain": "PO line item", "description": "Items ordered from suppliers with quantities and costs"},
        {"name": "goods_receipts", "category": "procurement", "file": "data/procurement/goods_receipts.csv", "grain": "goods receipt note", "description": "Warehouse receipts and inspection notes"},
        {"name": "goods_receipt_items", "category": "procurement", "file": "data/procurement/goods_receipt_items.csv", "grain": "GRN line item", "description": "Items received from suppliers with condition status"},
        {"name": "inventory_opening_balances", "category": "inventory", "file": "data/inventory/inventory_opening_balances.csv", "grain": "branch-SKU opening count", "description": "Initial stock count as of 2024-01-01"},
        {"name": "inventory_movements", "category": "inventory", "file": "data/inventory/inventory_movements.csv", "grain": "stock transaction", "description": "Continuous stock ledger movements with running balances"},
        {"name": "stock_transfers", "category": "inventory", "file": "data/inventory/stock_transfers.csv", "grain": "transfer event", "description": "Inter-branch stock replenishments from Chennai Central Hub"},
        {"name": "stock_adjustments", "category": "inventory", "file": "data/inventory/stock_adjustments.csv", "grain": "adjustment event", "description": "Physical count reconciliations and damage write-offs"},
        {"name": "expenses", "category": "finance", "file": "data/finance/expenses.csv", "grain": "expense voucher", "description": "Operating expenses: rent, salaries, utilities, freight, supplies"},
        {"name": "cash_transactions", "category": "finance", "file": "data/finance/cash_transactions.csv", "grain": "cash/bank transaction", "description": "Cash and bank flow ledger with inflows and outflows"},
        {"name": "deliveries", "category": "operations", "file": "data/operations/deliveries.csv", "grain": "delivery shipment", "description": "Logistics dispatch records with promised and actual dates"},
        {"name": "salesperson_targets", "category": "operations", "file": "data/operations/salesperson_targets.csv", "grain": "employee-month quota", "description": "Monthly sales targets assigned to sales executives"},
        {"name": "product_price_history", "category": "pricing", "file": "data/pricing/product_price_history.csv", "grain": "price revision event", "description": "Historical price changes with effective dates and reasons"},
        {"name": "promotions", "category": "marketing", "file": "data/marketing/promotions.csv", "grain": "promotional campaign", "description": "Marketing discount promotions and seasonal festival campaigns"}
    ]
}

with open(os.path.join(META_DIR, "dataset_catalog.json"), "w", encoding="utf-8") as f:
    json.dump(catalog_data, f, indent=2)

print("Generated dataset_catalog.json.")

# 6. VALIDATION EXPECTATIONS
expectations = {
    "foreign_key_checks": [
        {"table": "sales_orders", "column": "customer_id", "ref_table": "customers", "ref_column": "customer_id"},
        {"table": "sales_orders", "column": "branch_id", "ref_table": "branches", "ref_column": "branch_id"},
        {"table": "sales_orders", "column": "salesperson_id", "ref_table": "employees", "ref_column": "employee_id"},
        {"table": "sales_order_items", "column": "order_id", "ref_table": "sales_orders", "ref_column": "order_id"},
        {"table": "sales_order_items", "column": "product_id", "ref_table": "products", "ref_column": "product_id"},
        {"table": "invoices", "column": "order_id", "ref_table": "sales_orders", "ref_column": "order_id"},
        {"table": "customer_payments", "column": "invoice_id", "ref_table": "invoices", "ref_column": "invoice_id"},
        {"table": "purchase_orders", "column": "supplier_id", "ref_table": "suppliers", "ref_column": "supplier_id"},
        {"table": "goods_receipts", "column": "po_id", "ref_table": "purchase_orders", "ref_column": "po_id"},
        {"table": "inventory_movements", "column": "product_id", "ref_table": "products", "ref_column": "product_id"},
        {"table": "inventory_movements", "column": "branch_id", "ref_table": "branches", "ref_column": "branch_id"}
    ],
    "temporal_integrity_checks": [
        {"rule": "order_date <= invoice_date", "table_pair": ["sales_orders", "invoices"], "keys": ["order_id", "order_id"]},
        {"rule": "invoice_date <= due_date", "table": "invoices", "date_cols": ["invoice_date", "due_date"]},
        {"rule": "po_date <= expected_delivery_date", "table": "purchase_orders", "date_cols": ["po_date", "expected_delivery_date"]},
        {"rule": "po_date <= receipt_date", "table_pair": ["purchase_orders", "goods_receipts"], "keys": ["po_id", "po_id"], "date_cols": ["po_date", "receipt_date"]},
        {"rule": "order_date <= promised_date", "table": "deliveries", "date_cols": ["order_date", "promised_date"]},
        {"rule": "all_historical_dates <= 2026-09-30", "scope": "All historical datasets in data/"},
        {"rule": "holdout_dates in 2026-10-01 to 2026-12-31", "scope": "validation/future_holdout/"}
    ],
    "business_logic_checks": [
        {"rule": "invoice grand_total == subtotal + tax_amount", "table": "invoices"},
        {"rule": "sales_order grand_total == subtotal + tax_amount", "table": "sales_orders"},
        {"rule": "inventory movement balance arithmetic: running_balance == prev_balance + quantity_change", "table": "inventory_movements"}
    ]
}

with open(os.path.join(META_DIR, "validation_expectations.json"), "w", encoding="utf-8") as f:
    json.dump(expectations, f, indent=2)

print("Generated validation_expectations.json.")
