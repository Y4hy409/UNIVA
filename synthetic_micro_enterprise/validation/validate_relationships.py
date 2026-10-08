"""
Vidyut Electricals & Power Solutions - Relational & Foreign Key Integrity Validator
Validates primary keys uniqueness, foreign key references, and absence of orphaned records.
"""

import os
import csv
import sys
from typing import Dict, List, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_csv(rel_path: str) -> List[Dict[str, str]]:
    path = os.path.join(DATA_DIR, rel_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def validate():
    print("=== 1. VALIDATING PRIMARY KEYS & UNIQUENESS ===")
    
    # 1. Master tables
    branches = load_csv("master/branches.csv")
    branch_ids = set(r["branch_id"] for r in branches)
    assert len(branch_ids) == len(branches), "Duplicate branch_id in branches.csv"
    print(f"[PASS] branches.csv: {len(branches)} unique branch IDs.")

    employees = load_csv("master/employees.csv")
    emp_ids = set(r["employee_id"] for r in employees)
    assert len(emp_ids) == len(employees), "Duplicate employee_id in employees.csv"
    print(f"[PASS] employees.csv: {len(employees)} unique employee IDs.")

    suppliers = load_csv("master/suppliers.csv")
    sup_ids = set(r["supplier_id"] for r in suppliers)
    assert len(sup_ids) == len(suppliers), "Duplicate supplier_id in suppliers.csv"
    print(f"[PASS] suppliers.csv: {len(suppliers)} unique supplier IDs.")

    products = load_csv("master/products.csv")
    prod_ids = set(r["product_id"] for r in products)
    assert len(prod_ids) == len(products), "Duplicate product_id in products.csv"
    skus = set(r["sku"] for r in products)
    assert len(skus) == len(products), "Duplicate sku in products.csv"
    print(f"[PASS] products.csv: {len(products)} unique product IDs and SKUs.")

    customers = load_csv("master/customers.csv")
    cust_ids = set(r["customer_id"] for r in customers)
    assert len(cust_ids) == len(customers), "Duplicate customer_id in customers.csv"
    print(f"[PASS] customers.csv: {len(customers)} unique customer IDs.")

    print("\n=== 2. VALIDATING FOREIGN KEY INTEGRITY ===")
    
    # Sales Orders -> Customers, Branches, Employees
    sales_orders = load_csv("sales/sales_orders.csv")
    order_ids = set(r["order_id"] for r in sales_orders)
    assert len(order_ids) == len(sales_orders), "Duplicate order_id in sales_orders.csv"
    
    for so in sales_orders:
        assert so["customer_id"] in cust_ids, f"Invalid customer_id {so['customer_id']} in order {so['order_id']}"
        assert so["branch_id"] in branch_ids, f"Invalid branch_id {so['branch_id']} in order {so['order_id']}"
        assert so["salesperson_id"] in emp_ids, f"Invalid salesperson_id {so['salesperson_id']} in order {so['order_id']}"
    print(f"[PASS] sales_orders.csv: {len(sales_orders)} orders with 100% valid customer, branch, and salesperson FKs.")

    # Sales Order Items -> Sales Orders, Products
    so_items = load_csv("sales/sales_order_items.csv")
    item_ids = set(r["order_item_id"] for r in so_items)
    assert len(item_ids) == len(so_items), "Duplicate order_item_id in sales_order_items.csv"
    for soi in so_items:
        assert soi["order_id"] in order_ids, f"Orphaned line item {soi['order_item_id']} referencing non-existent order {soi['order_id']}"
        assert soi["product_id"] in prod_ids, f"Invalid product_id {soi['product_id']} in line item {soi['order_item_id']}"
    print(f"[PASS] sales_order_items.csv: {len(so_items)} line items with 100% valid order and product FKs.")

    # Invoices -> Sales Orders, Customers, Branches
    invoices = load_csv("sales/invoices.csv")
    inv_ids = set(r["invoice_id"] for r in invoices)
    assert len(inv_ids) == len(invoices), "Duplicate invoice_id in invoices.csv"
    for inv in invoices:
        assert inv["order_id"] in order_ids, f"Invoice {inv['invoice_id']} references invalid order {inv['order_id']}"
        assert inv["customer_id"] in cust_ids, f"Invoice {inv['invoice_id']} references invalid customer {inv['customer_id']}"
        assert inv["branch_id"] in branch_ids, f"Invoice {inv['invoice_id']} references invalid branch {inv['branch_id']}"
    print(f"[PASS] invoices.csv: {len(invoices)} invoices with 100% valid order and customer FKs.")

    # Payments -> Invoices, Orders, Customers
    payments = load_csv("sales/customer_payments.csv")
    pay_ids = set(r["payment_id"] for r in payments)
    assert len(pay_ids) == len(payments), "Duplicate payment_id in customer_payments.csv"
    for p in payments:
        assert p["invoice_id"] in inv_ids, f"Payment {p['payment_id']} references invalid invoice {p['invoice_id']}"
        assert p["customer_id"] in cust_ids, f"Payment {p['payment_id']} references invalid customer {p['customer_id']}"
    print(f"[PASS] customer_payments.csv: {len(payments)} payment receipts with 100% valid invoice FKs.")

    # Purchases -> Suppliers
    pos = load_csv("procurement/purchase_orders.csv")
    po_ids = set(r["po_id"] for r in pos)
    assert len(po_ids) == len(pos), "Duplicate po_id in purchase_orders.csv"
    for po in pos:
        assert po["supplier_id"] in sup_ids, f"PO {po['po_id']} references invalid supplier {po['supplier_id']}"
    print(f"[PASS] purchase_orders.csv: {len(pos)} purchase orders with 100% valid supplier FKs.")

    # Goods Receipts -> POs
    grns = load_csv("procurement/goods_receipts.csv")
    grn_ids = set(r["receipt_id"] for r in grns)
    assert len(grn_ids) == len(grns), "Duplicate receipt_id in goods_receipts.csv"
    for grn in grns:
        assert grn["po_id"] in po_ids, f"GRN {grn['receipt_id']} references invalid PO {grn['po_id']}"
    print(f"[PASS] goods_receipts.csv: {len(grns)} goods receipts with 100% valid PO FKs.")

    # Inventory Movements -> Branches, Products
    movements = load_csv("inventory/inventory_movements.csv")
    for mov in movements:
        assert mov["branch_id"] in branch_ids, f"Movement {mov['movement_id']} references invalid branch {mov['branch_id']}"
        assert mov["product_id"] in prod_ids, f"Movement {mov['movement_id']} references invalid product {mov['product_id']}"
    print(f"[PASS] inventory_movements.csv: {len(movements)} movement records with 100% valid branch and product FKs.")

    print("\nALL RELATIONAL AND FOREIGN KEY CHECKS PASSED WITH 100% INTEGRITY.")

if __name__ == "__main__":
    validate()
