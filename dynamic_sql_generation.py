from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from langchain.prompts import PromptTemplate
import re

business_term_mapping = {
    "UBC": "COUNT(DISTINCT BillingDocument)",
    "unique billing count": "COUNT(DISTINCT BillingDocument)",
    "milk DTM":"DTM",
    "net amount": "SUM(NetAmount)",
    "sales quantity": "SUM(SalesQuantity)",
    "total tax": "SUM(TotalTax)",
    "total amount": "SUM(TotalAmount)",
    "butter milk": "buttermilk",
    "butter Milk": "buttermilk",
    "Butter Milk": "buttermilk",
    
}

def replace_business_terms(user_input: str) -> str:
    for key, value in business_term_mapping.items():
        pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
        user_input = pattern.sub(value, user_input)
    return user_input

from langchain.prompts import PromptTemplate

prompt_template = PromptTemplate(
    input_variables=["user_input"],
    template=""" 
You are a professional support representative helping a business analytics team with SQL queries. Your goal is to translate natural language queries from business users into accurate SQL queries based on a table of sales data, `Dw.fsales`. Your aim is to assist by providing precise SQL without unnecessary explanations.

### Table: Dw.fsales
| Column Name            | Data Type           | Description                                 |
|------------------------|---------------------|---------------------------------------------|
| DId                   | int                 | Internal ID                                 |
| BillingDocument       | bigint              | Sales bill number                           |
| BillingDocumentItem   | int                 | Item number in the bill                     |
| BillingDate           | date                | Date of billing                             |
| SalesOfficeID         | int                 | Sales office code                           |
| DistributionChannel   | nvarchar(25)        | Sales distribution channel                  |
| DisivisonCode         | int                 | Division code                               |
| Route                 | nvarchar(25)        | Sales route                                 |
| RouteDescription      | nvarchar(50)        | Route description                           |
| CustomerGroup         | nvarchar(25)        | Customer group                              |
| CustomerID            | nvarchar(50)        | Customer ID                                 |
| ProductHeirachy1      | nvarchar(35)        | Product category level 1 (e.g., Milk)       |
| ProductHeirachy2      | nvarchar(35)        | Product category level 2 (e.g., Cow)        |
| ProductHeirachy3      | nvarchar(35)        | Product category level 3 (e.g., DTM)        |
| ProductHeirachy4      | nvarchar(35)        | Product category level 4 (e.g., Sachets)    |
| ProductHeirachy5      | nvarchar(35)        | Product category level 5 (e.g., 500 ML)     |
| Materialgroup         | nvarchar(35)        | Material group                              |
| SubMaterialgroup1     | nvarchar(35)        | Sub-material group level 1                  |
| SubMaterialgroup2     | nvarchar(35)        | Sub-material group level 2                  |
| SubMaterialgroup3     | nvarchar(35)        | Sub-material group level 3                  |
| MaterialCode          | int                 | Material code                               |
| SalesQuantity         | decimal             | Quantity sold                               |
| SalesUnit             | nvarchar(5)         | Unit of measurement                         |
| TotalAmount           | decimal             | Total value including taxes                 |
| TotalTax              | decimal             | Total tax                                   |
| NetAmount             | decimal             | Total without tax                           |
| EffectiveStartDate    | datetime            | Contract/validity start                     |
| EffectiveEndDate      | datetime            | Contract/validity end                       |
| IsActive              | bit                 | 1 = active                                  |
| SalesOrganizationCode | int                 | Sales org code                              |
| SalesOrgCodeDesc      | nvarchar(50)        | Sales org description                       |
| ItemCategory          | nvarchar(75)        | Item category                               |
| ShipToParty           | nvarchar(30)        | Shipping partner ID                         |


### Product Hierarchies:
- ProductHeirachy1: Milk, Curd, Flav.Milk, Ghee, Frozen Dessert, Cream, ButterMilk, Lassi, Milk Cake, IceCream
- ProductHeirachy2: Cow, Buffalo, Default, Mixed
- ProductHeirachy3: DTM,STD Milk, Plain, Mango Tango, STANDY, Pista, TM, FCM, BFCM, Pine Apple, Caramel Ripple Sundae
- ProductHeirachy4: Sachets, Poly Pack, Tetra Pack, Matka, Cup, Pillow Pack, Bucket, Cone, Stick (Ice Cream), Glass Bottle
- ProductHeirachy5: 500 ML, 1000 GMS, 165 GMS, 10 KG, 9.1 KG, 200 GMS, 60ML, 400 GMS, 475 GMS, 350 ML

### Sample Values:
- SalesUnit: CAR, L, KG, EA
- DistributionChannel: Parlours, Direct
- DisivisonCode: 1, 4, 3, 2
- CustomerGroup: Parlours, HDC
- Materialgroup: MILK, UHT MILK, BUTTER MILK, BUCKET CURD, ICE CREAM/FD, SWEET LASSI (POUCH), CHEESE, BUTTER MILK (CUP), POUCH CURD, FRUIT LASSI (CUP)
- SubMaterialgroup1: Non-Dairy, Dairy, Dairy-Tradable Goods
- SubMaterialgroup2: Milk, VAP, Fat (Bulk), Fat (CP)
- SubMaterialgroup3: Milk - STD, Milk - FCM, VAP-Ice Cream, VAP-Butter Milk (Plain), Milk-TM-Special, VAP-Curd (Pouch), Milk-TM-Family, VAP-Lassi(Sweet), Milk - BFCM, VAP-Frozen Dessert
- ItemCategory: L2N, ZREN, G2N, ZZMS, ZMTS

- Sample Routes: 1942G, 1942J, 1940U, 1942F, 1945B, 1942B, 1981A, 1981B, 1941Q, 1965B
- Route Descriptions:
    - LB NAGAR TO VANASTALIPURAM
    - LB NAGAR TO SANTOSHNAGAR
    - Uppal-Vidyanagar-D.D.colony
    - KALLURU S O < > Khammam Local
    - Erragadda-MLA Colony-Banjarahills

### Instructions:
- Always use the table: `Dw.fsales`
- Use `DISTINCT` when asked for "different", "unique", or "list"
- Use `SUM()` or `COUNT()` if user asks for total, number, or total amount
- Use appropriate `WHERE` clauses when asked for specific date ranges (e.g., last year, last month, etc.)
- When you see product hierarchy terms in the user query, ensure they are enclosed in single quotes in the SQL query.
- Always enclose product hierarchy values in single quotes in the SQL query to avoid invalid column name errors.
- Generate a correct SQL query based on the user's question.
- Focus on **dates**: Always filter `BillingDate` by time references like "last week", "yesterday", "this month", etc.
- If the user mentions **“top”, “highest”**, calculate normalized sales over the requested period (e.g., divide the total by 7 for a weekly comparison).
- If the user asks for **“total”**, use `SUM(SalesQuantity)` without division.
- If the user asks for **“average”**, divide `SUM(SalesQuantity)` by the number of days in the requested period (7 for a week, 30 for a month, etc.).
- When grouping by product hierarchies, always enclose values in single quotes in the query (e.g., `'Milk'`, `'Butter'`).
- If the period is a **week**, divide the result by 7 for averages or comparisons.
- If the period is a **month**, divide the result by 30 for averages or comparisons.
- Be concise with the SQL and avoid adding units or unnecessary formatting.

### SQL RULES:

1. Always use the table: `Dw.fsales`
2. Use single quotes for string values (e.g., `'Milk'`)
3. If asked for:
   - “total sales” → use `SUM(SalesQuantity)`
   - “average sales per day last week” → use `SUM(SalesQuantity)/7`
4. Use `DATEADD(WEEK, -1, GETDATE())` to filter for "last week" (adjust if needed).
5. Use `GROUP BY` when asking by route, product, etc.
6. Use `COUNT(DISTINCT BillingDocument)` for UBC (unique billing count).
7. No explanations — only the SQL output.
8. Always sanitize values and avoid placeholder names like `example_value`.


### BUSINESS LANGUAGE CONVENTIONS:
- Questions are asked like: “What is the sales quantity for Milk DTM sale for last week?”
- “Curd” or “Milk” refer to `ProductHeirachy1` values.
- “DTM” or similar refer to `ProductHeirachy3` values.
- “Last week” means the previous calendar week (Monday to Sunday).
- UBC means unique billing count → use `COUNT(DISTINCT BillingDocument)`
- When the user asks for comparison between products or routes, use `GROUP BY`
- Use `SUM(SalesQuantity)` for total sales, and `SUM(SalesQuantity)/7` for weekly average.

### EXAMPLES:
- **"What is the sales quantity for Milk DTM sale for last week?"**  
→ `SELECT SUM(SalesQuantity)/7 FROM Dw.fsales WHERE ProductHeirachy1 = 'Milk' AND ProductHeirachy3 = 'DTM' AND BillingDate BETWEEN DATEADD(DAY, 1 - DATEPART(WEEKDAY, GETDATE()), DATEADD(WEEK, -1, GETDATE())) AND DATEADD(DAY, 7 - DATEPART(WEEKDAY, GETDATE()), DATEADD(WEEK, -1, GETDATE()));`



### Example Queries:
- **"Top selling milk product last week"** → Use `SUM(SalesQuantity)/7` and order DESC.
- **"Sales quantity of milk for last week"** → Use `SUM(SalesQuantity)/7`.
- **"Total sales quantity for butter last month"** → Use `SUM(SalesQuantity)/30`.
- **"Average sales of milk per day last week"** → Use `SUM(SalesQuantity)/7`.
- **"Total sales for the past month"** → Use `SUM(SalesQuantity)`.

### Sample Query Translations:
1. "What’s the total sales for today?" → `SELECT SUM(SalesQuantity) FROM Dw.fsales WHERE BillingDate = CAST(GETDATE() AS DATE);`
2. "Show UBC and Net Amount for last week by route" → `SELECT Route, SUM(UBC), SUM(NetAmount) FROM Dw.fsales WHERE BillingDate >= DATEADD(week, -1, GETDATE()) GROUP BY Route;`
3. "Compare sales of Milk vs Curd in April" → `SELECT SUM(SalesQuantity) FROM Dw.fsales WHERE ProductHeirachy1 IN ('Milk', 'Curd') AND BillingDate >= '2025-04-01' AND BillingDate < '2025-05-01' GROUP BY ProductHeirachy1;`
4. "Top 5 selling products in the last 30 days" → `SELECT TOP 5 ProductHeirachy1, SUM(SalesQuantity) FROM Dw.fsales WHERE BillingDate >= DATEADD(day, -30, GETDATE()) GROUP BY ProductHeirachy1 ORDER BY SUM(SalesQuantity) DESC;`
5. "Which product had the highest UBC in Route X?" → `SELECT ProductHeirachy1, MAX(UBC) FROM Dw.fsales WHERE Route = 'Route X' GROUP BY ProductHeirachy1;`

User Query: "USER_INPUT"

Context:
- **Product Types**: Milk, Curd, etc.
- **Metrics**: Sales Quantity, Net Amount, Total Amount, Sales Date, etc.
- **Filters**: Region, Date Range, Sales Office, etc.
- **Comparison Operations**: SUM, AVG, COUNT, etc.
- **Relationships**: The user may ask for comparisons between product categories, across different time periods, or specific filters.

### Instructions:
1. **Identify the main product(s)** involved in the query (e.g., Milk, Curd).
2. **Identify the metric(s)** the user wants to analyze (e.g., Sales Quantity, Net Amount).
3. Recognize if the user is asking for **comparisons** between products (e.g., comparing Milk vs. Curd).
4. **Identify any filters** mentioned in the query (e.g., Region, Date Range).
5. **Generate the SQL query** based on the user's request:
   - Ensure that product categories are enclosed in single quotes in the query.
   - Apply the appropriate aggregation function (SUM, AVG, etc.) as required.
   - Filter by date range and region or other specified filters.

### SQL Query Template:

```sql
SELECT 
    Product, 
    SUM(SalesQuantity) AS TotalSales, 
    SUM(NetAmount) AS TotalAmount
FROM Dw.fsales
WHERE Product IN ('Milk', 'Curd')  -- Adjust based on user query
  AND BillingDate BETWEEN '2025-04-01' AND '2025-04-30'  -- Adjust based on user input
  AND Region = 'Region A'  -- Adjust if region filter is specified
GROUP BY Product;

User Query: {user_input}

SQL:
"""
)

llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4",
    openai_api_key=None
)

nl_to_sql_chain = LLMChain(llm=llm, prompt=prompt_template)

product_hierarchy_terms = {
    'Milk', 'Butter', 'ButterMilk', 'Cheese', 'Cold Coffee', 'Cream', 'Curd', 'Doodh Peda',
    'Flav.Milk', 'Frozen Dessert', 'Ghee', 'Gluco Shakti', 'Gulab Jamun', 'IceCream', 'Laddu', 
    'Lassi', 'Milk Cake', 'Milk Shakes', 'Paneer', 'Rasgulla', 'Shrikhand', 'SkimMilk Powder',
    'Buffalo', 'Cow', 'Default', 'Mixed',
    'Afghan Delight', 'Agmarked', 'Almond Crunch', 'American Delight', 'Amrakhand', 'Anjeer Badam',
    'Badam', 'Badam Nuts', 'Badam Pista Kesar', 'Banana Cinnamon', 'Banana Strawberry', 'Belgium Chocolate',
    'Berry Burst', 'BFCM', 'Black Currant Vanilla', 'Black Current', 'Blocks', 'Bubble Gum', 'Butter Scotch',
    'Butterscotch Bliss', 'Butterscotch Crunch', 'Caramel Nuts', 'Caramel Ripple Sundae', 'Cassatta',
    'Choco chips', 'Choco Rock', 'Chocobar', 'Chocolate', 'Chocolate Coffee Fudge', 'Chocolate Overload',
    'Classic Kulfi', 'Classic Vanilla', 'Coffee', 'Cookies & Cream', 'Cotton Candy', 'Cubes', 'Double Chocolate',
    'DTM', 'Elachi', 'FCM', 'Fig Honey', 'Fruit Fantasy', 'Fruit Fusion', 'Gol Gappa', 'Golden Cow Milk',
    'Grape Juicy', 'Gulkhand Kulfi', 'HONEY NUTS', 'ISI', 'Jowar', 'Kala Khatta', 'Kohinoor Kulfi', 'Laddoo Prasadam',
    'LATTE', 'Low Fat', 'Malai Kulfi', 'Mango', 'Mango Alphanso', 'Mango Juicy', 'Mango Masti Jusy',
    'Mango Tango', 'Mawa Kulfi', 'Mega-Sundae', 'Melon Rush', 'Mixed Berry Sundae', 'Mixed Millet', 'Mozarella',
    'NonAgmarked', 'Orange', 'Orange Juicy', 'Pan Kulfi', 'Pine Apple', 'Pineapple', 'Pista', 'Pistachio',
    'Plain', 'Pot Kulfi (Pista)', 'Premium Vannila', 'Probiotic', 'Probiotic TM', 'Rajbhog', 'Rasperry Twin',
    'Roasted Cashew', 'Royal Rose Delight', 'Sabja', 'Salted', 'Shrikhand Kesar', 'Sitaphal', 'Slices', 'Slim',
    'Special', 'STANDY', 'STD', 'STD Milk', 'Strawberry', 'Strawbery', 'Sweet', 'TM', 'Twin Vanilla&Strawberry',
    'Vanilla', 'Vanilla&Strawberry', 'Alu. Foil Pack', 'Aluminium Foil  Pack', 'Ball', 'Box', 'Bucket', 'Carton',
    'Ceka Pack', 'Cone', 'Cup', 'Glass Bottle', 'Jar', 'Matka', 'Pillow Pack', 'Poly Pack', 'Pouch', 'PP + Box',
    'PP Bottle', 'Sachets', 'Spout Pouch', 'STANDY POUCH', 'Stick', 'Stick (Ice Cream)', 'Tetra Pack', 'Tin', 'Tray',
    'Tub', 'UHT Poly Pack', '1 KG', '10 KG', '100 GMS', '100 ML', '1000 GMS', '1000 ML', '110 ML', '110ML',
    '115 GMS', '120 GMS', '120 ML', '125 GMS', '125 ML', '125ML', '12ML', '130 GMS', '130 ML', '135 GMS', '135 ML',
    '140 GMS', '140 ML', '145 GMS', '145 ML', '15 KG', '150 GMS', '150 ML', '155 ML', '160 GMS', '160 ML', '165 GMS',
    '165 ML', '170 GMS', '170 ML', '175 ML', '18.2 KG', '180 GMS', '180 ML', '185 ML', '190 ML', '2 KG', '2 Litres',
    '20 GMS', '20 KG', '200 GMS', '200 ML', '220 GMS', '220 ML', '225 GMS', '225 ML', '230 ML', '250 GMS', '250 ML',
    '25ML', '300 GMS', '310 ML', '325 ML', '330 ML', '35 ML', '350 GMS', '350 ML', '360 GMS', '375 ML', '380 GMS',
    '4 liters', '4 Litres', '4.5 KG', '4.70 KG', '40 ML', '400 GMS', '400 ML', '425 GMS', '425 ML', '440 ML', '450 GMS',
    '450 ML', '475 GMS', '475 ML', '480 GMS', '480 ML', '485 ML', '490 ML', '5 Kg', '5 Litres', '50 ML', '500 GMS',
    '500 ML', '6 Liter', '60 ML', '60ML', '65 ML', '70 GMS', '70 ML', '700 ML', '700+700ML', '700ML', '750 ML',
    '80 GMS', '80 ML', '800 ML', '850 GMS', '9 KG', '9.1 KG', '90 ML', '900 GMS', '900 ML', '950 GMS', '950 ML',
    '975 ML', '990 ML'
}

def preprocess_user_input(user_input: str) -> str:
    # Replace business terms with SQL expressions
    user_input = replace_business_terms(user_input)
    # Sort terms by length descending to avoid partial replacements
    sorted_terms = sorted(product_hierarchy_terms, key=len, reverse=True)
    for term in sorted_terms:
        # Use regex to replace whole word matches case-insensitively
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        user_input = pattern.sub(f"'{term}'", user_input)
    return user_input

def fix_unquoted_product_terms(sql_query: str) -> str:
    """
    Post-process the generated SQL query to ensure product hierarchy terms are quoted.
    """
    for term in product_hierarchy_terms:
        # Replace unquoted term with quoted term, only if it appears as a standalone word
        pattern = re.compile(rf"(?<!')\b{re.escape(term)}\b(?!')", re.IGNORECASE)
        sql_query = pattern.sub(f"'{term}'", sql_query)
    return sql_query

def generate_sql_from_nl(user_query: str) -> str:
    """
    Generate SQL query from natural language user query using LangChain LLMChain.
    Preprocess user input to handle business terms and product hierarchy terms.
    Post-process generated SQL to fix unquoted product hierarchy terms.
    Strip markdown code block delimiters from the generated SQL before returning.
    """
    preprocessed_query = preprocess_user_input(user_query)
    result = nl_to_sql_chain.run(user_input=preprocessed_query)
    # Remove markdown triple backticks and optional language specifier
    if result.startswith("```sql"):
        result = result[len("```sql"):].strip()
    elif result.startswith("```"):
        result = result[len("```"):].strip()
    # Remove any trailing ```
    if result.endswith("```"):
        result = result[:-3].strip()
    # Fix unquoted product hierarchy terms in SQL
    result = fix_unquoted_product_terms(result)
    return result.strip()
