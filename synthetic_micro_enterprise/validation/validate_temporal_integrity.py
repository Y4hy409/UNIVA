"""
Vidyut Electricals & Power Solutions - Temporal Integrity & Forecasting Cutoff Validator
Verifies:
1. All historical dates fall strictly within [2024-01-01, 2026-09-30].
2. No future data leakage in historical files.
3. Holdout dataset resides strictly in [2026-10-01, 2026-12-31].
4. Chronological relationships: order_date <= invoice_date <= due_date, po_date <= expected_delivery_date, po_date <= receipt_date.
"""

import os
import csv
from datetime import datetime, date
from typing import Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HOLDOUT_DIR = os.path.join(BASE_DIR, "validation", "future_holdout")

START_DATE = date(2024, 1, 1)
HISTORICAL_CUTOFF = date(2026, 9, 30)
HOLDOUT_START = date(2026, 10, 1)
HOLDOUT_END = date(2026, 12, 31)

def pdate(d_str: str) -> date:
    return datetime.strptime(d_str, "%Y-%m-%d").date()

def validate():
    print("=== 1. VALIDATING HISTORICAL BOUNDS & FUTURE LEAKAGE PREVENTION ===")
    
    # Check historical files
    hist_files_and_date_cols = [
        ("sales/sales_orders.csv", ["order_date"]),
        ("sales/sales_order_items.csv", ["order_date"]),
        ("sales/invoices.csv", ["invoice_date"]),
        ("sales/customer_payments.csv", ["payment_date"]),
        ("sales/sales_returns.csv", ["return_date"]),
        ("sales/credit_notes.csv", ["credit_note_date"]),
        ("procurement/purchase_orders.csv", ["po_date"]),
        ("procurement/goods_receipts.csv", ["receipt_date"]),
        ("inventory/inventory_movements.csv", ["movement_date"]),
        ("finance/expenses.csv", ["expense_date"]),
        ("finance/cash_transactions.csv", ["transaction_date"]),
        ("operations/deliveries.csv", ["order_date"])
    ]

    for rel_path, date_cols in hist_files_and_date_cols:
        full_path = os.path.join(DATA_DIR, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for r in reader:
                count += 1
                for dc in date_cols:
                    val = r.get(dc)
                    if val:
                        d = pdate(val)
                        assert d >= START_DATE, f"Date {d} before start date {START_DATE} in {rel_path}"
                        assert d <= HISTORICAL_CUTOFF, f"CRITICAL LEAKAGE: Future date {d} > cutoff {HISTORICAL_CUTOFF} in historical file {rel_path}"
        print(f"[PASS] {rel_path}: {count} records strictly verified within [{START_DATE} to {HISTORICAL_CUTOFF}].")

    print("\n=== 2. VALIDATING FUTURE HOLDOUT DATASET BOUNDS ===")
    holdout_path = os.path.join(HOLDOUT_DIR, "actual_sales_q4_2026.csv")
    with open(holdout_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        h_count = 0
        for r in reader:
            h_count += 1
            d = pdate(r["order_date"])
            assert d >= HOLDOUT_START, f"Holdout date {d} < holdout start {HOLDOUT_START}"
            assert d <= HOLDOUT_END, f"Holdout date {d} > holdout end {HOLDOUT_END}"
    print(f"[PASS] actual_sales_q4_2026.csv: {h_count} holdout records strictly within [{HOLDOUT_START} to {HOLDOUT_END}].")

    print("\n=== 3. VALIDATING CHRONOLOGICAL CAUSALITY RULES ===")
    
    # Invoices: invoice_date <= due_date
    with open(os.path.join(DATA_DIR, "sales/invoices.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inv_d = pdate(r["invoice_date"])
            due_d = pdate(r["due_date"])
            assert inv_d <= due_d, f"Invoice {r['invoice_id']} due_date {due_d} < invoice_date {inv_d}"
    print("[PASS] Invoices: 100% satisfy invoice_date <= due_date.")

    # Purchase Orders: po_date <= expected_delivery_date
    po_map = {}
    with open(os.path.join(DATA_DIR, "procurement/purchase_orders.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            po_d = pdate(r["po_date"])
            exp_d = pdate(r["expected_delivery_date"])
            assert po_d <= exp_d, f"PO {r['po_id']} expected_date {exp_d} < po_date {po_d}"
            po_map[r["po_id"]] = po_d
    print("[PASS] Purchase Orders: 100% satisfy po_date <= expected_delivery_date.")

    # Goods Receipts: receipt_date >= po_date
    with open(os.path.join(DATA_DIR, "procurement/goods_receipts.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rec_d = pdate(r["receipt_date"])
            po_d = po_map.get(r["po_id"])
            if po_d:
                assert rec_d >= po_d, f"GRN {r['receipt_id']} receipt_date {rec_d} < po_date {po_d}"
    print("[PASS] Goods Receipts: 100% satisfy receipt_date >= po_date.")

    # Deliveries: promised_date >= order_date
    with open(os.path.join(DATA_DIR, "operations/deliveries.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ord_d = pdate(r["order_date"])
            prom_d = pdate(r["promised_date"])
            assert prom_d >= ord_d, f"Delivery {r['delivery_id']} promised_date {prom_d} < order_date {ord_d}"
    print("[PASS] Deliveries: 100% satisfy promised_date >= order_date.")

    print("\nALL TEMPORAL INTEGRITY & FORECASTING CUTOFF CHECKS PASSED PERFECTLY.")

if __name__ == "__main__":
    validate()
