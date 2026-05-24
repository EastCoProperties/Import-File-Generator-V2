import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Import File Builder", layout="wide")
st.title("Import File Builder")
st.caption("Convert Underwriting Engine output into the blind-offer import layout.")

IMPORT_HEADERS = ['Type', 'First Name', 'Last Name', 'Owner Full Name', 'Company', 'Address', 'City', 'State', 'Zip', 'APN', 'Latitude', 'Longitude', 'FIPS', 'Property Address', 'Property City', 'Property State', 'Property Zip', 'Property County', 'Property Size', 'Short Legal Description', 'Assessed Value', 'Market Value', 'Multiplier', "Owner's First Name", "Owner's Last Name", "2nd Owner's First Name", "2nd Owner's Last Name", 'Offer Amount', '2nd Offer Amount', '3rd Offer Amount', 'Betty Score', 'TLP Estimate', 'Hyperlink', 'Zoning', 'Offer Accept By', 'Close Date']

def clean_columns(df):
    """Make duplicate source columns unique while preserving the original visible names as much as possible."""
    seen = {}
    new_cols = []
    for col in df.columns:
        base = str(col)
        if base not in seen:
            seen[base] = 0
            new_cols.append(base)
        else:
            seen[base] += 1
            new_cols.append(f"{base}__dup{seen[base]}")
    df.columns = new_cols
    return df

def find_col(df, candidates):
    cols = list(df.columns)
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in cols:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    # partial fallback
    for cand in candidates:
        cand_low = cand.lower()
        for c in cols:
            if cand_low == c.lower().replace("__dup1", ""):
                return c
    return None

def get_series(df, candidates, default=""):
    col = find_col(df, candidates)
    if col is None:
        return pd.Series([default] * len(df), index=df.index)
    return df[col]

def numeric_series(df, candidates):
    s = get_series(df, candidates, default=np.nan)
    return pd.to_numeric(
        pd.Series(s).astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace({"": np.nan, "No Offer": np.nan, "nan": np.nan}),
        errors="coerce"
    )

def make_type(first_name, company):
    first = first_name.fillna("").astype(str).str.strip()
    comp = company.fillna("").astype(str).str.strip()
    return np.where(first.eq("") & comp.ne(""), "Company", np.where(first.eq(""), "Company", "Individual"))

def build_import(df, offer_accept_by="", close_date="", exclude_no_offer=True):
    out = pd.DataFrame(index=df.index)

    first = get_series(df, ["First Name", "Owner 1 First Name", "Owner's First Name"], "")
    last = get_series(df, ["Last Name", "Owner 1 Last Name", "Owner's Last Name"], "")
    owner_full = get_series(df, ["Owner Full Name", "Owner Name(s)", "Owner Name", "Owner"], "")
    company = get_series(df, ["Company"], "")

    # If company is blank and first name is blank, use owner full name as company.
    company_fixed = company.copy()
    blank_company = company_fixed.fillna("").astype(str).str.strip().eq("")
    blank_first = first.fillna("").astype(str).str.strip().eq("")
    company_fixed.loc[blank_company & blank_first] = owner_full.loc[blank_company & blank_first]

    offer1 = numeric_series(df, ["1st Offer", "Offer Amount", "First Offer"])
    offer2 = numeric_series(df, ["2nd Offer", "2nd Offer Amount", "Second Offer"])
    offer3 = numeric_series(df, ["3rd Offer", "3rd Offer Amount", "Third Offer"])

    if exclude_no_offer:
        keep = offer1.notna() & offer2.notna() & offer3.notna()
        df = df.loc[keep].copy()
        first = first.loc[keep]
        last = last.loc[keep]
        owner_full = owner_full.loc[keep]
        company_fixed = company_fixed.loc[keep]
        offer1 = offer1.loc[keep]
        offer2 = offer2.loc[keep]
        offer3 = offer3.loc[keep]
        out = pd.DataFrame(index=df.index)

    out["Type"] = make_type(first, company_fixed)
    out["First Name"] = first
    out["Last Name"] = last
    out["Owner Full Name"] = owner_full
    out["Company"] = company_fixed
    out["Address"] = get_series(df, ["Address", "Mail Full Address", "Mail Address"], "")
    out["City"] = get_series(df, ["City", "Mail City"], "")
    out["State"] = get_series(df, ["State", "Mail State"], "")
    out["Zip"] = get_series(df, ["Zip", "Mail Zip"], "")
    out["APN"] = get_series(df, ["APN", "Parcel ID", "Parcel Number"], "")
    out["Latitude"] = get_series(df, ["Latitude", "Lat"], "")
    out["Longitude"] = get_series(df, ["Longitude", "Long", "Lng"], "")
    out["FIPS"] = get_series(df, ["FIPS"], "")
    out["Property Address"] = get_series(df, ["Property Address", "Parcel Full Address"], "")
    out["Property City"] = get_series(df, ["Property City", "Parcel City"], "")
    out["Property State"] = get_series(df, ["Property State", "Parcel State"], "")
    out["Property Zip"] = get_series(df, ["Property Zip", "Parcel Zip"], "")
    out["Property County"] = get_series(df, ["Property County", "Parcel County"], "")
    out["Property Size"] = get_series(df, ["Property Size", "Lot size", "Lot Acres", "Calc Acreage", "Acres"], "")
    out["Short Legal Description"] = get_series(df, ["Short Legal Description", "Legal Description"], "")

    # Assessed Value should use the true county value when available.
    out["Assessed Value"] = numeric_series(df, ["County Assessed Value", "Total Market Value", "Total Assessed Value", "Assessed Value", "_Calc Assessed"])

    # Market Value should reflect the final true MV used by underwriting.
    out["Market Value"] = numeric_series(df, ["Offer MV Used", "Market Value", "TLP Estimate"])

    out["Multiplier"] = get_series(df, ["Multiplier"], "")
    out["Owner's First Name"] = get_series(df, ["Owner's First Name", "Owner 1 First Name", "First Name"], "")
    out["Owner's Last Name"] = get_series(df, ["Owner's Last Name", "Owner 1 Last Name", "Last Name"], "")
    out["2nd Owner's First Name"] = get_series(df, ["2nd Owner's First Name", "Owner 2 First Name"], "")
    out["2nd Owner's Last Name"] = get_series(df, ["2nd Owner's Last Name", "Owner 2 Last Name"], "")
    out["Offer Amount"] = offer1
    out["2nd Offer Amount"] = offer2
    out["3rd Offer Amount"] = offer3
    out["Betty Score"] = get_series(df, ["Betty Score", "BETTY SCORE"], "")

    # TLP Estimate column remains market intelligence. Prefer original TLP if available.
    out["TLP Estimate"] = numeric_series(df, ["TLP Estimate", "_Calc TLP", "Offer MV Used"])

    out["Hyperlink"] = get_series(df, ["Hyperlink", "Link", "URL", "Property URL"], "")
    out["Zoning"] = get_series(df, ["Zoning"], "")
    out["Offer Accept By"] = offer_accept_by
    out["Close Date"] = close_date

    # Exact header order.
    out = out[IMPORT_HEADERS]
    return out.reset_index(drop=True)

uploaded = st.file_uploader("Upload Underwriting Engine output", type=["xlsx", "xls", "csv"])

with st.expander("Options", expanded=True):
    c1, c2, c3 = st.columns(3)
    exclude_no_offer = c1.checkbox("Exclude records missing any offer amount", value=True)
    offer_accept_by = c2.text_input("Offer Accept By", value="")
    close_date = c3.text_input("Close Date", value="")
    output_format = st.radio("Output format", ["Excel .xlsx", "CSV"], horizontal=True)

if uploaded:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded, low_memory=False)
        else:
            df = pd.read_excel(uploaded, sheet_name="Offer Model")
    except Exception:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded, low_memory=False)
        else:
            # Fall back to first sheet if Offer Model is not present.
            df = pd.read_excel(uploaded)

    df = clean_columns(df)
    st.success(f"Loaded {len(df):,} rows and {len(df.columns):,} columns.")

    import_df = build_import(df, offer_accept_by, close_date, exclude_no_offer)
    st.write(f"Import file rows: {len(import_df):,}")
    st.dataframe(import_df.head(50), use_container_width=True)

    if output_format == "Excel .xlsx":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            import_df.to_excel(writer, index=False, sheet_name="SAMPLE-IMPORT-LIST")
            wb = writer.book
            ws = writer.sheets["SAMPLE-IMPORT-LIST"]

            header_fmt = wb.add_format({"bold": True, "bg_color": "#D9EAD3", "border": 1})
            money_fmt = wb.add_format({"num_format": "$#,##0.00"})
            num_fmt = wb.add_format({"num_format": "0.00"})
            text_fmt = wb.add_format({"num_format": "@"})

            for col_idx, col in enumerate(import_df.columns):
                ws.write(0, col_idx, col, header_fmt)
                width = min(max(len(col) + 2, 12), 28)
                ws.set_column(col_idx, col_idx, width)

            for col_name in ["Assessed Value", "Market Value", "Offer Amount", "2nd Offer Amount", "3rd Offer Amount", "TLP Estimate"]:
                if col_name in import_df.columns:
                    idx = import_df.columns.get_loc(col_name)
                    ws.set_column(idx, idx, 16, money_fmt)

            for col_name in ["Property Size", "Latitude", "Longitude"]:
                if col_name in import_df.columns:
                    idx = import_df.columns.get_loc(col_name)
                    ws.set_column(idx, idx, 14, num_fmt)

            for col_name in ["APN", "Zip", "Property Zip", "FIPS"]:
                if col_name in import_df.columns:
                    idx = import_df.columns.get_loc(col_name)
                    ws.set_column(idx, idx, 14, text_fmt)

            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(import_df), len(import_df.columns)-1)

        output.seek(0)
        st.download_button(
            "Download Import File",
            output,
            "blind_offer_import_file.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        csv = import_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Import CSV", csv, "blind_offer_import_file.csv", "text/csv")
