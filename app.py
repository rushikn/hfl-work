import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# Ensure OPENAI_API_KEY is set in environment before importing LangChain
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

import pyodbc
import openai
from dynamic_sql_generation import generate_sql_from_nl
import re
import contractions

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DRIVER = os.getenv("Driver")
SERVER = os.getenv("Server")
DATABASE = os.getenv("Database")
UID = os.getenv("UID")
PWD = os.getenv("PWD")

openai.api_key = OPENAI_API_KEY

# Define column data types for Dw.fsales table
COLUMN_TYPES = {
    "DId": "int",
    "BillingDocument": "varchar",
    "BillingDocumentItem": "varchar",
    "BillingDate": "date",
    "SalesOfficeID": "int",
    "DistributionChannel": "varchar",
    "DisivisonCode": "varchar",
    "Route": "varchar",
    "RouteDescription": "varchar",
    "CustomerGroup": "varchar",
    "CustomerID": "varchar",
    "ProductHeirachy1": "varchar",
    "ProductHeirachy2": "varchar",
    "ProductHeirachy3": "varchar",
    "ProductHeirachy4": "varchar",
    "ProductHeirachy5": "varchar",
    "Materialgroup": "varchar",
    "SubMaterialgroup1": "varchar",
    "SubMaterialgroup2": "varchar",
    "SubMaterialgroup3": "varchar",
    "MaterialCode": "varchar",
    "SalesQuantity": "int",
    "SalesUnit": "varchar",
    "TotalAmount": "decimal",
    "TotalTax": "decimal",
    "NetAmount": "decimal",
    "EffectiveStartDate": "date",
    "EffectiveEndDate": "date",
    "IsActive": "bit",
    "SalesOrganizationCode": "varchar",
    "SalesOrgCodeDesc": "varchar",
    "ItemCategory": "varchar",
    "ShipToParty": "varchar"
}

def fix_sql_value_quoting(sql_query):
    # This function attempts to fix quoting of values based on column data types
    for column, col_type in COLUMN_TYPES.items():
        # Regex to find conditions like column = 'value' or column='value'
        pattern = re.compile(rf"({column}\s*=\s*)'([^']*)'", re.IGNORECASE)
        def replacer(match):
            prefix = match.group(1)
            value = match.group(2)
            # For numeric types, remove quotes
            if col_type in ['int', 'decimal', 'bit']:
                # Check if value is numeric or boolean-like
                if value.isdigit() or value.lower() in ['true', 'false', '0', '1']:
                    return f"{prefix}{value}"
                else:
                    # If value is not numeric, keep quotes to avoid SQL error
                    return match.group(0)
            else:
                # For varchar, date, keep quotes
                return match.group(0)
        sql_query = pattern.sub(replacer, sql_query)
    return sql_query

def validate_sql_query(sql_query):
    # Check for placeholder or example values in the SQL query
    placeholders = ['specific_salesofficeid', 'example_value', 'placeholder']
    for ph in placeholders:
        if ph.lower() in sql_query.lower():
            return False, f"SQL query contains placeholder value: {ph}"
    return True, ""

def execute_sql_query(sql_query):
    try:
        connection_string = (
            f"DRIVER={{{DRIVER}}};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            f"UID={UID};"
            f"PWD={PWD}"
        )
        with pyodbc.connect(connection_string, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results
    except Exception as e:
        st.error(f"Error executing SQL query: {e}")
        return None

def results_to_natural_language(results, user_query):
    if not results:
        return "No results found."

    # Detect sales quantity questions without a time reference
    if "salesquantity" in user_query.lower().replace(" ", "") or "sales quantity" in user_query.lower():
        # Extend time references with additional time-related keywords
        time_keywords = [
            "yesterday", "today", "last week", "last month", "this week", "this month", 
            "on", "between", "from", "to", "qtd", "quarter", "mtd", "month", "wtd", "week", 
            "ytd", "year", "l7d", "last 7 days", "lw", "previous week", "pw"
        ]
        
        # Check if any time keyword is present in the user's query
        if not any(time_kw in user_query.lower() for time_kw in time_keywords):
            return "Please specify a time period for the sales quantity (e.g., 'last week', 'yesterday', 'QTD', 'MTD', 'L7D', etc.)."

    # Convert results list of dicts to string for prompt
    results_str = "\n".join([str(row) for row in results[:10]])  # limit to first 10 rows

    prompt_text = (
        f"The user asked: \"{user_query}\"\n\n"
        f"The SQL query returned the following result:\n{results_str}\n\n"
        "Generate a direct, concise, and natural language answer using the user's question and result. "
        "Avoid explanations and unit information. Example output: 'The unique billing count for yesterday is 3421.'\n\n"
        "Answer:"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[ 
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=150,
            temperature=0.3,
        )
        summary = response.choices[0].message['content'].strip()

        # Remove units if accidentally generated
        units = [
            "$ USD", "€ EUR", "£ GBP", "₹ INR", "¥ JPY", "₩ KRW", 
            "KG", "G", "L", "ML", "Units","$"
        ]
        
        for unit in units:
            summary = summary.replace(unit, "")

        return summary
    except Exception as e:
        st.error(f"Error generating natural language summary: {e}")
        return "Could not generate summary."


def main():
    st.set_page_config(page_title="AskDB", page_icon="🗄️", layout="centered")
    st.title("Ask HFL ")

    user_query = st.text_area("Enter your query:")

    sql_query = None  # Initialize sql_query to avoid UnboundLocalError

    if st.button("Run Query"):
        if not user_query.strip():
            st.warning("Please enter a query.")
            return

        with st.spinner("Translating to SQL..."):
            # Preprocess the user query before generating SQL
            preprocessed_query = contractions.fix(user_query)
        # Use dynamic SQL generation via LLM chain
        sql_query = generate_sql_from_nl(preprocessed_query)
        # Fix SQL value quoting based on column types
        sql_query = fix_sql_value_quoting(sql_query)
        print(f"Generated SQL Query: {sql_query}")
        st.subheader("Generated SQL Query:")
        st.code(sql_query, language="sql")

    # Validate SQL query for placeholders
    if sql_query is None:
        st.warning("No SQL query generated.")
        return

    valid, error_msg = validate_sql_query(sql_query)
    if not valid:
        st.error(error_msg)
        return

    with st.spinner("Executing SQL query..."):
        try:
            results = execute_sql_query(sql_query)
        except Exception as e:
            st.error(f"Error executing SQL query: {e}")
            return
        
    if results is not None:
        st.subheader("Result:")
        summary = results_to_natural_language(results, user_query)
        st.write(summary)

if __name__ == "__main__":
    main()
