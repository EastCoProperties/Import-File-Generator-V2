# Import File Builder

This Streamlit app converts an Underwriting Engine output workbook into the blind-offer import file layout.

## Input

Upload the workbook produced by the Underwriting Engine app.

The app looks for a sheet named:

- Offer Model

If that sheet is not found, it uses the first sheet.

## Output Layout

The output sheet is named:

- SAMPLE-IMPORT-LIST

The output uses this exact header order from the provided import template:

Type, First Name, Last Name, Owner Full Name, Company, Address, City, State, Zip, APN, Latitude, Longitude, FIPS, Property Address, Property City, Property State, Property Zip, Property County, Property Size, Short Legal Description, Assessed Value, Market Value, Multiplier, Owner's First Name, Owner's Last Name, 2nd Owner's First Name, 2nd Owner's Last Name, Offer Amount, 2nd Offer Amount, 3rd Offer Amount, Betty Score, TLP Estimate, Hyperlink, Zoning, Offer Accept By, Close Date

## Key Mapping

- Offer Amount = 1st Offer
- 2nd Offer Amount = 2nd Offer
- 3rd Offer Amount = 3rd Offer
- Market Value = Offer MV Used
- Assessed Value = County Assessed Value / Total Market Value
- Property Size = Lot size / Lot Acres / Calc Acreage
- TLP Estimate = original TLP Estimate when available

## Deploy

Upload these files to your GitHub repo root:

- app.py
- requirements.txt
- README.md
- .gitignore

Deploy in Streamlit Cloud with main file path:

- app.py
