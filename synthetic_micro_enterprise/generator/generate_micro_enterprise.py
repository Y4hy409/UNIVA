"""
Vidyut Electricals & Power Solutions - Synthetic Micro-Enterprise Data Generator
Generates a complete, relational, temporally consistent, and forecasting-ready business ecosystem.
Historical Range: 2024-01-01 to 2026-09-30 (33 Months)
Future Holdout Range: 2026-10-01 to 2026-12-31 (Q4 2026)
"""

import os
import csv
import json
import random
import math
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Tuple

SEED = 42
random.seed(SEED)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MASTER_DIR = os.path.join(DATA_DIR, "master")
SALES_DIR = os.path.join(DATA_DIR, "sales")
PROC_DIR = os.path.join(DATA_DIR, "procurement")
INV_DIR = os.path.join(DATA_DIR, "inventory")
FIN_DIR = os.path.join(DATA_DIR, "finance")
OPS_DIR = os.path.join(DATA_DIR, "operations")
PRICE_DIR = os.path.join(DATA_DIR, "pricing")
MKTG_DIR = os.path.join(DATA_DIR, "marketing")
KNOW_DIR = os.path.join(DATA_DIR, "knowledge")
META_DIR = os.path.join(BASE_DIR, "metadata")
VAL_DIR = os.path.join(BASE_DIR, "validation")
HOLDOUT_DIR = os.path.join(VAL_DIR, "future_holdout")

for d in [MASTER_DIR, SALES_DIR, PROC_DIR, INV_DIR, FIN_DIR, OPS_DIR, PRICE_DIR, MKTG_DIR, KNOW_DIR, META_DIR, VAL_DIR, HOLDOUT_DIR]:
    os.makedirs(d, exist_ok=True)

START_DATE = date(2024, 1, 1)
CUTOFF_DATE = date(2026, 9, 30)
HOLDOUT_END_DATE = date(2026, 12, 31)

def write_csv(filepath: str, headers: List[str], rows: List[List[Any]]):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {os.path.basename(filepath)}: {len(rows)} rows.")

def dstr(d: date) -> str:
    return d.strftime("%Y-%m-%d")

# =============================================================================
# 1. MASTER DATA GENERATION
# =============================================================================

# Branches
branches_data = [
    ["BR-01", "HQ-CHN", "Vidyut Central Hub & Showroom", "Chennai", "Parrys Corner, George Town", "Hub & Retail", "2021-04-01", "Active"],
    ["BR-02", "BLR-EC", "Vidyut Electronic City Retail Branch", "Bangalore", "Electronic City Phase 1", "Retail Outlet", "2023-01-15", "Active"],
    ["BR-03", "CBE-TH", "Vidyut Coimbatore Townhall Branch", "Coimbatore", "Town Hall Cross Cut Road", "Retail Outlet", "2023-08-01", "Active"]
]

# Employees
employees_data = [
    ["EMP-001", "VK-01", "Venkatesh Kumar", "Managing Director", "BR-01", "2021-04-01", "", "Active"],
    ["EMP-002", "RS-02", "Ravi Shankar", "Branch Manager", "BR-01", "2021-06-15", "", "Active"],
    ["EMP-003", "AN-03", "Anand Natarajan", "Senior Sales Executive", "BR-01", "2021-08-01", "", "Active"],
    ["EMP-004", "PM-04", "Priya Mohan", "Accountant & Billing", "BR-01", "2022-02-10", "", "Active"],
    ["EMP-005", "KR-05", "Karthik Rajan", "Warehouse Supervisor", "BR-01", "2021-05-01", "", "Active"],
    ["EMP-006", "SK-06", "Suresh Kumar", "Branch Manager", "BR-02", "2023-01-10", "", "Active"],
    ["EMP-007", "DS-07", "Deepak Sharma", "Sales Executive", "BR-02", "2023-02-01", "", "Active"],
    ["EMP-008", "MV-08", "Meera Venkat", "Billing Clerk", "BR-02", "2023-03-15", "", "Active"],
    ["EMP-009", "GB-09", "Ganesh Balaji", "Branch Manager", "BR-03", "2023-07-20", "", "Active"],
    ["EMP-010", "SP-10", "Santhosh Pandian", "Sales Executive", "BR-03", "2023-08-01", "", "Active"],
    ["EMP-011", "RM-11", "Ramesh Murugan", "Field Electrician Support", "BR-01", "2022-06-01", "2025-04-30", "Exited"],
    ["EMP-012", "LK-12", "Lavanya Krishnan", "Junior Sales Associate", "BR-03", "2024-05-15", "", "Active"]
]

# Suppliers
suppliers_data = [
    ["SUP-001", "LUM-01", "Lumina Lighting Ltd", "Mumbai", "Maharashtra", "+91 98201 12345", "Net 30", 5, "2021-04-01", "Active"],
    ["SUP-002", "ORB-02", "Orbit Wires & Cables Corp", "Ahmedabad", "Gujarat", "+91 97240 54321", "Net 45", 8, "2021-04-15", "Active"],
    ["SUP-003", "MAX-03", "MaxVolt Modular Switchgear", "Hyderabad", "Telangana", "+91 98490 67890", "Net 30", 4, "2021-05-01", "Active"],
    ["SUP-004", "ZEP-04", "Zephyr Fans & Appliances", "Kolkata", "West Bengal", "+91 98300 98765", "Net 60", 12, "2022-01-10", "Active"],
    ["SUP-005", "ELE-05", "ElectroSafe Switchgear & MCBs", "Chennai", "Tamil Nadu", "+91 94440 11223", "Net 15", 3, "2021-06-01", "Active"],
    ["SUP-006", "KRD-06", "Kiran Distribution & Conduit Supplies", "Bangalore", "Karnataka", "+91 98860 33445", "Net 30", 6, "2022-08-15", "Active"],
    ["SUP-007", "ECO-07", "EcoGlow Solar & LED Panels", "Pune", "Maharashtra", "+91 98500 55667", "Advance 50%", 10, "2023-03-01", "Active"],
    ["SUP-008", "VAP-08", "Vardhman Electrical Accessories", "Delhi", "Delhi", "+91 98110 77889", "Net 30", 7, "2021-04-01", "Active"]
]

# Products Master (38 SKUs)
products_raw = [
    # ID, SKU, Name, Category, Subcategory, Brand, Unit, Purchase_Price, Selling_Price, Reorder_Level, Reorder_Qty, Tax_Rate, Launch_Date, Disc_Date, Status
    ["PRD-001", "LED-BULB-09W", "EcoGlow LED Bulb 9W Cool Day White", "Lighting", "LED Bulbs", "EcoGlow", "NOS", 42.0, 75.0, 150, 400, 18.0, "2021-04-01", "", "Active"],
    ["PRD-002", "LED-BULB-12W", "EcoGlow LED Bulb 12W Cool Day White", "Lighting", "LED Bulbs", "EcoGlow", "NOS", 58.0, 110.0, 100, 300, 18.0, "2021-04-01", "", "Active"],
    ["PRD-003", "LED-BULB-18W", "Lumina Ultra Bright 18W LED Bulb", "Lighting", "LED Bulbs", "Lumina", "NOS", 95.0, 175.0, 60, 200, 18.0, "2022-01-15", "", "Active"],
    ["PRD-004", "LED-BAT-20W", "Lumina Slimline 20W LED Batten Tube Light", "Lighting", "Tube Lights", "Lumina", "NOS", 145.0, 240.0, 80, 250, 18.0, "2021-06-01", "", "Active"],
    ["PRD-005", "LED-BAT-36W", "Lumina Commercial 36W LED Batten Light", "Lighting", "Tube Lights", "Lumina", "NOS", 280.0, 450.0, 40, 120, 18.0, "2022-03-10", "", "Active"],
    ["PRD-006", "LED-PNL-15W", "EcoGlow 15W Slim Round Downlight Panel", "Lighting", "Panel Lights", "EcoGlow", "NOS", 160.0, 280.0, 50, 150, 18.0, "2022-05-01", "", "Active"],
    ["PRD-007", "LED-PNL-24W", "EcoGlow 24W 2x2 Square Ceiling Panel", "Lighting", "Panel Lights", "EcoGlow", "NOS", 520.0, 850.0, 30, 80, 18.0, "2023-01-20", "", "Active"],
    ["PRD-008", "LED-FL-50W", "Lumina Outdoor 50W Waterproof Flood Light", "Lighting", "Outdoor Lights", "Lumina", "NOS", 650.0, 1100.0, 20, 50, 18.0, "2023-04-10", "", "Active"],
    ["PRD-009", "INC-BLB-60W", "Classic 60W Incandescent Filament Bulb", "Lighting", "Incandescent", "Vardhman", "NOS", 12.0, 22.0, 0, 0, 18.0, "2021-04-01", "2024-06-30", "Discontinued"],
    
    # Fans
    ["PRD-010", "FAN-CEIL-1200", "Zephyr Breeze 1200mm High Speed Ceiling Fan", "Appliances", "Ceiling Fans", "Zephyr", "NOS", 1350.0, 2150.0, 40, 100, 18.0, "2021-04-01", "", "Active"],
    ["PRD-011", "FAN-BLDC-1200", "Zephyr Smart Eco BLDC 1200mm 28W Fan", "Appliances", "Ceiling Fans", "Zephyr", "NOS", 2200.0, 3450.0, 25, 60, 18.0, "2024-03-01", "", "Active"],
    ["PRD-012", "FAN-EXH-150", "Zephyr FreshAir 150mm Kitchen Exhaust Fan", "Appliances", "Exhaust Fans", "Zephyr", "NOS", 620.0, 1050.0, 30, 75, 18.0, "2021-08-15", "", "Active"],
    ["PRD-013", "FAN-WALL-400", "Zephyr High Airflow 400mm Wall Fan", "Appliances", "Wall Fans", "Zephyr", "NOS", 1480.0, 2350.0, 20, 50, 18.0, "2022-02-20", "", "Active"],
    
    # Switches & Sockets
    ["PRD-014", "SW-MOD-6A", "MaxVolt Alpha 6A 1-Way Modular Switch", "Switches", "Modular Switches", "MaxVolt", "NOS", 18.0, 35.0, 300, 800, 18.0, "2021-04-01", "", "Active"],
    ["PRD-015", "SW-MOD-16A", "MaxVolt Alpha 16A Power Switch", "Switches", "Modular Switches", "MaxVolt", "NOS", 42.0, 78.0, 150, 400, 18.0, "2021-04-01", "", "Active"],
    ["PRD-016", "SOC-MOD-6A", "MaxVolt 3-Pin 6A Shuttered Safety Socket", "Switches", "Modular Sockets", "MaxVolt", "NOS", 36.0, 68.0, 200, 500, 18.0, "2021-04-01", "", "Active"],
    ["PRD-017", "SOC-MOD-16A", "MaxVolt 6/16A Universal Power Socket", "Switches", "Modular Sockets", "MaxVolt", "NOS", 65.0, 115.0, 120, 300, 18.0, "2021-04-01", "", "Active"],
    ["PRD-018", "REG-MOD-FAN", "MaxVolt 4-Step Capacitive Fan Regulator", "Switches", "Regulators", "MaxVolt", "NOS", 140.0, 240.0, 60, 150, 18.0, "2021-06-10", "", "Active"],
    ["PRD-019", "PLT-MOD-4M", "MaxVolt 4-Module Sleek White Faceplate", "Switches", "Plates", "MaxVolt", "NOS", 48.0, 90.0, 100, 250, 18.0, "2021-04-01", "", "Active"],
    ["PRD-020", "PLT-MOD-8M", "MaxVolt 8-Module Double Row Faceplate", "Switches", "Plates", "MaxVolt", "NOS", 85.0, 155.0, 80, 200, 18.0, "2021-04-01", "", "Active"],
    
    # Wires & Cables
    ["PRD-021", "WIR-FR-100", "Orbit FlexiSafe 1.0 sq mm Copper Wire (90m)", "Wires & Cables", "Building Wires", "Orbit", "COIL", 880.0, 1320.0, 40, 100, 18.0, "2021-04-01", "", "Active"],
    ["PRD-022", "WIR-FR-150", "Orbit FlexiSafe 1.5 sq mm Copper Wire (90m)", "Wires & Cables", "Building Wires", "Orbit", "COIL", 1250.0, 1850.0, 50, 120, 18.0, "2021-04-01", "", "Active"],
    ["PRD-023", "WIR-FR-250", "Orbit FlexiSafe 2.5 sq mm Copper Wire (90m)", "Wires & Cables", "Building Wires", "Orbit", "COIL", 1950.0, 2850.0, 45, 100, 18.0, "2021-04-01", "", "Active"],
    ["PRD-024", "WIR-FR-400", "Orbit HeavyDuty 4.0 sq mm Copper Wire (90m)", "Wires & Cables", "Building Wires", "Orbit", "COIL", 3100.0, 4450.0, 25, 60, 18.0, "2021-07-01", "", "Active"],
    ["PRD-025", "WIR-FR-600", "Orbit MainLine 6.0 sq mm Copper Wire (90m)", "Wires & Cables", "Building Wires", "Orbit", "COIL", 4600.0, 6500.0, 15, 40, 18.0, "2022-01-10", "", "Active"],
    ["PRD-026", "CBL-ARM-4C10", "Orbit Armoured 4-Core 10 sq mm Underground Cable", "Wires & Cables", "Power Cables", "Orbit", "MTR", 185.0, 260.0, 100, 300, 18.0, "2022-08-01", "", "Active"],
    
    # Switchgear & Protection
    ["PRD-027", "MCB-SP-10A", "ElectroSafe 10A Single Pole C-Curve MCB", "Switchgear", "MCBs", "ElectroSafe", "NOS", 82.0, 145.0, 80, 200, 18.0, "2021-04-01", "", "Active"],
    ["PRD-028", "MCB-SP-16A", "ElectroSafe 16A Single Pole C-Curve MCB", "Switchgear", "MCBs", "ElectroSafe", "NOS", 85.0, 150.0, 100, 250, 18.0, "2021-04-01", "", "Active"],
    ["PRD-029", "MCB-SP-32A", "ElectroSafe 32A Single Pole Heavy Duty MCB", "Switchgear", "MCBs", "ElectroSafe", "NOS", 95.0, 170.0, 70, 180, 18.0, "2021-04-01", "", "Active"],
    ["PRD-030", "MCB-DP-32A", "ElectroSafe 32A Double Pole Main Isolator MCB", "Switchgear", "MCBs", "ElectroSafe", "NOS", 220.0, 380.0, 35, 90, 18.0, "2021-05-15", "", "Active"],
    ["PRD-031", "RCCB-4P-40A", "ElectroSafe 40A 4-Pole 30mA Earth Leakage RCCB", "Switchgear", "RCCBs", "ElectroSafe", "NOS", 1250.0, 2100.0, 15, 40, 18.0, "2022-04-01", "", "Active"],
    ["PRD-032", "DB-SPN-08W", "ElectroSafe 8-Way SPN Metal Enclosure Distribution Board", "Switchgear", "Distribution Boards", "ElectroSafe", "NOS", 450.0, 780.0, 20, 50, 18.0, "2021-09-01", "", "Active"],
    ["PRD-033", "DB-TPN-04W", "ElectroSafe 4-Way TPN Vertical Phase DB", "Switchgear", "Distribution Boards", "ElectroSafe", "NOS", 1650.0, 2650.0, 10, 25, 18.0, "2022-11-01", "", "Active"],
    
    # Accessories & Conduits
    ["PRD-034", "EXT-SPIKE-4W", "Vardhman 4-Socket 2M Surge Protector Spike Strip", "Accessories", "Extension Strips", "Vardhman", "NOS", 210.0, 360.0, 40, 100, 18.0, "2021-04-01", "", "Active"],
    ["PRD-035", "CON-PVC-25MM", "Kiran Rigid PVC 25mm Electrical Conduit Pipe (3m)", "Accessories", "Conduits", "Kiran", "NOS", 38.0, 65.0, 200, 500, 18.0, "2021-04-01", "", "Active"],
    ["PRD-036", "TAP-ELEC-BLK", "Vardhman Heavy Duty Insulation Tape Roll Black", "Accessories", "Tapes", "Vardhman", "NOS", 7.5, 15.0, 300, 1000, 18.0, "2021-04-01", "", "Active"],
    ["PRD-037", "LUG-COP-16MM", "Vardhman Tinned Copper Cable Lugs 16mm (Pack 50)", "Accessories", "Lugs & Terminals", "Vardhman", "PKT", 140.0, 240.0, 25, 60, 18.0, "2022-05-10", "", "Active"],
    ["PRD-038", "TST-VOLT-DIG", "MaxVolt Digital AC Voltage & Continuity Tester Pen", "Accessories", "Testing Tools", "MaxVolt", "NOS", 90.0, 165.0, 30, 80, 18.0, "2023-06-01", "", "Active"]
]

# Customers (48 Customers with realistic B2B/B2C profiles)
customers_raw = [
    # ID, Code, Name, Type, Phone, Email, City, Area, State, Since, Credit_Allowed, Credit_Limit, Payment_Terms, Status, Inactive_Date
    ["CUST-001", "C-BALA", "Balaji Electrical Contractors", "Contractor", "98401 22334", "balaji.electricals@gmail.com", "Chennai", "T. Nagar", "Tamil Nadu", "2021-04-05", True, 250000.0, "Net 30", "Active", ""],
    ["CUST-002", "C-KALA", "Kalaivani Hardware & Paints", "Retailer / Trader", "98412 33445", "kalaivanitraders@yahoo.com", "Chennai", "Tambaram", "Tamil Nadu", "2021-04-10", True, 150000.0, "Net 15", "Active", ""],
    ["CUST-003", "C-SARV", "Saravana Electric Works (Govindaraj)", "Electrician", "94440 98765", "", "Chennai", "Mylapore", "Tamil Nadu", "2021-04-15", True, 50000.0, "Net 15", "Active", ""],
    ["CUST-004", "C-SRIR", "Sri Ramakrishna Builders & Infra", "Builder / Commercial", "98400 11998", "purchase@sriraminfra.in", "Chennai", "OMR Kandanchavadi", "Tamil Nadu", "2021-06-01", True, 500000.0, "Net 45", "Active", ""],
    ["CUST-005", "C-MURA", "Murugan Auto Garage & Works", "Small Commercial", "98840 55443", "murugan.garage@outlook.com", "Chennai", "Ambattur Industrial Estate", "Tamil Nadu", "2021-07-20", False, 0.0, "Immediate Cash", "Active", ""],
    ["CUST-006", "C-PRIY", "Dr. Priya Sundaram (Home Clinic)", "Residential / B2C", "98402 77665", "drpriya.s@gmail.com", "Chennai", "Anna Nagar", "Tamil Nadu", "2021-08-12", False, 0.0, "Immediate UPI", "Active", ""],
    ["CUST-007", "C-TECH", "TechPark Facility Maintenance Team", "Institution", "98841 88990", "fm.chennai@techparkhub.com", "Chennai", "Siruseri IT Park", "Tamil Nadu", "2021-09-01", True, 300000.0, "Net 30", "Active", ""],
    ["CUST-008", "C-ANBU", "Anbu Electricals (Anbazhagan)", "Electrician", "94451 23456", "", "Chennai", "Chromepet", "Tamil Nadu", "2021-11-05", True, 30000.0, "Net 7", "Active", ""],
    ["CUST-009", "C-DEVI", "Devi Agency & Lighting Store", "Retailer / Trader", "98418 66778", "deviagencychn@gmail.com", "Chennai", "Perambur", "Tamil Nadu", "2022-01-10", True, 180000.0, "Net 30", "Active", ""],
    ["CUST-010", "C-VELS", "Vels Vidyashram School Campus", "Institution", "98409 44332", "admin@velscampus.edu.in", "Chennai", "Pallavaram", "Tamil Nadu", "2022-02-18", True, 100000.0, "Net 30", "Active", ""],
    ["CUST-011", "C-VICT", "Victory Housing Projects Phase 2", "Builder / Commercial", "98404 99001", "accounts@victoryhousing.com", "Chennai", "Porur", "Tamil Nadu", "2022-04-05", True, 400000.0, "Net 45", "Active", ""],
    ["CUST-012", "C-KART", "Karthik Residential Apartment Owner", "Residential / B2C", "98844 11223", "karthik.r91@gmail.com", "Chennai", "Adyar", "Tamil Nadu", "2022-05-20", False, 0.0, "Immediate Card", "Active", ""],
    ["CUST-013", "C-METR", "Metro Supermarket Tambaram", "Small Commercial", "98415 55667", "tambaram@metrosupermarket.in", "Chennai", "Tambaram West", "Tamil Nadu", "2022-07-15", True, 80000.0, "Net 15", "Active", ""],
    ["CUST-014", "C-SIVA", "Siva Shankaran (Individual Home)", "Residential / B2C", "94441 66778", "siva.shankaran@gmail.com", "Chennai", "Velachery", "Tamil Nadu", "2022-09-10", False, 0.0, "Immediate Cash", "Active", ""],
    ["CUST-015", "C-SRIN", "Srinivasan & Sons Contractor", "Contractor", "98405 33221", "srini_contractor@rediffmail.com", "Chennai", "Kodambakkam", "Tamil Nadu", "2022-11-01", True, 200000.0, "Net 30", "Active", ""],
    ["CUST-016", "C-ROYA", "Royal Comfort Residency Hotel", "Small Commercial", "98847 77889", "maintenance@royalcomfort.in", "Chennai", "Egmore", "Tamil Nadu", "2023-01-10", True, 120000.0, "Net 30", "Active", ""],
    ["CUST-017", "C-APEX", "Apex Manufacturing Solutions", "Small Commercial", "98410 88221", "facility@apexmanufacturing.com", "Chennai", "Guindy Industrial Estate", "Tamil Nadu", "2023-02-15", True, 350000.0, "Net 30", "Active", ""],
    ["CUST-018", "C-LAKS", "Lakshmi Vilas Sweets & Bakery", "Small Commercial", "98403 44556", "", "Chennai", "Triplicane", "Tamil Nadu", "2023-04-01", False, 0.0, "Immediate UPI", "Active", ""],
    ["CUST-019", "C-POOM", "Poompuhar Handicrafts Store", "Small Commercial", "98848 11990", "poompuhar.chn@gov.in", "Chennai", "Mount Road", "Tamil Nadu", "2023-05-15", True, 60000.0, "Net 30", "Active", ""],
    ["CUST-020", "C-SELV", "Selvam Electrician Services", "Electrician", "94452 77889", "", "Chennai", "Saidapet", "Tamil Nadu", "2023-06-20", True, 40000.0, "Net 15", "Active", ""],
    ["CUST-021", "C-MOHD", "Mohammed Riyaz (Home Renovation)", "Residential / B2C", "98416 33221", "riyaz.m@hotmail.com", "Chennai", "Royapettah", "Tamil Nadu", "2023-08-10", False, 0.0, "Immediate Cash", "Active", ""],
    ["CUST-022", "C-GLOB", "Global Smart Solutions (P) Ltd", "Contractor", "98406 22110", "procurement@globalsmart.com", "Chennai", "Sholinganallur", "Tamil Nadu", "2023-10-05", True, 300000.0, "Net 30", "Active", ""],
    ["CUST-023", "C-KALA2", "Kalam Brothers Electrical Store", "Retailer / Trader", "98411 99887", "kalambrothers@gmail.com", "Chennai", "Washermanpet", "Tamil Nadu", "2023-11-20", True, 100000.0, "Net 15", "Active", ""],
    ["CUST-024", "C-VIVE", "Vivek Enterprises (Old Partner)", "Retailer / Trader", "98407 11445", "vivek.ent@vsnl.com", "Chennai", "Sowcarpet", "Tamil Nadu", "2021-04-01", True, 100000.0, "Net 30", "Inactive", "2024-03-31"],

    # Bangalore Customers (BR-02)
    ["CUST-025", "C-BLR1", "Brigade Vista Apartment Owners Assn", "Residential / B2C", "98860 11223", "rwa@brigadevista.in", "Bangalore", "Electronic City Phase 1", "Karnataka", "2023-01-20", True, 150000.0, "Net 30", "Active", ""],
    ["CUST-026", "C-BLR2", "Manjunatha Electrical Works", "Electrician", "97400 44556", "", "Bangalore", "BTM Layout", "Karnataka", "2023-02-10", True, 60000.0, "Net 15", "Active", ""],
    ["CUST-027", "C-BLR3", "InnoTech Coworking Hub", "Small Commercial", "99000 88990", "facilities@innotechhub.com", "Bangalore", "HSR Layout", "Karnataka", "2023-03-01", True, 200000.0, "Net 30", "Active", ""],
    ["CUST-028", "C-BLR4", "Sri Venkateshwara Hardware & Electricals", "Retailer / Trader", "98450 77889", "svhardwaresblr@gmail.com", "Bangalore", "Bommasandra", "Karnataka", "2023-04-15", True, 250000.0, "Net 30", "Active", ""],
    ["CUST-029", "C-BLR5", "Raghavendra Infrastructure Developers", "Builder / Commercial", "99450 22334", "raghavendra.infra@gmail.com", "Bangalore", "Whitefield", "Karnataka", "2023-06-01", True, 450000.0, "Net 45", "Active", ""],
    ["CUST-030", "C-BLR6", "Dr. Arvind Rao Dental Clinic", "Small Commercial", "98862 33445", "dr.arvind@raodental.com", "Bangalore", "Koramangala", "Karnataka", "2023-07-20", False, 0.0, "Immediate UPI", "Active", ""],
    ["CUST-031", "C-BLR7", "Nandini Milk Parlour & Mart", "Small Commercial", "94480 66778", "", "Bangalore", "Jayanagar", "Karnataka", "2023-09-05", False, 0.0, "Immediate Cash", "Active", ""],
    ["CUST-032", "C-BLR8", "Cauvery Engineering Contractors", "Contractor", "98455 11998", "purchase@cauveryengg.in", "Bangalore", "Peenya Industrial Area", "Karnataka", "2023-10-15", True, 300000.0, "Net 30", "Active", ""],
    ["CUST-033", "C-BLR9", "Suresh Babu (Villa Construction)", "Residential / B2C", "98866 55443", "sureshbabu.blr@yahoo.com", "Bangalore", "Sarjapur Road", "Karnataka", "2024-01-10", False, 0.0, "Immediate Card", "Active", ""],
    ["CUST-034", "C-BLR10", "Silicon Valley PG Hostel Chain", "Institution", "99001 77665", "admin@siliconpghostels.com", "Bangalore", "Electronic City Phase 2", "Karnataka", "2024-02-15", True, 120000.0, "Net 30", "Active", ""],
    ["CUST-035", "C-BLR11", "Gowda Electrical Repairs", "Electrician", "94482 99001", "", "Bangalore", "Bannerghatta Road", "Karnataka", "2024-04-01", True, 35000.0, "Net 7", "Active", ""],
    ["CUST-036", "C-BLR12", "Urban Spaces Interior Studio", "Contractor", "98452 44332", "design@urbanspaces.in", "Bangalore", "Indiranagar", "Karnataka", "2024-06-10", True, 200000.0, "Net 30", "Active", ""],

    # Coimbatore Customers (BR-03)
    ["CUST-037", "C-CBE1", "Kovai Textile Mills Facility Team", "Small Commercial", "98422 11223", "electrical@kovaitextiles.com", "Coimbatore", "Peelamedu", "Tamil Nadu", "2023-08-05", True, 350000.0, "Net 30", "Active", ""],
    ["CUST-038", "C-CBE2", "Marutham Electrical & Power Agency", "Retailer / Trader", "98430 33445", "marutham.cbe@gmail.com", "Coimbatore", "Gandhipuram", "Tamil Nadu", "2023-08-20", True, 200000.0, "Net 15", "Active", ""],
    ["CUST-039", "C-CBE3", "Rangasamy Electrician Workshop", "Electrician", "94430 55667", "", "Coimbatore", "R.S. Puram", "Tamil Nadu", "2023-09-10", True, 45000.0, "Net 15", "Active", ""],
    ["CUST-040", "C-CBE4", "Sri Krishna Engineering College Hostel", "Institution", "98425 77889", "estate@srikrishnaengg.edu", "Coimbatore", "Kuniyamuthur", "Tamil Nadu", "2023-10-01", True, 180000.0, "Net 30", "Active", ""],
    ["CUST-041", "C-CBE5", "Kongu Builders & Real Estate", "Builder / Commercial", "98433 99001", "kongubuilderscbe@gmail.com", "Coimbatore", "Avinashi Road", "Tamil Nadu", "2023-11-15", True, 400000.0, "Net 45", "Active", ""],
    ["CUST-042", "C-CBE6", "Velan Pump & Motor Spares Store", "Retailer / Trader", "98428 44556", "velanpumpscbe@rediffmail.com", "Coimbatore", "Ganapathy", "Tamil Nadu", "2024-01-05", True, 120000.0, "Net 15", "Active", ""],
    ["CUST-043", "C-CBE7", "Sundaram Hospital Maintenance", "Institution", "98431 88990", "maintenance@sundaramhospital.org", "Coimbatore", "Saibaba Colony", "Tamil Nadu", "2024-02-20", True, 150000.0, "Net 30", "Active", ""],
    ["CUST-044", "C-CBE8", "Mani Bros Electricals (Mani)", "Electrician", "94435 22334", "", "Coimbatore", "Singanallur", "Tamil Nadu", "2024-03-15", True, 40000.0, "Net 7", "Active", ""],
    ["CUST-045", "C-CBE9", "Karthika Departmental Store", "Small Commercial", "98426 66778", "", "Coimbatore", "Thudiyalur", "Tamil Nadu", "2024-05-01", False, 0.0, "Immediate Cash", "Active", ""],
    ["CUST-046", "C-CBE10", "Annamalai Agro Processing Unit", "Small Commercial", "98438 11990", "accounts@annamalaiagro.in", "Coimbatore", "Pollachi Road", "Tamil Nadu", "2024-06-15", True, 220000.0, "Net 30", "Active", ""],
    ["CUST-047", "C-CBE11", "Kovai Elite Residency Hotel", "Small Commercial", "98420 77665", "admin@kovaielite.com", "Coimbatore", "Race Course Road", "Tamil Nadu", "2024-07-10", True, 90000.0, "Net 30", "Active", ""],
    ["CUST-048", "C-CBE12", "Ramachandran (Individual House Owner)", "Residential / B2C", "94438 33221", "ramachandran.cbe@gmail.com", "Coimbatore", "Vadavalli", "Tamil Nadu", "2024-08-01", False, 0.0, "Immediate UPI", "Active", ""]
]

print("Writing master tables...")
write_csv(os.path.join(MASTER_DIR, "branches.csv"), ["branch_id", "branch_code", "branch_name", "city", "area", "branch_type", "opening_date", "status"], branches_data)
write_csv(os.path.join(MASTER_DIR, "employees.csv"), ["employee_id", "employee_code", "employee_name", "role", "branch_id", "joining_date", "exit_date", "status"], employees_data)
write_csv(os.path.join(MASTER_DIR, "suppliers.csv"), ["supplier_id", "supplier_code", "supplier_name", "city", "state", "contact", "payment_terms", "lead_time_days", "supplier_since", "status"], suppliers_data)
write_csv(os.path.join(MASTER_DIR, "products.csv"), ["product_id", "sku", "product_name", "category", "subcategory", "brand", "unit", "purchase_price", "selling_price", "reorder_level", "reorder_quantity", "tax_rate", "launch_date", "discontinued_date", "status"], products_raw)
write_csv(os.path.join(MASTER_DIR, "customers.csv"), ["customer_id", "customer_code", "customer_name", "customer_type", "phone", "email", "city", "area", "state", "customer_since", "credit_allowed", "credit_limit", "payment_terms", "status", "inactive_date"], customers_raw)

# Map helpers
product_map = {p[0]: p for p in products_raw}
customer_map = {c[0]: c for c in customers_raw}
supplier_map = {s[0]: s for s in suppliers_data}

# Assign primary branch to customers based on city
cust_branch_map = {}
for c in customers_raw:
    cid = c[0]
    city = c[6]
    if city == "Chennai":
        cust_branch_map[cid] = "BR-01"
    elif city == "Bangalore":
        cust_branch_map[cid] = "BR-02"
    else:
        cust_branch_map[cid] = "BR-03"

# =============================================================================
# 2. PRICING & PROMOTIONS HISTORY
# =============================================================================
# Copper price surge in Q1 2025 (+15%), LED bulb price drop in mid 2025 (-10%)
price_history_rows = []
for p in products_raw:
    pid = p[0]
    p_price = float(p[7])
    s_price = float(p[8])
    l_date = p[12]
    # Initial price
    price_history_rows.append([f"PH-{len(price_history_rows)+1:04d}", pid, p[1], l_date, p_price, s_price, "Initial Launch Catalog Price", "Approved"])
    
    if "WIR-" in p[1] or "CBL-" in p[1]:
        # Raw copper escalation on 2025-02-01
        new_p = round(p_price * 1.15, 2)
        new_s = round(s_price * 1.12, 2)
        price_history_rows.append([f"PH-{len(price_history_rows)+1:04d}", pid, p[1], "2025-02-01", new_p, new_s, "Copper Commodity Global Price Surge Revision", "Approved"])
    elif "LED-BULB" in p[1] or "LED-BAT" in p[1]:
        # Manufacturing efficiency drop on 2025-07-01
        new_p = round(p_price * 0.90, 2)
        new_s = round(s_price * 0.92, 2)
        price_history_rows.append([f"PH-{len(price_history_rows)+1:04d}", pid, p[1], "2025-07-01", new_p, new_s, "LED Semiconductor Cost Reduction Revision", "Approved"])

write_csv(os.path.join(PRICE_DIR, "product_price_history.csv"), ["price_change_id", "product_id", "sku", "effective_date", "purchase_price", "selling_price", "change_reason", "approval_status"], price_history_rows)

# Promotions
promotions_data = [
    ["PROMO-001", "Diwali Festive Lighting Mega Sale 2024", "2024-10-15", "2024-11-05", "Lighting", 10.0, "Bulk purchase discount on LED bulbs and panel lights", "BR-01,BR-02,BR-03", "Completed"],
    ["PROMO-002", "Summer Cooling Fan Festival 2024", "2024-04-01", "2024-05-31", "Appliances", 8.0, "Special installer discount on ceiling and exhaust fans", "BR-01,BR-02,BR-03", "Completed"],
    ["PROMO-003", "Monsoon Contractor Wire Bonanza 2024", "2024-07-01", "2024-08-15", "Wires & Cables", 5.0, "5% instant rebate on purchases above 5 coils", "BR-01", "Completed"],
    ["PROMO-004", "New Year Renovation Special 2025", "2025-01-01", "2025-01-20", "Switches", 7.5, "Discount on modular plates and sockets combo", "BR-01,BR-02,BR-03", "Completed"],
    ["PROMO-005", "Summer Cooling Fan Extravaganza 2025", "2025-03-15", "2025-05-31", "Appliances", 10.0, "Heavy discount on Zephyr BLDC smart fans", "BR-01,BR-02,BR-03", "Completed"],
    ["PROMO-006", "Diwali Grand Sparkle Lighting 2025", "2025-10-10", "2025-11-02", "Lighting", 12.0, "Flat 12% off on 10+ LED batten and downlight packs", "BR-01,BR-02,BR-03", "Completed"],
    ["PROMO-007", "Summer Cooling Beat-The-Heat 2026", "2026-03-20", "2026-05-31", "Appliances", 12.0, "Early summer fan discount & free tester pen", "BR-01,BR-02,BR-03", "Completed"],
    ["PROMO-008", "Independence Contractor Appreciation 2026", "2026-08-01", "2026-08-20", "Wires & Cables", 6.0, "Special loyalty points + 6% discount on Orbit wires", "BR-01,BR-02,BR-03", "Completed"],
    # Holdout promo (Q4 2026)
    ["PROMO-009", "Diwali Light-Up Festival 2026", "2026-10-15", "2026-11-05", "Lighting", 15.0, "High discount festive LED promotion", "BR-01,BR-02,BR-03", "Scheduled"]
]
write_csv(os.path.join(MKTG_DIR, "promotions.csv"), ["promo_id", "promo_name", "start_date", "end_date", "target_category", "discount_pct", "description", "eligible_branches", "status"], promotions_data[:8])

# =============================================================================
# 3. TEMPORAL TRANSACTION SIMULATION ENGINE
# =============================================================================

# Seasonality multipliers per category by month (1 to 12)
seasonality = {
    "Lighting":     {1: 0.95, 2: 0.90, 3: 0.90, 4: 0.90, 5: 0.95, 6: 0.90, 7: 0.95, 8: 1.05, 9: 1.15, 10: 1.45, 11: 1.35, 12: 1.05}, # Festive peak Oct-Nov
    "Appliances":   {1: 0.75, 2: 0.90, 3: 1.35, 4: 1.65, 5: 1.70, 6: 1.30, 7: 0.95, 8: 0.80, 9: 0.85, 10: 0.90, 11: 0.80, 12: 0.75}, # Summer fan peak Mar-Jun
    "Wires & Cables":{1: 1.00, 2: 1.10, 3: 1.20, 4: 1.15, 5: 1.05, 6: 0.85, 7: 0.80, 8: 0.90, 9: 1.10, 10: 1.15, 11: 1.10, 12: 1.05},# Construction cycle
    "Switches":     {1: 1.00, 2: 1.05, 3: 1.10, 4: 1.10, 5: 1.05, 6: 0.95, 7: 0.90, 8: 1.00, 9: 1.10, 10: 1.20, 11: 1.15, 12: 1.05},
    "Switchgear":   {1: 0.95, 2: 1.05, 3: 1.15, 4: 1.10, 5: 1.00, 6: 0.90, 7: 0.85, 8: 0.95, 9: 1.05, 10: 1.15, 11: 1.10, 12: 1.00},
    "Accessories":  {1: 0.95, 2: 0.95, 3: 1.05, 4: 1.05, 5: 1.00, 6: 0.95, 7: 0.95, 8: 1.00, 9: 1.05, 10: 1.15, 11: 1.10, 12: 1.00}
}

# General YoY growth trend factor (2024 = 1.00, 2025 = 1.14, 2026 = 1.28)
def get_growth_factor(d: date) -> float:
    days_since_start = (d - START_DATE).days
    return 1.0 + (0.13 * (days_since_start / 365.0))

print("Simulating procurement, sales, inventory, and finance over time...")

sales_orders = []
sales_order_items = []
invoices = []
customer_payments = []
sales_returns = []
credit_notes = []

purchase_orders = []
purchase_order_items = []
goods_receipts = []
goods_receipt_items = []

inventory_openings = []
inventory_movements = []
stock_transfers = []
stock_adjustments = []

expenses = []
cash_transactions = []
deliveries = []
salesperson_targets = []

# Initialize opening balances for all active products across 3 branches
curr_stock = {b[0]: {p[0]: 0 for p in products_raw} for b in branches_data}

for b in branches_data:
    bid = b[0]
    for p in products_raw:
        pid = p[0]
        if p[14] == "Discontinued":
            init_qty = 50 if bid == "BR-01" else 15
        else:
            init_qty = random.randint(100, 350) if bid == "BR-01" else random.randint(30, 120)
        curr_stock[bid][pid] = init_qty
        unit_cost = float(p[7])
        inventory_openings.append([
            f"OB-{bid}-{pid}",
            "2024-01-01",
            bid,
            pid,
            p[1],
            init_qty,
            unit_cost,
            round(init_qty * unit_cost, 2),
            "Annual Physical Stock Opening Count 2024"
        ])

# Generate monthly targets for active salespeople
salespeople = [e for e in employees_data if "Sales" in e[3] or "Manager" in e[3]]

curr_month = date(2024, 1, 1)
while curr_month <= HOLDOUT_END_DATE:
    m_str = curr_month.strftime("%Y-%m")
    m_end = (curr_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    for sp in salespeople:
        base_target = 350000.0 if "Manager" in sp[3] else 220000.0
        if sp[4] == "BR-01":
            base_target *= 1.3
        elif sp[4] == "BR-03":
            base_target *= 0.9
        # Seasonality factor
        base_target *= seasonality["Lighting"].get(curr_month.month, 1.0)
        salesperson_targets.append([
            f"TGT-{sp[0]}-{m_str}",
            sp[0],
            sp[2],
            sp[4],
            m_str,
            dstr(curr_month),
            dstr(m_end),
            round(base_target, 2),
            "Approved Monthly Sales Quota"
        ])
    # Next month
    curr_month = (curr_month.replace(day=28) + timedelta(days=4)).replace(day=1)

# Holdout sales storage
holdout_sales_orders = []
holdout_sales_order_items = []
holdout_invoices = []
holdout_payments = []

so_counter = 1
inv_counter = 1
pay_counter = 1
ret_counter = 1
cn_counter = 1
po_counter = 1
gr_counter = 1
del_counter = 1
exp_counter = 1
csh_counter = 1
mov_counter = 1
trf_counter = 1
adj_counter = 1

# Simulate day by day from 2024-01-01 through 2026-12-31
curr_d = START_DATE
while curr_d <= HOLDOUT_END_DATE:
    is_holdout = (curr_d > CUTOFF_DATE)
    growth = get_growth_factor(curr_d)
    day_of_week = curr_d.weekday() # 0 = Mon, 6 = Sun
    
    # -------------------------------------------------------------
    # A. PROCUREMENT (Purchases placed on regular cadences)
    # -------------------------------------------------------------
    if not is_holdout and day_of_week in [0, 2] and random.random() < 0.65:
        # Place a purchase order to suppliers
        sup = random.choice(suppliers_data)
        sup_id = sup[0]
        sup_lead = int(sup[7])
        exp_d = curr_d + timedelta(days=sup_lead + random.randint(-1, 3))
        
        # Select items from supplier's domain
        sup_prods = [p for p in products_raw if p[5] == sup[2].split()[0] or p[14] == "Active"]
        if not sup_prods:
            sup_prods = [p for p in products_raw if p[14] == "Active"]
        
        selected_prods = random.sample(sup_prods, min(len(sup_prods), random.randint(2, 5)))
        po_id = f"PO-{po_counter:05d}"
        po_counter += 1
        
        po_total = 0.0
        po_items_list = []
        for p in selected_prods:
            qty = random.randint(p[9], p[10] * 2) if p[10] > 0 else 50
            unit_cost = float(p[7])
            line_tot = round(qty * unit_cost, 2)
            po_total += line_tot
            po_items_list.append([f"POI-{len(purchase_order_items)+len(po_items_list)+1:06d}", po_id, p[0], p[1], p[2], qty, unit_cost, line_tot, dstr(exp_d)])
        
        po_status = "Issued" if exp_d > curr_d else "Completed"
        purchase_orders.append([po_id, dstr(curr_d), sup_id, sup[2], "BR-01", round(po_total, 2), dstr(exp_d), po_status, f"PO raised by {employees_data[4][2]}"])
        purchase_order_items.extend(po_items_list)
        
        # Simulate goods receipt upon arrival (receipt_date >= po_date)
        actual_rec_d = exp_d + timedelta(days=random.choice([-1, 0, 0, 1, 2, 4 if random.random() < 0.15 else 0]))
        if actual_rec_d <= CUTOFF_DATE:
            gr_id = f"GRN-{gr_counter:05d}"
            gr_counter += 1
            gr_status = "Received in Full" if random.random() > 0.10 else "Partial Receipt"
            goods_receipts.append([gr_id, po_id, dstr(actual_rec_d), sup_id, "BR-01", employees_data[4][0], gr_status, "Inspected and accepted"])
            for poi in po_items_list:
                rec_qty = poi[5] if gr_status == "Received in Full" else int(poi[5] * 0.8)
                goods_receipt_items.append([f"GRI-{len(goods_receipt_items)+1:06d}", gr_id, poi[2], poi[3], poi[5], rec_qty, "Good Condition", dstr(actual_rec_d)])
                # Update inventory ledger
                curr_stock["BR-01"][poi[2]] += rec_qty
                inventory_movements.append([
                    f"MOV-{mov_counter:07d}", dstr(actual_rec_d), "BR-01", poi[2], poi[3], "PURCHASE_IN", rec_qty, curr_stock["BR-01"][poi[2]], gr_id, f"Inward from {sup[2]}"
                ])
                mov_counter += 1

    # -------------------------------------------------------------
    # B. INTER-BRANCH STOCK TRANSFERS & ADJUSTMENTS
    # -------------------------------------------------------------
    if not is_holdout and day_of_week == 3 and random.random() < 0.40:
        # Transfer stock from Central Hub BR-01 to retail outlets BR-02 or BR-03
        dest_branch = random.choice(["BR-02", "BR-03"])
        prod = random.choice([p for p in products_raw if p[14] == "Active"])
        pid = prod[0]
        if curr_stock["BR-01"][pid] > 40:
            trf_qty = random.randint(15, 35)
            curr_stock["BR-01"][pid] -= trf_qty
            curr_stock[dest_branch][pid] += trf_qty
            trf_id = f"TRF-{trf_counter:05d}"
            trf_counter += 1
            stock_transfers.append([trf_id, dstr(curr_d), "BR-01", dest_branch, pid, prod[1], trf_qty, employees_data[4][0], "Completed", "Branch Replenishment"])
            inventory_movements.append([f"MOV-{mov_counter:07d}", dstr(curr_d), "BR-01", pid, prod[1], "TRANSFER_OUT", -trf_qty, curr_stock["BR-01"][pid], trf_id, f"Transferred to {dest_branch}"])
            mov_counter += 1
            inventory_movements.append([f"MOV-{mov_counter:07d}", dstr(curr_d), dest_branch, pid, prod[1], "TRANSFER_IN", trf_qty, curr_stock[dest_branch][pid], trf_id, f"Received from BR-01"])
            mov_counter += 1

    # Occasional stock damage / adjustment (0.05 probability per week)
    if not is_holdout and random.random() < 0.03:
        adj_b = random.choice(branches_data)[0]
        adj_p = random.choice(products_raw)
        adj_pid = adj_p[0]
        if curr_stock[adj_b][adj_pid] > 10:
            adj_qty = -random.randint(1, 4) # Damaged in transit or mishandled
            curr_stock[adj_b][adj_pid] += adj_qty
            adj_id = f"ADJ-{adj_counter:05d}"
            adj_counter += 1
            stock_adjustments.append([adj_id, dstr(curr_d), adj_b, adj_pid, adj_p[1], adj_qty, "Damaged / Broken in Showroom", employees_data[1][0], "Approved"])
            inventory_movements.append([f"MOV-{mov_counter:07d}", dstr(curr_d), adj_b, adj_pid, adj_p[1], "ADJUSTMENT_DAMAGE", adj_qty, curr_stock[adj_b][adj_pid], adj_id, "Physical stock adjustment"])
            mov_counter += 1

    # -------------------------------------------------------------
    # C. SALES ORDERS & BILLING
    # -------------------------------------------------------------
    if day_of_week != 6: # Store open Mon-Sat
        num_orders_today = random.randint(3, 8) if not is_holdout else random.randint(4, 9)
        for _ in range(num_orders_today):
            # Select customer
            cust = random.choice(customers_raw)
            cid = cust[0]
            c_since = datetime.strptime(cust[9], "%Y-%m-%d").date()
            if curr_d < c_since:
                continue
            if cust[13] == "Inactive" and cust[14] and curr_d > datetime.strptime(cust[14], "%Y-%m-%d").date():
                continue
            
            c_branch = cust_branch_map[cid]
            c_type = cust[3]
            
            # Select products based on customer type
            if "Contractor" in c_type or "Builder" in c_type:
                p_pool = [p for p in products_raw if p[3] in ["Wires & Cables", "Switchgear", "Switches", "Lighting"] and p[14] == "Active"]
                num_items = random.randint(3, 7)
            elif "Electrician" in c_type:
                p_pool = [p for p in products_raw if p[3] in ["Switches", "Switchgear", "Accessories", "Lighting"] and p[14] == "Active"]
                num_items = random.randint(2, 5)
            elif "Retailer" in c_type:
                p_pool = [p for p in products_raw if p[14] == "Active"]
                num_items = random.randint(4, 8)
            else: # B2C
                p_pool = [p for p in products_raw if p[3] in ["Lighting", "Appliances", "Accessories"] and p[14] == "Active"]
                num_items = random.randint(1, 3)
            
            order_items = random.sample(p_pool, min(len(p_pool), num_items))
            order_id = f"SO-{so_counter:06d}"
            inv_id = f"INV-{inv_counter:06d}"
            so_counter += 1
            inv_counter += 1
            
            order_subtotal = 0.0
            order_tax = 0.0
            line_items = []
            
            for prod in order_items:
                pid = prod[0]
                cat = prod[3]
                season_mult = seasonality.get(cat, {}).get(curr_d.month, 1.0)
                
                # Base order quantity
                if "Contractor" in c_type or "Builder" in c_type:
                    qty = int(random.randint(5, 25) * season_mult)
                elif "Retailer" in c_type:
                    qty = int(random.randint(10, 40) * season_mult)
                elif "Electrician" in c_type:
                    qty = int(random.randint(2, 12) * season_mult)
                else:
                    qty = int(random.randint(1, 3) * season_mult)
                qty = max(1, qty)
                
                # Check price at effective date
                price = float(prod[8])
                if ("WIR-" in prod[1] or "CBL-" in prod[1]) and curr_d >= date(2025, 2, 1):
                    price = round(price * 1.12, 2)
                elif ("LED-BULB" in prod[1] or "LED-BAT" in prod[1]) and curr_d >= date(2025, 7, 1):
                    price = round(price * 0.92, 2)
                
                # Check promotion discount
                disc_pct = 0.0
                for promo in promotions_data:
                    p_st = datetime.strptime(promo[2], "%Y-%m-%d").date()
                    p_en = datetime.strptime(promo[3], "%Y-%m-%d").date()
                    if p_st <= curr_d <= p_en and (promo[4] == cat or promo[4] == "All"):
                        disc_pct = float(promo[5])
                        break
                
                final_unit_price = round(price * (1.0 - (disc_pct / 100.0)), 2)
                line_total = round(qty * final_unit_price, 2)
                tax_amt = round(line_total * (float(prod[11]) / 100.0), 2)
                
                order_subtotal += line_total
                order_tax += tax_amt
                
                item_row = [
                    f"SOI-{len(sales_order_items)+len(line_items)+1:07d}",
                    order_id,
                    dstr(curr_d),
                    pid,
                    prod[1],
                    prod[2],
                    prod[3],
                    qty,
                    price,
                    disc_pct,
                    final_unit_price,
                    line_total,
                    tax_amt
                ]
                line_items.append(item_row)
                
                # Update stock and ledger for historical records
                if not is_holdout:
                    curr_stock[c_branch][pid] = max(0, curr_stock[c_branch][pid] - qty)
                    inventory_movements.append([
                        f"MOV-{mov_counter:07d}", dstr(curr_d), c_branch, pid, prod[1], "SALE_OUT", -qty, curr_stock[c_branch][pid], inv_id, f"Sold on {inv_id}"
                    ])
                    mov_counter += 1
            
            order_grand_total = round(order_subtotal + order_tax, 2)
            
            # Sales rep
            branch_emps = [e for e in employees_data if e[4] == c_branch and ("Sales" in e[3] or "Manager" in e[3])]
            sales_rep = random.choice(branch_emps)[0] if branch_emps else employees_data[0][0]
            
            order_row = [
                order_id,
                dstr(curr_d),
                cid,
                cust[2],
                c_type,
                c_branch,
                sales_rep,
                round(order_subtotal, 2),
                round(order_tax, 2),
                order_grand_total,
                "Invoiced"
            ]
            
            # Invoice: invoice_date = order_date, due_date based on payment terms
            p_terms = cust[12]
            if "Net 15" in p_terms:
                due_d = curr_d + timedelta(days=15)
            elif "Net 30" in p_terms:
                due_d = curr_d + timedelta(days=30)
            elif "Net 45" in p_terms:
                due_d = curr_d + timedelta(days=45)
            elif "Net 7" in p_terms:
                due_d = curr_d + timedelta(days=7)
            else:
                due_d = curr_d
            
            inv_row = [
                inv_id,
                order_id,
                dstr(curr_d),
                dstr(due_d),
                cid,
                cust[2],
                c_branch,
                round(order_subtotal, 2),
                round(order_tax, 2),
                order_grand_total,
                p_terms,
                "Unpaid"
            ]
            
            # Simulate Customer Payment
            # Prompt payers vs late payers
            if "Immediate" in p_terms:
                pay_d = curr_d
                pay_mode = "UPI" if "UPI" in p_terms else ("Credit Card" if "Card" in p_terms else "Cash")
                pay_amt = order_grand_total
                inv_row[11] = "Paid"
                pay_row = [f"PAY-{pay_counter:06d}", inv_id, order_id, cid, dstr(pay_d), pay_amt, pay_mode, f"Ref-{pay_counter*1001}", "Settled on Billing"]
                pay_counter += 1
                if not is_holdout:
                    customer_payments.append(pay_row)
                    # Record cash transaction
                    cash_transactions.append([f"CSH-{csh_counter:06d}", dstr(pay_d), c_branch, "INFLOW", "Customer Payment", pay_amt, pay_mode, inv_id, f"Receipt from {cust[2]}"])
                    csh_counter += 1
                else:
                    holdout_payments.append(pay_row)
            else: # Credit terms
                # Customer payment delay profile
                delay_days = random.choice([
                    random.randint(5, 14), # early
                    random.randint(15, 30), # on time
                    random.randint(31, 55), # slightly late
                    random.randint(60, 95) if random.random() < 0.15 else random.randint(15, 30) # overdue
                ])
                pay_d = curr_d + timedelta(days=delay_days)
                
                # Check if payment happens before cutoff
                if pay_d <= (CUTOFF_DATE if not is_holdout else HOLDOUT_END_DATE):
                    inv_row[11] = "Paid"
                    pay_amt = order_grand_total
                    pay_mode = random.choice(["NEFT / Bank Transfer", "Cheque", "RTGS", "UPI"])
                    pay_row = [f"PAY-{pay_counter:06d}", inv_id, order_id, cid, dstr(pay_d), pay_amt, pay_mode, f"UTR-{pay_counter*8899}", f"Credit Settlement {p_terms}"]
                    pay_counter += 1
                    if not is_holdout:
                        customer_payments.append(pay_row)
                        cash_transactions.append([f"CSH-{csh_counter:06d}", dstr(pay_d), c_branch, "INFLOW", "Customer Payment", pay_amt, pay_mode, inv_id, f"Bank Settlement from {cust[2]}"])
                        csh_counter += 1
                    else:
                        holdout_payments.append(pay_row)
                else:
                    # Still open / pending payment
                    if curr_d + timedelta(days=delay_days) > (CUTOFF_DATE if not is_holdout else HOLDOUT_END_DATE):
                        inv_row[11] = "Overdue" if (CUTOFF_DATE if not is_holdout else HOLDOUT_END_DATE) > due_d else "Pending"
            
            # Delivery record (for orders requiring delivery)
            if "Contractor" in c_type or "Builder" in c_type or "Institution" in c_type:
                del_prom_d = curr_d + timedelta(days=random.randint(1, 3))
                del_act_d = del_prom_d + timedelta(days=random.choice([0, 0, 0, 1, 2 if random.random() < 0.1 else 0]))
                del_status = "Delivered" if del_act_d <= (CUTOFF_DATE if not is_holdout else HOLDOUT_END_DATE) else "In Transit"
                del_row = [
                    f"DEL-{del_counter:06d}",
                    order_id,
                    inv_id,
                    cid,
                    c_branch,
                    dstr(curr_d),
                    dstr(del_prom_d),
                    dstr(del_act_d) if del_status == "Delivered" else "",
                    del_status,
                    "Vidyut Logistics Delivery Van"
                ]
                del_counter += 1
                if not is_holdout:
                    deliveries.append(del_row)

            # Occasional Sales Return (1.5% probability for B2C/electricians)
            if not is_holdout and random.random() < 0.015 and line_items:
                ret_item = random.choice(line_items)
                ret_qty = min(ret_item[7], random.randint(1, 2))
                ret_amt = round(ret_qty * ret_item[10], 2)
                ret_d = curr_d + timedelta(days=random.randint(2, 7))
                if ret_d <= CUTOFF_DATE:
                    ret_id = f"RET-{ret_counter:05d}"
                    cn_id = f"CN-{cn_counter:05d}"
                    ret_counter += 1
                    cn_counter += 1
                    sales_returns.append([ret_id, inv_id, order_id, cid, dstr(ret_d), ret_item[3], ret_item[4], ret_qty, ret_amt, "Defective / Voltage Flickering", "Approved"])
                    credit_notes.append([cn_id, ret_id, inv_id, cid, dstr(ret_d), ret_amt, "Credit Note Issued for Defective Replacement", "Adjusted"])
                    # Return to stock / quarantined
                    inventory_movements.append([f"MOV-{mov_counter:07d}", dstr(ret_d), c_branch, ret_item[3], ret_item[4], "CUSTOMER_RETURN_IN", ret_qty, curr_stock[c_branch][ret_item[3]], ret_id, "Customer Return Quarantined"])
                    mov_counter += 1

            if not is_holdout:
                sales_orders.append(order_row)
                sales_order_items.extend(line_items)
                invoices.append(inv_row)
            else:
                holdout_sales_orders.append(order_row)
                holdout_sales_order_items.extend(line_items)
                holdout_invoices.append(inv_row)

    # -------------------------------------------------------------
    # D. OPERATIONAL & RECURRING EXPENSES
    # -------------------------------------------------------------
    if not is_holdout:
        # Monthly Rent on 1st of month
        if curr_d.day == 1:
            for b in branches_data:
                bid = b[0]
                rent_amt = 75000.0 if bid == "BR-01" else (45000.0 if bid == "BR-02" else 35000.0)
                exp_id = f"EXP-{exp_counter:06d}"
                exp_counter += 1
                expenses.append([exp_id, dstr(curr_d), bid, "Rent", rent_amt, "Monthly Commercial Showroom Lease Rent", "Bank Transfer", "Paid"])
                cash_transactions.append([f"CSH-{csh_counter:06d}", dstr(curr_d), bid, "OUTFLOW", "Showroom Rent", rent_amt, "Bank Transfer", exp_id, f"Rent for {b[2]}"])
                csh_counter += 1
        
        # Monthly Salaries on 5th of month
        if curr_d.day == 5:
            for b in branches_data:
                bid = b[0]
                b_emps = [e for e in employees_data if e[4] == bid and e[7] == "Active"]
                sal_tot = len(b_emps) * 32000.0
                exp_id = f"EXP-{exp_counter:06d}"
                exp_counter += 1
                expenses.append([exp_id, dstr(curr_d), bid, "Salaries", sal_tot, f"Staff Monthly Payroll ({len(b_emps)} Employees)", "Bank Transfer", "Paid"])
                cash_transactions.append([f"CSH-{csh_counter:06d}", dstr(curr_d), bid, "OUTFLOW", "Payroll Salaries", sal_tot, "Bank Transfer", exp_id, f"Salary Payout {bid}"])
                csh_counter += 1
        
        # Utility bills on 10th
        if curr_d.day == 10:
            for b in branches_data:
                bid = b[0]
                eb_amt = round(random.uniform(8500, 16500), 2)
                exp_id = f"EXP-{exp_counter:06d}"
                exp_counter += 1
                expenses.append([exp_id, dstr(curr_d), bid, "Electricity & Utilities", eb_amt, "TANGEDCO / BESCOM Commercial Electricity Bill", "Online Banking", "Paid"])
                cash_transactions.append([f"CSH-{csh_counter:06d}", dstr(curr_d), bid, "OUTFLOW", "Electricity Bill", eb_amt, "Online Banking", exp_id, "Utility Payment"])
                csh_counter += 1

        # Periodic misc operational expenses (Tea, transport, delivery van fuel, printer paper)
        if random.random() < 0.25:
            b_exp = random.choice(branches_data)[0]
            misc_cat = random.choice(["Vehicle Fuel & Freight", "Office Supplies & Printing", "Staff Refreshments & Tea", "Minor Maintenance & Repair"])
            misc_amt = round(random.uniform(350, 2400), 2)
            exp_id = f"EXP-{exp_counter:06d}"
            exp_counter += 1
            expenses.append([exp_id, dstr(curr_d), b_exp, misc_cat, misc_amt, "Operational petty cash expense", "Cash / UPI", "Paid"])
            cash_transactions.append([f"CSH-{csh_counter:06d}", dstr(curr_d), b_exp, "OUTFLOW", misc_cat, misc_amt, "Petty Cash", exp_id, "Operational expense"])
            csh_counter += 1

    curr_d += timedelta(days=1)

print(f"Total historical sales orders: {len(sales_orders)}")
print(f"Total historical sales items: {len(sales_order_items)}")
print(f"Total holdout future orders (Q4 2026): {len(holdout_sales_orders)}")

# =============================================================================
# 4. WRITE ALL DATASET FILES
# =============================================================================

# Sales
write_csv(os.path.join(SALES_DIR, "sales_orders.csv"), ["order_id", "order_date", "customer_id", "customer_name", "customer_type", "branch_id", "salesperson_id", "subtotal", "tax_amount", "grand_total", "order_status"], sales_orders)
write_csv(os.path.join(SALES_DIR, "sales_order_items.csv"), ["order_item_id", "order_id", "order_date", "product_id", "sku", "product_name", "category", "quantity", "unit_price", "discount_pct", "final_price", "line_total", "tax_amount"], sales_order_items)
write_csv(os.path.join(SALES_DIR, "invoices.csv"), ["invoice_id", "order_id", "invoice_date", "due_date", "customer_id", "customer_name", "branch_id", "subtotal", "tax_amount", "grand_total", "payment_terms", "payment_status"], invoices)
write_csv(os.path.join(SALES_DIR, "customer_payments.csv"), ["payment_id", "invoice_id", "order_id", "customer_id", "payment_date", "amount_paid", "payment_mode", "reference_number", "notes"], customer_payments)
write_csv(os.path.join(SALES_DIR, "sales_returns.csv"), ["return_id", "invoice_id", "order_id", "customer_id", "return_date", "product_id", "sku", "quantity_returned", "refund_amount", "reason", "status"], sales_returns)
write_csv(os.path.join(SALES_DIR, "credit_notes.csv"), ["credit_note_id", "return_id", "invoice_id", "customer_id", "credit_note_date", "credit_amount", "reason", "status"], credit_notes)

# Procurement
write_csv(os.path.join(PROC_DIR, "purchase_orders.csv"), ["po_id", "po_date", "supplier_id", "supplier_name", "destination_branch", "total_amount", "expected_delivery_date", "status", "notes"], purchase_orders)
write_csv(os.path.join(PROC_DIR, "purchase_order_items.csv"), ["po_item_id", "po_id", "product_id", "sku", "product_name", "quantity_ordered", "unit_cost", "line_total", "expected_date"], purchase_order_items)
write_csv(os.path.join(PROC_DIR, "goods_receipts.csv"), ["receipt_id", "po_id", "receipt_date", "supplier_id", "receiving_branch", "received_by_employee_id", "inspection_status", "remarks"], goods_receipts)
write_csv(os.path.join(PROC_DIR, "goods_receipt_items.csv"), ["receipt_item_id", "receipt_id", "product_id", "sku", "quantity_ordered", "quantity_received", "condition_status", "receipt_date"], goods_receipt_items)

# Inventory
write_csv(os.path.join(INV_DIR, "inventory_opening_balances.csv"), ["balance_id", "balance_date", "branch_id", "product_id", "sku", "quantity_on_hand", "unit_cost", "total_valuation", "notes"], inventory_openings)
write_csv(os.path.join(INV_DIR, "inventory_movements.csv"), ["movement_id", "movement_date", "branch_id", "product_id", "sku", "movement_type", "quantity_change", "running_balance", "reference_doc_id", "description"], inventory_movements)
write_csv(os.path.join(INV_DIR, "stock_transfers.csv"), ["transfer_id", "transfer_date", "from_branch", "to_branch", "product_id", "sku", "quantity_transferred", "authorized_by", "transfer_status", "notes"], stock_transfers)
write_csv(os.path.join(INV_DIR, "stock_adjustments.csv"), ["adjustment_id", "adjustment_date", "branch_id", "product_id", "sku", "quantity_adjusted", "reason", "approved_by", "status"], stock_adjustments)

# Finance
write_csv(os.path.join(FIN_DIR, "expenses.csv"), ["expense_id", "expense_date", "branch_id", "category", "amount", "description", "payment_mode", "status"], expenses)
write_csv(os.path.join(FIN_DIR, "cash_transactions.csv"), ["transaction_id", "transaction_date", "branch_id", "flow_type", "category", "amount", "payment_channel", "reference_id", "narration"], cash_transactions)

# Operations
write_csv(os.path.join(OPS_DIR, "deliveries.csv"), ["delivery_id", "order_id", "invoice_id", "customer_id", "branch_id", "order_date", "promised_date", "actual_delivery_date", "delivery_status", "vehicle_info"], deliveries)
write_csv(os.path.join(OPS_DIR, "salesperson_targets.csv"), ["target_id", "salesperson_id", "salesperson_name", "branch_id", "target_month", "period_start", "period_end", "target_amount", "status"], salesperson_targets)

# Future Holdout (Q4 2026 for evaluation of prediction accuracy)
write_csv(os.path.join(HOLDOUT_DIR, "actual_sales_q4_2026.csv"), ["order_id", "order_date", "customer_id", "customer_name", "customer_type", "branch_id", "salesperson_id", "subtotal", "tax_amount", "grand_total", "order_status"], holdout_sales_orders)
write_csv(os.path.join(HOLDOUT_DIR, "actual_sales_items_q4_2026.csv"), ["order_item_id", "order_id", "order_date", "product_id", "sku", "product_name", "category", "quantity", "unit_price", "discount_pct", "final_price", "line_total", "tax_amount"], holdout_sales_order_items)

# =============================================================================
# 5. BUSINESS KNOWLEDGE DOCUMENTS (RAG / SOPs)
# =============================================================================
knowledge_docs = {
    "company_profile.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
Company Overview & Enterprise Profile

1. Business Identity
Company Name: Vidyut Electricals & Power Solutions
Legal Structure: Partnership Firm (MSME Registered)
Founders: Venkatesh Kumar & Ravi Shankar
Established: April 1, 2021
Headquarters: 48, Armenian Street, Parrys Corner, George Town, Chennai - 600001, Tamil Nadu
GSTIN: 33AABFV1234F1Z8

2. Core Business Activity
Vidyut Electricals is an authorized wholesale distributor and retail stockist of electrical wiring, industrial switchgear, modular switches, LED lighting fixtures, and residential/commercial ventilation fans across South India.

3. Operational Branches
- Chennai Central Hub & Showroom (Parrys Corner, George Town, Chennai - 600001)
- Bangalore Retail Outlet (Electronic City Phase 1, Bangalore - 560100)
- Coimbatore Townhall Branch (Cross Cut Road, Coimbatore - 641001)

4. Customer Segments
- Licensed Electrical Contractors (Building projects, factories, villas)
- Certified Electricians & Technicians
- Regional Electrical & Hardware Retailers
- Commercial Institutions & IT Facilities
- Walk-in Residential Homeowners

5. Authorized Distribution Partnerships
- Orbit Wires & Cables Corp (Copper building wires, power cables)
- MaxVolt Switchgear (Modular switches, sockets, regulators)
- ElectroSafe Switchgear (MCBs, RCCBs, Distribution Boards)
- Zephyr Fans & Appliances (Ceiling, exhaust, and wall fans)
- EcoGlow & Lumina Lighting (LED bulbs, panels, tube lights, floodlights)
""",

    "sales_policy.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
STANDARD SALES & PRICING POLICY
Document Ref: POL-SALES-2024-V2
Effective Date: 2024-01-01 (Updated 2025-07-01)

1. Sales Quotations & Validity
- Written quotations issued to contractors and institutions remain valid for 15 calendar days from issuance.
- Copper wire and underground cable prices are subject to global commodity market escalation. If raw copper rates increase by over 5%, revised rates apply immediately upon written notice.

2. Minimum Order Quantities (MOQ)
- Building Wires (Orbit 90m coils): Minimum order 2 coils per size.
- PVC Conduits (25mm): Minimum bundle of 10 pipes.
- Modular Switches & Sockets: Box quantities (Pack of 20 units) for contractor pricing.

3. Applicable GST Rates
- All lighting, switches, cables, switchgear, and fans attract 18.0% GST under HSN Chapter 85.
- Tax invoices are generated electronically and sent via SMS/Email to registered customers upon dispatch.

4. Sales Channels
- Showroom Counter Billing (Cash, UPI, Point of Sale Card)
- B2B Contractor Credit Dispatch (Delivery challan followed by tax invoice)
- Telephone & WhatsApp Business Order Bookings
""",

    "credit_policy.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
CREDIT MANAGEMENT & CUSTOMER CREDIT LIMIT POLICY
Document Ref: POL-CREDIT-2024-V1
Effective Date: 2024-01-01 (Revision Approved by Managing Partner)

1. Credit Eligibility Criteria
- Credit facilities are strictly extended only to Registered Contractors, Builders, Institutions, and verified Retailers with at least 3 completed cash/advance transactions.
- Walk-in residential customers are not eligible for credit facilities.

2. Standard Payment Terms & Credit Limits
- Category A (Tier-1 Builders & Commercial Contractors): Net 45 Days, Credit Limit up to Rs. 5,00,000.
- Category B (General Electrical Contractors & Retailers): Net 30 Days, Credit Limit up to Rs. 2,50,000.
- Category C (Individual Licensed Electricians): Net 7 to Net 15 Days, Credit Limit up to Rs. 50,000.

3. Overdue Penalties & Account Freezing
- Invoices remaining unpaid 15 days past due date (e.g. Day 46 on Net 30 terms) will incur interest of 1.5% per month.
- Fresh sales dispatches are automatically frozen if total outstanding exceeds 110% of approved credit limit or if any invoice is unpaid past 60 days.

4. Approved Credit Exceptions
- Credit limit increases exceeding Rs. 50,000 require written sign-off from Venkatesh Kumar (Managing Director).
""",

    "return_policy.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
GOODS RETURN, DEFECT REPLACEMENT & RESTOCKING POLICY
Document Ref: POL-RET-2024-V1
Effective Date: 2024-01-01

1. Return Window
- Customers may return unopened, undamaged items in original packaging within 14 days of invoice date.
- Return requests must be accompanied by the original Tax Invoice copy.

2. Non-Returnable Items
- Custom-cut wires, underground cables cut to specific lengths from drums.
- Items damaged due to wrong wiring, electrical short circuits, or lightning surges.
- Discontinued or clearance clearance stock.

3. Defective Goods Replacement Under Manufacturer Warranty
- LED Bulbs & Panels: 2 Years Over-the-Counter Replacement Warranty against driver failure or flickering.
- Zephyr Fans: 2 Years On-Site Manufacturer Service Warranty.
- ElectroSafe MCBs/RCCBs: 3 Years Free Replacement for trip coil failures.

4. Credit Notes
- Approved returns will receive a Credit Note (CN) credited against the customer's ledger account. Cash refunds are issued only for original cash counter sales.
""",

    "inventory_policy.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
INVENTORY MANAGEMENT, STOCK AUDIT & REORDER POLICY
Document Ref: POL-INV-2024-V1
Effective Date: 2024-01-01

1. Inventory Valuation Method
- Inventory is tracked and valued on a Weighted Average Cost (WAC) basis in accordance with Indian Accounting Standards.

2. Reorder Levels & Stockout Prevention
- Fast-Moving SKUs (9W LED Bulbs, 1.5/2.5 sq mm Wires, 6A Switches, 16A MCBs): Minimum 2 weeks buffer stock must be maintained at Central Hub (BR-01).
- Reorder triggers are initiated automatically when stock levels fall below designated Reorder Level (RL).

3. Physical Stock Verification Cadence
- Monthly cycle count of Top 10 High-Value SKUs (Wires and Distribution Panels).
- Full Annual Physical Stocktake conducted on March 31 of each financial year.

4. Inter-Branch Stock Replenishment
- Bangalore (BR-02) and Coimbatore (BR-03) branches receive weekly consolidated supply transfers from the Chennai Central Hub (BR-01) every Thursday.
""",

    "procurement_policy.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
SUPPLIER PROCUREMENT & LEAD TIME MANAGEMENT
Document Ref: POL-PROC-2024-V1
Effective Date: 2024-01-01

1. Supplier Selection & Approved Vendor List (AVL)
- Purchases must only be placed with manufacturers and primary distributors listed on the Approved Vendor List.
- All incoming goods must undergo sample inspection by the Warehouse In-Charge (Karthik Rajan) prior to Goods Receipt Note (GRN) generation.

2. Standard Supplier Payment Terms
- Lumina Lighting: Net 30 Days
- Orbit Wires: Net 45 Days
- Zephyr Fans: Net 60 Days
- EcoGlow Solar/LED: 50% Advance with Purchase Order, 50% on Delivery

3. Handling Supplier Delivery Delays
- If expected delivery date is breached by more than 5 working days, the purchasing desk must notify branch managers to prioritize alternate stock transfers.
""",

    "payment_terms.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
PAYMENT TERMS & BANKING SPECIFICATIONS

1. Accepted Payment Channels
- NEFT / RTGS / IMPS Bank Transfer
- UPI QR Codes (PhonePe, GooglePay, Paytm for Business)
- Point of Sale (POS) Credit / Debit Cards
- Account Payee Cheques (Subject to 3-day clearance before dispatch for new accounts)
- Cash (Transactions capped at Rs. 1,99,000 per invoice as per Income Tax Section 269ST)

2. Designated Business Bank Account
Account Name: Vidyut Electricals and Power Solutions
Bank: HDFC Bank Ltd
Branch: Parrys Corner Branch, Chennai
Account Number: 50200012345678
IFSC Code: HDFC0000123
Account Type: Current Account
""",

    "branch_operations.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
BRANCH OPERATIONS & TIMINGS GUIDELINE

1. Operating Hours
- Monday to Saturday: 9:30 AM to 8:30 PM
- Sunday: Closed (Except during October Diwali festive season: 10:00 AM to 6:00 PM)

2. Branch Roles & Responsibilities
- Chennai Central Hub (BR-01): Central warehousing, primary supplier receiving, wholesale contractor dispatch, administrative accounts.
- Bangalore Branch (BR-02): Retail sales, local electrician network, IT facility supply.
- Coimbatore Branch (BR-03): Retail sales, textile mill and agricultural motor switchgear supply.

3. Emergency Customer Support
- Dedicated contractor helpline available from 8:00 AM to 9:00 PM for urgent project breakdowns.
""",

    "discount_policy.txt": """VIDYUT ELECTRICALS & POWER SOLUTIONS
CONTRACTOR SLAB DISCOUNTS & REBATE STRUCTURE
Document Ref: POL-DISC-2024-V2
Effective Date: 2024-01-01

1. Annual Volume Rebate Slabs for Contractors
- Annual Billing Rs. 5 Lakhs to Rs. 10 Lakhs: Additional 1.5% Year-End Loyalty Rebate.
- Annual Billing Rs. 10 Lakhs to Rs. 25 Lakhs: Additional 3.0% Year-End Loyalty Rebate.
- Annual Billing > Rs. 25 Lakhs: Additional 4.5% Year-End Loyalty Rebate + Priority Site Delivery.

2. Trade Cash Discounts
- 1.0% Spot Cash Discount is permitted on invoice totals if paid immediately at counter via Cash or UPI for bills exceeding Rs. 10,000.
"""
}

for doc_name, doc_content in knowledge_docs.items():
    doc_path = os.path.join(KNOW_DIR, doc_name)
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(doc_content)
    print(f"Generated knowledge doc: {doc_name}")

print("\nAll datasets and knowledge documents generated successfully.")
