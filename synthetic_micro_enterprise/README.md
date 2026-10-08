# Vidyut Electricals & Power Solutions — Synthetic Micro-Enterprise Business Data Ecosystem

This directory contains a complete, realistic, relational, and forecasting-ready synthetic business dataset representing **Vidyut Electricals & Power Solutions**, a fictional Indian micro-enterprise (MSME) trading in electrical equipment, industrial switchgear, lighting fixtures, copper cables, and appliances across South India.

---

## 1. Enterprise Profile & Persona

- **Company Name**: Vidyut Electricals & Power Solutions
- **Legal Form**: Partnership Firm (MSME Registered)
- **Founders**: Venkatesh Kumar & Ravi Shankar
- **Headquarters & Central Hub**: Parrys Corner, George Town, Chennai, Tamil Nadu
- **Branch Network**:
  - `BR-01`: Chennai Central Hub & Showroom (Chennai)
  - `BR-02`: Bangalore Electronic City Retail Outlet (Bangalore)
  - `BR-03`: Coimbatore Townhall Branch (Coimbatore)
- **Product Lines**: 38 SKUs across 6 categories (Lighting, Appliances, Wires & Cables, Switches, Switchgear, Accessories).
- **Customer Ecosystem**: 48 B2B & B2C customers (Licensed Electrical Contractors, Regional Retailers, Certified Electricians, Builders, IT Institutions, and Homeowners).
- **Supplier Ecosystem**: 8 Primary Manufacturers and Distributors with varied lead times, credit terms, and delivery delays.

---

## 2. Directory Structure

```
synthetic_micro_enterprise/
├── data/
│   ├── master/
│   │   ├── branches.csv                  # 3 branch showroom locations
│   │   ├── employees.csv                 # 12 employees across management, sales, and warehouse
│   │   ├── suppliers.csv                 # 8 approved vendors with lead times and terms
│   │   ├── products.csv                  # 38 product SKUs with cost, price, and reorder levels
│   │   └── customers.csv                 # 48 B2B and B2C customer master accounts
│   │
│   ├── sales/
│   │   ├── sales_orders.csv              # 4,466 header sales orders with dates and totals
│   │   ├── sales_order_items.csv         # 15,062 order line items with quantities and prices
│   │   ├── invoices.csv                  # 4,466 tax invoices with due dates and payment status
│   │   ├── customer_payments.csv         # 4,376 receipts across UPI, NEFT, Cheque, and Cash
│   │   ├── sales_returns.csv             # 74 warranty return and defect records
│   │   └── credit_notes.csv              # 74 credit notes issued for customer refunds
│   │
│   ├── procurement/
│   │   ├── purchase_orders.csv           # 174 supplier purchase orders
│   │   ├── purchase_order_items.csv      # 606 purchase order line items
│   │   ├── goods_receipts.csv            # 173 warehouse goods receipts (GRNs)
│   │   └── goods_receipt_items.csv       # 604 inspected receipt items
│   │
│   ├── inventory/
│   │   ├── inventory_opening_balances.csv# 114 opening balance records as of 2024-01-01
│   │   ├── inventory_movements.csv       # 15,813 continuous stock ledger transactions
│   │   ├── stock_transfers.csv           # 35 inter-branch replenishment transfers
│   │   └── stock_adjustments.csv         # Physical stock audit damage adjustments
│   │
│   ├── finance/
│   │   ├── expenses.csv                  # 538 operating expense vouchers (rent, salaries, EB)
│   │   └── cash_transactions.csv         # 4,914 cash and bank ledger transactions
│   │
│   ├── operations/
│   │   ├── deliveries.csv                # 1,352 site delivery shipments with promised/actual dates
│   │   └── salesperson_targets.csv       # 252 monthly sales quotas per sales executive
│   │
│   ├── pricing/
│   │   └── product_price_history.csv     # 49 price revision events (copper surge, LED drop)
│   │
│   ├── marketing/
│   │   └── promotions.csv                # 8 seasonal marketing campaigns (Diwali, Summer Fan)
│   │
│   └── knowledge/                        # 9 Business Knowledge & Policy Documents (for RAG)
│       ├── company_profile.txt
│       ├── sales_policy.txt
│       ├── credit_policy.txt
│       ├── return_policy.txt
│       ├── inventory_policy.txt
│       ├── procurement_policy.txt
│       ├── payment_terms.txt
│       ├── branch_operations.txt
│       └── discount_policy.txt
│
├── metadata/
│   ├── data_dictionary.csv               # 119 column definitions, data types, keys, and date semantics
│   ├── dataset_catalog.json              # Machine-readable schema catalog and grain definitions
│   ├── relationships.json                # Foreign key graph and entity relationships
│   ├── temporal_metadata.json            # Temporal grain, primary date fields, and forecastability flags
│   ├── golden_questions.csv              # 105 curated benchmark questions spanning all query classes
│   └── validation_expectations.json      # Assertions, constraints, and relational validation rules
│
├── generator/
│   ├── generate_micro_enterprise.py      # Deterministic, parameterizable Python data generator
│   └── generate_metadata.py              # Metadata, schema, and golden question generator
│
├── validation/
│   ├── validate_relationships.py         # Foreign key and primary key uniqueness validator
│   ├── validate_temporal_integrity.py    # Temporal bounds, date causality, and leakage validator
│   ├── validate_business_rules.py        # Financial arithmetic and ledger continuity validator
│   └── future_holdout/
│       ├── actual_sales_q4_2026.csv      # 499 actual orders (unseen ground truth for holdout testing)
│       └── actual_sales_items_q4_2026.csv# 1,639 actual line items in Q4 2026
│
└── README.md
```

---

## 3. Temporal Architecture & Forecasting Support

### A. Temporal Range
- **Historical Data Range**: `2024-01-01` to `2026-09-30` (33 continuous calendar months).
- **Historical Cutoff Date**: `2026-09-30`. No actual transaction in `data/` exists after this date.
- **Hidden Future Holdout Period**: `2026-10-01` to `2026-12-31` (Q4 2026). Stored strictly inside `validation/future_holdout/`.

### B. Prediction & Holdout Evaluation Concept
```
Historical Training / Validation Data
[2024-01-01 ──────────────────────── 2026-09-30]
                                            │
                                            │ UNIVA Prediction Module generates forecast
                                            ▼
                                [2026-10-01 ── 2026-12-31]
                                            ▲
                                            │ Evaluated against hidden holdout
                                            │
                             validation/future_holdout/
                             actual_sales_q4_2026.csv
```
This enables authentic evaluation of prediction accuracy (MAPE, RMSE, Forecast Bias) without leaking future ground truth into historical training datasets.

---

## 4. Key Embedded Business Patterns & Messiness

1. **Seasonality**:
   - **Appliances / Fans**: High summer surge between March and June (+65% to +70% demand).
   - **Lighting**: Autumn festive surge during Diwali in October/November (+35% to +45% demand).
   - **Wires & Cables**: Peak construction season in Q1 and early summer, monsoon dip in July/August.
2. **Dynamic Pricing & Inflation**:
   - Copper raw material surge on `2025-02-01` (+15% purchase cost, +12% selling price).
   - LED panel manufacturing deflation on `2025-07-01` (-10% purchase cost, -8% selling price).
3. **Realistic Credit & Payment Delays**:
   - Prompt cash/UPI counter customers settle immediately.
   - B2B contractors on Net 30/45 experience varied delay profiles (early, on-time, late, overdue).
4. **Supply Chain Disruption**:
   - Occasional supplier delivery delays of 1 to 5 days.
   - Partial goods receipts and quarantined damaged returns.
5. **Product & Customer Lifecycle**:
   - Older incandescent 60W bulbs (`PRD-009`) phased out on `2024-06-30`.
   - Inactive customer accounts (`C-VIVE`) with zero transactions past exit date.
   - New high-efficiency BLDC fans (`PRD-011`) launched on `2024-03-01`.

---

## 5. Running Generators & Validators

### Re-generating Data:
```bash
python synthetic_micro_enterprise/generator/generate_micro_enterprise.py
python synthetic_micro_enterprise/generator/generate_metadata.py
```

### Running Validation Test Suite:
```bash
python synthetic_micro_enterprise/validation/validate_relationships.py
python synthetic_micro_enterprise/validation/validate_temporal_integrity.py
python synthetic_micro_enterprise/validation/validate_business_rules.py
```
*(All 3 validators pass with 100% relational integrity, zero date leakage, and exact arithmetic consistency).*
